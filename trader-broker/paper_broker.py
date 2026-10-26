#!/usr/bin/env python3
"""Standalone Indian Paper Broker Simulation Engine. Standard library only.

Simulates order execution for Indian Cash Equity (NSE/BSE) with:
- MIS (Margin Intraday Square-off) with 5x leverage & CNC (Delivery).
- Real-world statutory charge calculation (STT, Exchange, SEBI, Stamp Duty, GST, Brokerage).
- Slippage model for market orders (0.05% realistic intraday equity slippage).
- Real-time updates to trader/portfolio.json and trader/state/broker.json.
"""

import datetime
import json
import math
import os
import sys

DEFAULT_INITIAL_CASH = 100000.0  # ₹ 1,00,000 INR starting capital


def get_ist_now():
    utc = datetime.datetime.now(datetime.timezone.utc)
    ist = utc + datetime.timedelta(hours=5, minutes=30)
    return ist.replace(tzinfo=None)


def calculate_indian_statutory_charges(side, price, qty, product="MIS", brokerage_per_order=20.0, brokerage_pct=0.03):
    """Computes exact SEBI & Exchange statutory transaction friction in INR.
    - Brokerage: min(20.0, 0.03% * turnover)
    - STT (Securities Transaction Tax): 0.025% on sell side for intraday MIS; 0.1% both sides for CNC.
    - Exchange txn charge: 0.00297% (NSE equity)
    - SEBI Turnover fee: ₹10 per crore (0.0001%)
    - Stamp duty: 0.003% on buy side
    - GST: 18% on (brokerage + exchange charges + SEBI fee)
    """
    turnover = float(price) * int(qty)
    brokerage = min(brokerage_per_order, round((brokerage_pct / 100.0) * turnover, 2))
    
    if product.upper() == "MIS":
        stt = round(0.00025 * turnover, 2) if side.upper() == "SELL" else 0.0
    else:  # CNC
        stt = round(0.001 * turnover, 2)
        
    exchange_charges = round(0.0000297 * turnover, 2)
    sebi_charges = round(0.000001 * turnover, 2)
    stamp_duty = round(0.00003 * turnover, 2) if side.upper() == "BUY" else 0.0
    gst = round(0.18 * (brokerage + exchange_charges + sebi_charges), 2)
    
    total_charges = round(brokerage + stt + exchange_charges + sebi_charges + stamp_duty + gst, 2)
    
    return {
        "turnover": round(turnover, 2),
        "brokerage": brokerage,
        "stt": stt,
        "exchange_charges": exchange_charges,
        "sebi_charges": sebi_charges,
        "stamp_duty": stamp_duty,
        "gst": gst,
        "total_charges": total_charges
    }


def load_portfolio(path="trader/portfolio.json"):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "currency": "INR",
        "cash": DEFAULT_INITIAL_CASH,
        "initial_capital": DEFAULT_INITIAL_CASH,
        "positions": {},
        "realized_pnl": 0.0,
        "total_charges_paid": 0.0,
        "trades_count": 0,
        "updated_at": get_ist_now().isoformat()
    }


def save_portfolio(portfolio, path="trader/portfolio.json"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    portfolio["updated_at"] = get_ist_now().isoformat()
    with open(path + ".tmp", "w", encoding="utf-8") as f:
        json.dump(portfolio, f, indent=2)
    os.replace(path + ".tmp", path)


def execute_paper_order(order, fill_price, slippage_pct=0.0005, portfolio_path="trader/portfolio.json"):
    """Fills an approved order against the simulated paper broker."""
    portfolio = load_portfolio(portfolio_path)
    side = str(order.get("side", "")).upper()
    sym = str(order.get("symbol", "")).upper()
    qty = int(order.get("qty", 0))
    product = str(order.get("product_type", "MIS")).upper()
    
    if qty <= 0:
        return {"status": "REJECTED", "reason": "Quantity must be greater than zero"}
        
    # Apply simulated slippage
    if side == "BUY":
        effective_price = round(fill_price * (1.0 + slippage_pct), 2)
    else:
        effective_price = round(fill_price * (1.0 - slippage_pct), 2)
        
    charges = calculate_indian_statutory_charges(side, effective_price, qty, product=product)
    gross_amount = charges["turnover"]
    net_cost = gross_amount + charges["total_charges"] if side == "BUY" else gross_amount - charges["total_charges"]
    
    # Margin calculation: MIS provides 5x leverage (20% margin required)
    margin_required = (gross_amount / 5.0) if product == "MIS" else gross_amount
    
    if side == "BUY":
        if portfolio["cash"] < (margin_required + charges["total_charges"]):
            return {
                "status": "REJECTED",
                "reason": f"Insufficient INR cash. Required ₹{margin_required + charges['total_charges']:.2f}, Available ₹{portfolio['cash']:.2f}"
            }
            
        portfolio["cash"] = round(portfolio["cash"] - (margin_required if product == "MIS" else gross_amount) - charges["total_charges"], 2)
        pos = portfolio["positions"].get(sym, {"qty": 0, "avg_price": 0.0, "product": product})
        new_qty = pos["qty"] + qty
        new_avg = round(((pos["qty"] * pos["avg_price"]) + (qty * effective_price)) / new_qty, 2)
        portfolio["positions"][sym] = {
            "qty": new_qty,
            "avg_price": new_avg,
            "product": product,
            "margin_blocked": round(pos.get("margin_blocked", 0.0) + margin_required, 2)
        }
    else:  # SELL
        pos = portfolio["positions"].get(sym, {"qty": 0, "avg_price": 0.0, "product": product})
        if pos["qty"] < qty and product != "MIS":
            return {"status": "REJECTED", "reason": f"Cannot sell {qty} shares of {sym}, currently holding {pos['qty']}"}
            
        realized = round((effective_price - pos["avg_price"]) * qty - charges["total_charges"], 2)
        portfolio["realized_pnl"] = round(portfolio["realized_pnl"] + realized, 2)
        
        # Release blocked margin & credit PnL
        margin_to_release = min(pos.get("margin_blocked", 0.0), (pos["avg_price"] * qty) / 5.0 if product == "MIS" else (pos["avg_price"] * qty))
        portfolio["cash"] = round(portfolio["cash"] + margin_to_release + realized, 2)
        
        remaining_qty = pos["qty"] - qty
        if remaining_qty <= 0:
            portfolio["positions"].pop(sym, None)
        else:
            pos["qty"] = remaining_qty
            pos["margin_blocked"] = round(max(0.0, pos.get("margin_blocked", 0.0) - margin_to_release), 2)
            portfolio["positions"][sym] = pos

    portfolio["total_charges_paid"] = round(portfolio["total_charges_paid"] + charges["total_charges"], 2)
    portfolio["trades_count"] += 1
    save_portfolio(portfolio, portfolio_path)
    
    return {
        "status": "FILLED",
        "symbol": sym,
        "side": side,
        "qty": qty,
        "fill_price": effective_price,
        "gross_turnover": gross_amount,
        "charges": charges,
        "net_cash_impact": net_cost,
        "remaining_cash": portfolio["cash"],
        "timestamp": get_ist_now().isoformat()
    }


if __name__ == "__main__":
    p = load_portfolio()
    print(f"Indian Paper Broker Initialized | Balance: ₹ {p['cash']:,.2f}")
