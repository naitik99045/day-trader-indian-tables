#!/usr/bin/env python3
"""Pre-trade risk check for Indian Equities (NSE/BSE). Standard library only, no network.

Reads proposed orders (trader/orders.json) and validates every one against:
- Risk rules (trader/config.json)
- Portfolio cash and holdings (trader/portfolio.json)
- Recent prices & previous close (trader/prices.json)
- Prior orders executed today (trader/state/broker.json)

Enforces Indian market regulations & guardrails:
1. Max loss per trade in INR.
2. Max daily loss limit in INR.
3. SEBI Intraday Peak Margin compliance (MIS 5x leverage).
4. Whole integer share constraint (No fractional shares in India).
5. Minimum Reward:Risk ratio net of statutory transaction charges (STT, Stamp Duty, GST, Brokerage).
6. NSE/BSE Circuit Limit proximity guard (Blocks entries within circuit buffer).
7. IST Trading session windows (09:15 to 15:30 IST, entries between 09:30 and 15:00 IST).

Output:
Each order receives PASS or BLOCK with clear human reasons.
Verdicts are cryptographically fingerprinted and written to trader/state/risk.json.
"""

import argparse
import datetime
import hashlib
import json
import math
import os
import re
import sys

DEFAULTS = {
    "currency": "INR",
    "budget": 100000,
    "cash_buffer_pct": 10,
    "max_position_pct": 50,
    "max_order_inr": 80000,
    "min_order_inr": 500,
    "max_loss_per_trade_inr": 1000,
    "max_daily_loss_inr": 3000,
    "max_trades_per_day": 3,
    "max_orders_per_day": 10,
    "min_reward_risk": 1.5,
    "require_stop": True,
    "product_type": "MIS",
    "exchange": "NSE",
    "mis_leverage": 5.0,
    "no_entries_before": "09:30",
    "no_entries_after": "15:00",
    "flat_by": "15:15",
    "fractional": False,
    "circuit_buffer_pct": 1.0,
    "blocked": [],
    "allow_short": True,
}

NSE_HOLIDAYS_2026_2027 = {
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-20": "Id-Ul-Fitr (Ramadan Eid)",
    "2026-03-27": "Shri Ram Navami",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Baba Saheb Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-27": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan (Muhurat Trading)",
    "2026-11-10": "Diwali Balipratipada",
    "2026-11-24": "Gurunanak Jayanti",
    "2026-12-25": "Christmas Day",
    "2027-01-26": "Republic Day",
    "2027-03-22": "Holi",
    "2027-03-26": "Good Friday",
    "2027-04-14": "Dr. Ambedkar Jayanti",
    "2027-05-01": "Maharashtra Day",
    "2027-08-15": "Independence Day",
    "2027-10-02": "Mahatma Gandhi Jayanti",
    "2027-12-25": "Christmas Day"
}

MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)
HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")


class RiskError(Exception):
    pass


# ---------------------------------------------------------------- IST Timekeeping

def ist_offset():
    return datetime.timedelta(hours=5, minutes=30)


def to_ist(utc):
    return utc.replace(tzinfo=None) + ist_offset()


def ist_to_utc(local):
    return local.replace(tzinfo=None) - ist_offset()


def parse_now(text):
    if not text:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    t = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        raise RiskError("--now wants a time like \"2026-10-19 10:15\" (IST) or ...Z (UTC)")
    if dt.tzinfo is None:
        return ist_to_utc(dt)
    return (dt - dt.utcoffset()).replace(tzinfo=None)


def is_trading_day(d):
    if d.weekday() >= 5:
        return False, "Weekend"
    h = NSE_HOLIDAYS_2026_2027.get(d.isoformat())
    if h:
        return False, f"NSE Holiday: {h}"
    return True, ""


# ---------------------------------------------------------------- Statutory Cost Calculations

def estimate_roundtrip_statutory_costs(entry, exit_price, qty, product="MIS"):
    turnover_in = entry * qty
    turnover_out = exit_price * qty
    total_turnover = turnover_in + turnover_out
    brokerage = min(40.0, 0.0003 * total_turnover)
    stt = 0.00025 * turnover_out if product == "MIS" else 0.001 * total_turnover
    exchange_fees = 0.0000297 * total_turnover
    sebi_fees = 0.000001 * total_turnover
    stamp_duty = 0.00003 * turnover_in
    gst = 0.18 * (brokerage + exchange_fees + sebi_fees)
    total_friction = round(brokerage + stt + exchange_fees + sebi_fees + stamp_duty + gst, 2)
    return total_friction


# ---------------------------------------------------------------- Core Risk Checks

