#!/usr/bin/env python3
"""NIFTY 50 Options Greeks & Quantitative Risk Engine. Standard library only.

Provides exact Black-Scholes-Merton mathematical modeling and Greeks calculation:
- Delta (Δ): Directional sensitivity (0.0 to 1.0 for CE, -1.0 to 0.0 for PE)
- Gamma (Γ): Rate of change in Delta per index point move
- Theta (Θ): Time decay per calendar day and per trading hour
- Vega (ν): Premium sensitivity to a 1% change in India VIX (Implied Volatility)
- Omega (Ω): Option elasticity / Gearing ratio (% change in option per 1% move in index)
- Rho (ρ): Interest rate sensitivity

Stop-Loss & Target Setting Methods:
1. Spot-to-Premium Delta/Gamma Taylor Mapping: Maps Spot chart technical SL/TP into exact option premiums.
2. Hourly Theta Decay Rate: Quantifies time-decay risk for intraday holding.
3. SEBI F&O Statutory Friction: Deducts 0.1% STT on option sell turnover, exchange charges, GST, and brokerage.

    python3 greeks.py --spot 24500 --strike 24500 --type CE --days 2 --iv 14.5
    python3 greeks.py plan --spot-entry 24500 --spot-sl 24460 --spot-target 24580 --type CE
"""

import argparse
import datetime
import json
import math
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Standard NIFTY parameters
DEFAULT_RISK_FREE_RATE = 0.065   # RBI 91-day T-Bill rate ~6.5%
DEFAULT_LOT_SIZE = 75           # NSE NIFTY contract lot size
STRIKE_STEP = 50                # NIFTY strike interval (e.g. 24450, 24500, 24550)
TRADING_HOURS_PER_DAY = 6.25    # 09:15 to 15:30 IST


# ---------------------------------------------------------------- Normal Distribution

def standard_normal_pdf(x):
    """Standard normal probability density function N'(x)."""
    return (1.0 / math.sqrt(2.0 * math.pi)) * math.exp(-0.5 * x * x)


def standard_normal_cdf(x):
    """Cumulative standard normal distribution function N(x) using math.erf."""
    return 0.5 * (1.0 + math.erf(x / math.sqrt(2.0)))


# ---------------------------------------------------------------- Black-Scholes Greeks

def calculate_d1_d2(spot, strike, t_years, r, sigma):
    """Computes Black-Scholes d1 and d2."""
    if t_years <= 0 or sigma <= 0 or spot <= 0 or strike <= 0:
        return 0.0, 0.0
    numerator = math.log(spot / strike) + (r + 0.5 * sigma * sigma) * t_years
    denominator = sigma * math.sqrt(t_years)
    d1 = numerator / denominator
    d2 = d1 - denominator
    return d1, d2