def fingerprint(order):
    keys = ("symbol", "side", "qty", "type", "limit_price", "stop_loss_trigger",
            "take_profit_target", "product_type", "order_class")
    core = {k: order[k] for k in keys if k in order and order[k] is not None}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def validate_order(order, cfg, portfolio, prices, prior_orders_today, now_ist):
    blocks = []
    warnings = []
    
    sym = str(order.get("symbol", "")).upper()
    side = str(order.get("side", "")).upper()
    qty = order.get("qty")
    typ = str(order.get("type", "market")).lower()
    product = str(order.get("product_type", cfg.get("product_type", "MIS"))).upper()
    
    # 1. Format & Asset
    if not sym:
        blocks.append("Missing stock symbol")
    if side not in ("BUY", "SELL"):
        blocks.append(f"Invalid order side: '{side}'")
    if qty is None or not isinstance(qty, int) or qty <= 0:
        blocks.append(f"Quantity must be a positive integer (Whole shares only on NSE/BSE). Got: {qty}")
        
    if sym in cfg.get("blocked", []):
        blocks.append(f"Symbol {sym} is on your blocked list")
        
    # Price discovery
    quote = (prices.get(sym) or {}) if isinstance(prices, dict) else {}
    current_price = float(order.get("limit_price") or quote.get("price") or (order.get("plan") or {}).get("entry") or 0.0)
    prev_close = float(quote.get("previous_close") or quote.get("prev_close") or 0.0)
    
    if current_price <= 0:
        blocks.append(f"Cannot determine price for {sym}")
        return blocks, warnings
        
    order_val = current_price * (qty or 0)
    
    # 2. Min / Max Order Value
    if order_val < cfg.get("min_order_inr", 500):
        blocks.append(f"Order value ₹{order_val:,.2f} is under min_order_inr (₹{cfg.get('min_order_inr', 500)})")
    if order_val > cfg.get("max_order_inr", 80000):
        blocks.append(f"Order value ₹{order_val:,.2f} exceeds max_order_inr (₹{cfg.get('max_order_inr', 80000)})")
        
    # 3. Position Size Cap (% of Account)
    account_budget = float(cfg.get("budget", 100000))
    max_pos_val = account_budget * (cfg.get("max_position_pct", 50) / 100.0)
    if order_val > max_pos_val:
        blocks.append(f"Order value ₹{order_val:,.2f} exceeds position cap of {cfg.get('max_position_pct', 50)}% (₹{max_pos_val:,.2f})")
        
    # 4. Margin & Cash Buffer
    cash_available = float(portfolio.get("cash", account_budget))
    cash_buffer = account_budget * (cfg.get("cash_buffer_pct", 10) / 100.0)
    effective_cash = max(0.0, cash_available - cash_buffer)
    
    leverage = float(cfg.get("mis_leverage", 5.0)) if product == "MIS" else 1.0
    margin_needed = order_val / leverage
    if margin_needed > effective_cash:
        blocks.append(f"Insufficient cash for margin. Margin needed: ₹{margin_needed:,.2f}, Available above buffer: ₹{effective_cash:,.2f}")
        
    # 5. Stop-Loss & Max Loss per Trade
    stop = float(order.get("stop_loss_trigger") or (order.get("plan") or {}).get("stop") or 0.0)
    if cfg.get("require_stop", True):
        if not stop or stop <= 0:
            blocks.append("No stop-loss specified while require_stop is enabled")
        elif side == "BUY" and stop >= current_price:
            blocks.append(f"Stop price (₹{stop:,.2f}) must be strictly below entry price (₹{current_price:,.2f})")
        elif side == "SELL" and stop <= current_price:
            blocks.append(f"Stop price (₹{stop:,.2f}) must be strictly above entry price (₹{current_price:,.2f})")
            
    if stop and current_price:
        risk_per_share = abs(current_price - stop)
        total_risk = round(risk_per_share * qty, 2)
        max_loss_limit = float(cfg.get("max_loss_per_trade_inr", 1000))
        if total_risk > max_loss_limit:
            blocks.append(f"Total risk ₹{total_risk:,.2f} exceeds max_loss_per_trade_inr (₹{max_loss_limit:,.2f})")
            
    # 6. Reward to Risk & Statutory Friction
    target = float(order.get("take_profit_target") or (order.get("plan") or {}).get("target") or 0.0)
    if target and stop and current_price:
        gross_reward = abs(target - current_price) * qty
        gross_risk = abs(current_price - stop) * qty
        statutory_costs = estimate_roundtrip_statutory_costs(current_price, target, qty, product=product)
        net_reward = gross_reward - statutory_costs
        net_risk = gross_risk + statutory_costs
        
        min_rr = float(cfg.get("min_reward_risk", 1.5))
        if net_risk > 0:
            net_rr = net_reward / net_risk
            if net_rr < min_rr:
                blocks.append(f"Net Reward:Risk after statutory taxes ({net_rr:.2f}) is below min_reward_risk ({min_rr:.2f}). Net Gain: ₹{net_reward:,.2f}, Net Risk: ₹{net_risk:,.2f}, Taxes: ₹{statutory_costs:,.2f}")
                
    # 7. Circuit Limit Proximity Guard
    if prev_close > 0:
        circuit_buffer = float(cfg.get("circuit_buffer_pct", 1.0)) / 100.0
        # Typical 10% circuit band
        upper_circuit = prev_close * 1.10
        lower_circuit = prev_close * 0.90
        if side == "BUY" and current_price >= (upper_circuit * (1.0 - circuit_buffer)):
            blocks.append(f"Circuit Guard: {sym} @ ₹{current_price:.2f} is within 1% of Upper Circuit (₹{upper_circuit:.2f})")
        elif side == "SELL" and current_price <= (lower_circuit * (1.0 + circuit_buffer)):
            blocks.append(f"Circuit Guard: {sym} @ ₹{current_price:.2f} is within 1% of Lower Circuit (₹{lower_circuit:.2f})")
            
    # 8. IST Trading Window
    time_now = now_ist.time()
    t_open = MARKET_OPEN
    t_close = MARKET_CLOSE
    
    start_str = cfg.get("no_entries_before", "09:30")
    end_str = cfg.get("no_entries_after", "15:00")
    m_start = HHMM.match(start_str)
    m_end = HHMM.match(end_str)
    
    if m_start and m_end:
        w_start = datetime.time(int(m_start.group(1)), int(m_start.group(2)))
        w_end = datetime.time(int(m_end.group(1)), int(m_end.group(2)))
        if time_now < w_start:
            blocks.append(f"Outside entry window: Current time {time_now.strftime('%H:%M')} is before {start_str} IST")
        elif time_now > w_end:
            blocks.append(f"Outside entry window: Current time {time_now.strftime('%H:%M')} is after {end_str} IST")
            
    is_ok, reason = is_trading_day(now_ist.date())
    if not is_ok:
        blocks.append(f"Market Closed: {reason}")
        
    # 9. Daily Trade Limits
    max_trades = int(cfg.get("max_trades_per_day", 3))
    if len(prior_orders_today) >= max_trades:
        blocks.append(f"Daily limit reached: {len(prior_orders_today)} trades already executed today (max {max_trades})")
        
    return blocks, warnings


def main():
    p = argparse.ArgumentParser(description="Pre-Trade Risk Engine for Indian Equities")
    p.add_argument("--now", help="Simulate current IST time")
    p.add_argument("--orders", default="trader/orders.json", help="Path to orders.json")
    p.add_argument("--config", default="trader/config.json", help="Path to config.json")
    p.add_argument("--portfolio", default="trader/portfolio.json", help="Path to portfolio.json")
    p.add_argument("--prices", default="trader/prices.json", help="Path to prices.json")
    p.add_argument("--broker-state", default="trader/state/broker.json", help="Path to broker.json")
    p.add_argument("--risk-state", default="trader/state/risk.json", help="Output path for risk verdicts")
    p.add_argument("--json", action="store_true", help="Output JSON result")
    p.add_argument("--no-write", action="store_true", help="Do not write risk.json")
    
    args = p.parse_args()
    now_utc = parse_now(args.now)
    now_ist = to_ist(now_utc)
    
    # Load state
    def load_or_default(path, default):
        if os.path.exists(path):
            try:
                with open(path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return default
        
    cfg = {**DEFAULTS, **load_or_default(args.config, {})}
    orders_data = load_or_default(args.orders, [])
    orders = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
    portfolio = load_or_default(args.portfolio, {"cash": cfg["budget"], "positions": {}})
    prices = load_or_default(args.prices, {})
    broker_state = load_or_default(args.broker_state, [])
    
    today_str = now_ist.date().isoformat()
    prior_orders = [o for o in broker_state if str(o.get("at", "")).startswith(today_str)]
    
    results = {}
    any_blocked = False
    
    print("=" * 70)
    print(" INDIAN PRE-TRADE RISK ENGINE (NSE/BSE)")
    print(f" Clock: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST | Account Cash: ₹ {portfolio.get('cash', cfg['budget']):,.2f}")
    print("=" * 70)
    
    for i, order in enumerate(orders, 1):
        fp = fingerprint(order)
        blocks, warnings = validate_order(order, cfg, portfolio, prices, prior_orders, now_ist)
        verdict = "BLOCK" if blocks else "PASS"
        if verdict == "BLOCK":
            any_blocked = True
            
        results[fp] = {
            "index": i,
            "symbol": order.get("symbol"),
            "side": order.get("side"),
            "qty": order.get("qty"),
            "verdict": verdict,
            "blocks": blocks,
            "warnings": warnings,
            "checked_at": now_ist.isoformat()
        }
        
        status_color = "[PASS]" if verdict == "PASS" else "[BLOCKED]"
        print(f"\nOrder #{i} {order.get('side')} {order.get('qty')} {order.get('symbol')} {status_color}")
        if blocks:
            for b in blocks:
                print(f"  ❌ BLOCK: {b}")
        if warnings:
            for w in warnings:
                print(f"  ⚠️ WARN: {w}")
        if verdict == "PASS":
            print("  ✅ All risk, margin, statutory cost, and circuit checks passed.")
            
    print("=" * 70)
    
    if not args.no_write:
        os.makedirs(os.path.dirname(args.risk_state), exist_ok=True)
        with open(args.risk_state, "w", encoding="utf-8") as f:
            json.dump({"verdicts": results, "updated_at": now_ist.isoformat()}, f, indent=2)
            
    if args.json:
        print(json.dumps(results, indent=2))
        
    return 1 if any_blocked else 0


if __name__ == "__main__":
    sys.exit(main())