def calculate_option_greeks(spot, strike, days_to_expiry, iv_pct, opt_type="CE", r=DEFAULT_RISK_FREE_RATE):
    """Calculates theoretical price and full Greeks (Delta, Gamma, Theta, Vega, Omega, Rho).
    
    Parameters:
    - spot: Current NIFTY Spot Index price
    - strike: Option Strike Price
    - days_to_expiry: Days remaining until weekly/monthly expiry (fractions allowed)
    - iv_pct: Implied Volatility in percent (e.g. 14.5 for India VIX 14.5)
    - opt_type: 'CE' (Call) or 'PE' (Put)
    - r: Annualized risk-free interest rate (default 6.5%)
    """
    spot = float(spot)
    strike = float(strike)
    opt_type = opt_type.upper()
    sigma = float(iv_pct) / 100.0
    t_years = max(0.0001, float(days_to_expiry) / 365.0)
    
    d1, d2 = calculate_d1_d2(spot, strike, t_years, r, sigma)
    pdf_d1 = standard_normal_pdf(d1)
    
    discount_factor = math.exp(-r * t_years)
    
    # 1. Theoretical Price
    if opt_type == "CE":
        price = spot * standard_normal_cdf(d1) - strike * discount_factor * standard_normal_cdf(d2)
        delta = standard_normal_cdf(d1)
        theta_annual = (-(spot * sigma * pdf_d1) / (2.0 * math.sqrt(t_years))
                        - r * strike * discount_factor * standard_normal_cdf(d2))
        rho = (strike * t_years * discount_factor * standard_normal_cdf(d2)) * 0.01
    else:  # PE
        price = strike * discount_factor * standard_normal_cdf(-d2) - spot * standard_normal_cdf(-d1)
        delta = standard_normal_cdf(d1) - 1.0
        theta_annual = (-(spot * sigma * pdf_d1) / (2.0 * math.sqrt(t_years))
                        + r * strike * discount_factor * standard_normal_cdf(-d2))
        rho = (-strike * t_years * discount_factor * standard_normal_cdf(-d2)) * 0.01
        
    price = max(0.05, price)
    
    # 2. Gamma (Rate of change of Delta per index point move)
    gamma = pdf_d1 / (spot * sigma * math.sqrt(t_years))
    
    # 3. Theta (Time decay)
    theta_daily = theta_annual / 365.0
    theta_hourly = theta_daily / TRADING_HOURS_PER_DAY
    
    # 4. Vega (Price change per 1% change in IV/India VIX)
    vega = (spot * math.sqrt(t_years) * pdf_d1) * 0.01
    
    # 5. Omega / Option Elasticity (Effective Leverage/Gearing)
    # Omega = (Delta * Spot) / Option Price
    omega = (delta * spot) / price
    
    # Intrinsic vs Extrinsic Value
    if opt_type == "CE":
        intrinsic = max(0.0, spot - strike)
    else:
        intrinsic = max(0.0, strike - spot)
    extrinsic = max(0.0, price - intrinsic)
    
    return {
        "spot": spot,
        "strike": strike,
        "type": opt_type,
        "days_to_expiry": round(days_to_expiry, 2),
        "iv_pct": round(iv_pct, 2),
        "theoretical_price": round(price, 2),
        "intrinsic_value": round(intrinsic, 2),
        "extrinsic_time_value": round(extrinsic, 2),
        "delta": round(delta, 4),
        "gamma": round(gamma, 6),
        "theta_daily": round(theta_daily, 2),
        "theta_hourly": round(theta_hourly, 3),
        "vega": round(vega, 2),
        "omega_elasticity": round(omega, 2),
        "rho": round(rho, 4)
    }


# ---------------------------------------------------------------- Strike Selection Engine

def find_optimal_strikes(spot, target_delta_min=0.55, target_delta_max=0.70, days_to_expiry=2.0, iv_pct=14.0):
    """Finds At-The-Money (ATM) and In-The-Money (ITM) strikes with Delta between 0.55 and 0.70.
    Eliminates low-delta OTM lottery traps.
    """
    spot = float(spot)
    atm_strike = round(spot / STRIKE_STEP) * STRIKE_STEP
    
    # Test nearby strikes
    candidate_ce = []
    candidate_pe = []
    
    for offset in range(-4, 5):
        k = atm_strike + (offset * STRIKE_STEP)
        g_ce = calculate_option_greeks(spot, k, days_to_expiry, iv_pct, "CE")
        g_pe = calculate_option_greeks(spot, k, days_to_expiry, iv_pct, "PE")
        
        # Categorize
        label_ce = "ATM" if k == atm_strike else ("ITM" if k < atm_strike else "OTM")
        label_pe = "ATM" if k == atm_strike else ("ITM" if k > atm_strike else "OTM")
        
        candidate_ce.append({**g_ce, "moneyness": label_ce})
        candidate_pe.append({**g_pe, "moneyness": label_pe})
        
    # Best Call: ATM or 1 strike ITM matching target delta
    best_ce = next((c for c in candidate_ce if c["moneyness"] in ("ATM", "ITM") and c["delta"] >= target_delta_min), candidate_ce[4])
    best_pe = next((p for p in candidate_pe if p["moneyness"] in ("ATM", "ITM") and abs(p["delta"]) >= target_delta_min), candidate_pe[4])
    
    return {
        "spot": spot,
        "atm_strike": atm_strike,
        "recommended_ce": best_ce,
        "recommended_pe": best_pe,
        "all_ce_strikes": candidate_ce,
        "all_pe_strikes": candidate_pe
    }


# ---------------------------------------------------------------- Spot-to-Option Stop-Loss & Target Planner

def plan_nifty_option_trade(spot_entry, spot_sl, spot_target, opt_type="CE", days_to_expiry=2.0, iv_pct=14.0, lot_size=DEFAULT_LOT_SIZE, lots=1):
    """Maps a NIFTY Spot index setup (Entry, Technical SL, Target) into exact option premium levels.
    
    Uses second-order Taylor series:
    ΔOption = (Delta * ΔSpot) + (0.5 * Gamma * (ΔSpot)^2)
    """
    spot_entry = float(spot_entry)
    spot_sl = float(spot_sl)
    spot_target = float(spot_target)
    opt_type = opt_type.upper()
    total_qty = lot_size * lots
    
    # Determine strike: 1 strike ITM for momentum buying
    atm_strike = round(spot_entry / STRIKE_STEP) * STRIKE_STEP
    if opt_type == "CE":
        strike = atm_strike - STRIKE_STEP  # 1 strike ITM (Delta ~0.60 - 0.65)
    else:
        strike = atm_strike + STRIKE_STEP  # 1 strike ITM
        
    greeks = calculate_option_greeks(spot_entry, strike, days_to_expiry, iv_pct, opt_type)
    delta = greeks["delta"]
    gamma = greeks["gamma"]
    entry_premium = greeks["theoretical_price"]
    
    # Spot moves
    if opt_type == "CE":
        spot_risk_pts = spot_entry - spot_sl
        spot_target_pts = spot_target - spot_entry
        # Downward move for SL: delta drops slightly
        premium_sl_drop = (delta * spot_risk_pts) - (0.5 * gamma * (spot_risk_pts ** 2))
        # Upward move for Target: gamma accelerates gain
        premium_target_gain = (delta * spot_target_pts) + (0.5 * gamma * (spot_target_pts ** 2))
    else:  # PE
        spot_risk_pts = spot_sl - spot_entry
        spot_target_pts = spot_entry - spot_target
        abs_delta = abs(delta)
        premium_sl_drop = (abs_delta * spot_risk_pts) - (0.5 * gamma * (spot_risk_pts ** 2))
        premium_target_gain = (abs_delta * spot_target_pts) + (0.5 * gamma * (spot_target_pts ** 2))
        
    sl_premium = max(0.50, round(entry_premium - premium_sl_drop, 2))
    target_premium = round(entry_premium + premium_target_gain, 2)
    
    premium_risk = round(entry_premium - sl_premium, 2)
    premium_reward = round(target_premium - entry_premium, 2)
    rr_ratio = round(premium_reward / premium_risk, 2) if premium_risk > 0 else 0.0
    
    # Rupee calculations
    total_capital_required = round(entry_premium * total_qty, 2)
    rupee_risk = round(premium_risk * total_qty, 2)
    rupee_reward = round(premium_reward * total_qty, 2)
    
    # Statutory Fees (0.1% STT on sell side, exchange charges, GST, ₹20 broker fee)
    sell_turnover = target_premium * total_qty
    stt = round(0.001 * sell_turnover, 2)
    exchange_txn = round(0.0005 * (total_capital_required + sell_turnover), 2)
    brokerage = 40.0  # ₹20 buy + ₹20 sell
    gst = round(0.18 * (brokerage + exchange_txn), 2)
    total_statutory_fees = round(stt + exchange_txn + brokerage + gst, 2)
    
    net_profit_at_target = round(rupee_reward - total_statutory_fees, 2)
    net_rr = round(net_profit_at_target / (rupee_risk + total_statutory_fees), 2) if rupee_risk > 0 else 0.0
    
    # Time-in-Trade Momentum Decay Limit (Max 4 candles = 20 mins)
    hourly_decay_rupees = round(abs(greeks["theta_hourly"]) * total_qty, 2)
    
    return {
        "instrument": f"NIFTY {int(strike)} {opt_type}",
        "strike": strike,
        "option_type": opt_type,
        "spot_levels": {
            "entry": spot_entry,
            "stop_loss": spot_sl,
            "target": spot_target,
            "spot_risk_points": round(spot_risk_pts, 2),
            "spot_target_points": round(spot_target_pts, 2)
        },
        "premium_levels": {
            "entry_premium": entry_premium,
            "stop_loss_premium": sl_premium,
            "target_premium": target_premium,
            "risk_per_share": premium_risk,
            "reward_per_share": premium_reward,
            "reward_risk_ratio": rr_ratio
        },
        "position_sizing": {
            "lot_size": lot_size,
            "lots": lots,
            "total_qty": total_qty,
            "capital_required_inr": total_capital_required,
            "max_loss_inr": rupee_risk,
            "gross_profit_inr": rupee_reward,
            "statutory_fees_inr": total_statutory_fees,
            "net_profit_inr": net_profit_at_target,
            "net_reward_risk_ratio": net_rr
        },
        "greeks": greeks,
        "theta_momentum_rules": {
            "hourly_decay_cost_inr": hourly_decay_rupees,
            "max_trade_duration_minutes": 20,
            "rule": "Exit or trail stop to breakeven if Nifty Spot does not advance within 15-20 minutes."
        }
    }


def main():
    p = argparse.ArgumentParser(description="NIFTY Options Greeks & Risk Engine")
    sub = p.add_subparsers(dest="command")
    
    # Command 1: Greeks calculation
    s_calc = sub.add_parser("calc", help="Calculate Black-Scholes Greeks for a strike")
    s_calc.add_argument("--spot", type=float, required=True)
    s_calc.add_argument("--strike", type=float, required=True)
    s_calc.add_argument("--type", choices=["CE", "PE", "ce", "pe"], default="CE")
    s_calc.add_argument("--days", type=float, default=2.0, help="Days to expiry")
    s_calc.add_argument("--iv", type=float, default=14.0, help="Implied Volatility / India VIX %")
    
    # Command 2: Strike recommendation
    s_rec = sub.add_parser("recommend", help="Find optimal ATM/ITM strikes")
    s_rec.add_argument("--spot", type=float, required=True)
    s_rec.add_argument("--days", type=float, default=2.0)
    s_rec.add_argument("--iv", type=float, default=14.0)
    
    # Command 3: Full Trade Plan
    s_plan = sub.add_parser("plan", help="Generate complete Spot-to-Option trade plan")
    s_plan.add_argument("--spot-entry", type=float, required=True)
    s_plan.add_argument("--spot-sl", type=float, required=True)
    s_plan.add_argument("--spot-target", type=float, required=True)
    s_plan.add_argument("--type", choices=["CE", "PE", "ce", "pe"], default="CE")
    s_plan.add_argument("--days", type=float, default=2.0)
    s_plan.add_argument("--iv", type=float, default=14.0)
    s_plan.add_argument("--lots", type=int, default=1)
    s_plan.add_argument("--json", action="store_true")
    
    args = p.parse_args()
    
    if args.command == "calc":
        res = calculate_option_greeks(args.spot, args.strike, args.days, args.iv, args.type)
        print("=" * 65)
        print(f" BLACK-SCHOLES GREEKS: NIFTY {int(args.strike)} {args.type.upper()}")
        print("=" * 65)
        print(f"  Theoretical Price:  ₹ {res['theoretical_price']:,.2f}")
        print(f"  Delta (Δ):          {res['delta']:+.4f} (Directional sensitivity)")
        print(f"  Gamma (Γ):          {res['gamma']:.6f} (Delta acceleration)")
        print(f"  Theta (Θ Daily):    ₹ {res['theta_daily']:,.2f} / day")
        print(f"  Theta (Θ Hourly):   ₹ {res['theta_hourly']:,.3f} / trading hour")
        print(f"  Vega (ν):           ₹ {res['vega']:,.2f} per 1% change in VIX")
        print(f"  Omega (Ω):          {res['omega_elasticity']:.2f}x (Effective Leverage/Gearing)")
        print("=" * 65)
        
    elif args.command == "recommend":
        rec = find_optimal_strikes(args.spot, days_to_expiry=args.days, iv_pct=args.iv)
        print("=" * 70)
        print(f" 🎯 OPTIMAL NIFTY STRIKES (Spot: {args.spot})")
        print("=" * 70)
        ce = rec["recommended_ce"]
        pe = rec["recommended_pe"]
        print(f" Recommended Bullish Call: NIFTY {int(ce['strike'])} CE ({ce['moneyness']})")
        print(f"   Premium: ₹ {ce['theoretical_price']} | Delta: {ce['delta']:+.2f} | Omega: {ce['omega_elasticity']:.1f}x")
        print(f"\n Recommended Bearish Put:  NIFTY {int(pe['strike'])} PE ({pe['moneyness']})")
        print(f"   Premium: ₹ {pe['theoretical_price']} | Delta: {pe['delta']:+.2f} | Omega: {pe['omega_elasticity']:.1f}x")
        print("=" * 70)
        
    elif args.command == "plan":
        plan = plan_nifty_option_trade(
            args.spot_entry, args.spot_sl, args.spot_target,
            opt_type=args.type, days_to_expiry=args.days, iv_pct=args.iv, lots=args.lots
        )
        if args.json:
            print(json.dumps(plan, indent=2))
            return 0
            
        print("=" * 70)
        print(f" ⚡ NIFTY OPTIONS TRADE PLAN: {plan['instrument']}")
        print("=" * 70)
        print(f" Spot Levels:       Entry {plan['spot_levels']['entry']} | SL {plan['spot_levels']['stop_loss']} | Target {plan['spot_levels']['target']}")
        print(f" Option Premium:    BUY @ ₹ {plan['premium_levels']['entry_premium']}")
        print(f" Premium Stop-Loss: ₹ {plan['premium_levels']['stop_loss_premium']} (Risk: ₹{plan['premium_levels']['risk_per_share']} / share)")
        print(f" Premium Target:    ₹ {plan['premium_levels']['target_premium']} (Gain: ₹{plan['premium_levels']['reward_per_share']} / share)")
        print(f" Reward-to-Risk:    {plan['premium_levels']['reward_risk_ratio']}R")
        print("-" * 70)
        print(f" Position Sizing:   {plan['position_sizing']['lots']} Lot(s) ({plan['position_sizing']['total_qty']} Qty)")
        print(f" Capital Required:  ₹ {plan['position_sizing']['capital_required_inr']:,.2f}")
        print(f" Max Risk:          ₹ {plan['position_sizing']['max_loss_inr']:,.2f}")
        print(f" Expected Gross:    ₹ {plan['position_sizing']['gross_profit_inr']:,.2f}")
        print(f" Statutory Fees:    ₹ {plan['position_sizing']['statutory_fees_inr']:,.2f} (0.1% STT + GST + Brokerage)")
        print(f" Net Realized Gain: ₹ {plan['position_sizing']['net_profit_inr']:,.2f} (Net R:R: {plan['position_sizing']['net_reward_risk_ratio']:.2f}R)")
        print("-" * 70)
        print(f" ⏳ Theta Risk:      ₹ {plan['theta_momentum_rules']['hourly_decay_cost_inr']:,.2f} / hour decay")
        print(f" ⚠️ Momentum Rule:   {plan['theta_momentum_rules']['rule']}")
        print("=" * 70)
    else:
        p.print_help()


if __name__ == "__main__":
    main()
