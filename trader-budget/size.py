#!/usr/bin/env python3
"""Position Sizing and Budget Manager for Indian Equities (trader-budget). Standard library only.

Sizes ONE day trade from trader/plan.json to your INR budget and max loss per trade,
then writes a structured order (entry, stop-loss, take-profit) to trader/orders.json.
Enforces SEBI 5x MIS leverage and strictly whole integer shares (no fractional shares).

    python3 size.py                                  # trader/plan.json + trader/config.json
    python3 size.py --write                          # write trader/orders.json
    python3 size.py --limit 2950.00 --write          # limit order at 2950.00
"""

import argparse
import datetime
import json
import math
import os
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
    "product_type": "MIS",
    "mis_leverage": 5.0,
    "exchange": "NSE"
}


class BudgetError(Exception):
    pass


def load_json(path, default=None):
    if os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return default


def calculate_position_size(plan, cfg, portfolio=None):
    sym = plan["symbol"]
    entry = float(plan["entry"])
    stop = float(plan["stop"])
    target = float(plan["target"])
    risk_per_share = abs(entry - stop)
    
    if risk_per_share <= 0:
        raise BudgetError(f"Invalid risk per share: {risk_per_share}")
        
    budget = float(cfg.get("budget", 100000))
    cash_buffer_pct = float(cfg.get("cash_buffer_pct", 10))
    cash_buffer = budget * (cash_buffer_pct / 100.0)
    
    cash = float((portfolio or {}).get("cash", budget))
    available_cash = max(0.0, cash - cash_buffer)
    
    leverage = float(cfg.get("mis_leverage", 5.0)) if cfg.get("product_type", "MIS") == "MIS" else 1.0
    buying_power = available_cash * leverage
    
    # 1. Max loss limit constraint
    max_loss_inr = float(cfg.get("max_loss_per_trade_inr", 1000))
    shares_by_risk = math.floor(max_loss_inr / risk_per_share)
    
    # 2. Position value cap constraint
    max_pos_pct = float(cfg.get("max_position_pct", 50))
    max_pos_val = budget * (max_pos_pct / 100.0)
    shares_by_pos_cap = math.floor(max_pos_val / entry)
    
    # 3. Max order value constraint
    max_order_inr = float(cfg.get("max_order_inr", 80000))
    shares_by_max_order = math.floor(max_order_inr / entry)
    
    # 4. Buying power constraint
    shares_by_cash = math.floor(buying_power / entry)
    
    # Final whole integer shares (the smallest of all limits)
    qty = max(0, min(shares_by_risk, shares_by_pos_cap, shares_by_max_order, shares_by_cash))
    
    order_val = round(qty * entry, 2)
    margin_needed = round(order_val / leverage, 2)
    actual_loss_at_stop = round(qty * risk_per_share, 2)
    expected_profit_at_target = round(qty * abs(target - entry), 2)
    
    if qty <= 0:
        reasons = []
        if shares_by_risk <= 0:
            reasons.append(f"Stop distance (₹{risk_per_share:.2f}) is too wide for your max loss (₹{max_loss_inr:.2f})")
        if shares_by_cash <= 0:
            reasons.append("Insufficient available cash above the cash buffer")
        raise BudgetError("Position size evaluated to 0 shares: " + "; ".join(reasons))
        
    order = {
        "symbol": sym,
        "exchange": "NSE",
        "side": "BUY",
        "qty": qty,
        "product_type": cfg.get("product_type", "MIS"),
        "type": "limit",
        "limit_price": entry,
        "stop_loss_trigger": stop,
        "take_profit_target": target,
        "order_class": "bracket",
        "order_value": order_val,
        "margin_required": margin_needed,
        "max_loss_inr": actual_loss_at_stop,
        "target_profit_inr": expected_profit_at_target,
        "plan": plan
    }
    
    return order, {
        "shares_by_risk": shares_by_risk,
        "shares_by_pos_cap": shares_by_pos_cap,
        "shares_by_max_order": shares_by_max_order,
        "shares_by_cash": shares_by_cash
    }


def main():
    p = argparse.ArgumentParser(description="Position Sizing for Indian Equities")
    p.add_argument("--plan", default="trader/plan.json")
    p.add_argument("--config", default="trader/config.json")
    p.add_argument("--portfolio", default="trader/portfolio.json")
    p.add_argument("--limit", type=float, help="Override limit entry price")
    p.add_argument("--write", action="store_true", help="Write to trader/orders.json")
    p.add_argument("--json", action="store_true", help="Output JSON order")
    
    args = p.parse_args()
    
    if not os.path.exists(args.plan):
        print(f"Plan file not found: {args.plan}")
        return 1
        
    plan = load_json(args.plan)
    if args.limit:
        plan["entry"] = args.limit
        
    cfg = {**DEFAULTS, **(load_json(args.config, {}))}
    portfolio = load_json(args.portfolio)
    
    try:
        order, limits = calculate_position_size(plan, cfg, portfolio)
    except BudgetError as e:
        print(f"❌ Sizing Refused: {e}")
        return 1
        
    print("=" * 65)
    print(f" POSITION SIZING (NSE): {order['symbol']}")
    print("=" * 65)
    print(f"  Allocated Shares:     {order['qty']} shares (Whole integer)")
    print(f"  Order Value:          ₹ {order['order_value']:,.2f}")
    print(f"  Margin Required (5x): ₹ {order['margin_required']:,.2f} ({order['product_type']})")
    print(f"  Entry Price:          ₹ {order['limit_price']:,.2f}")
    print(f"  Stop-Loss:            ₹ {order['stop_loss_trigger']:,.2f}")
    print(f"  Target:               ₹ {order['take_profit_target']:,.2f}")
    print(f"  Max Loss at Stop:     ₹ {order['max_loss_inr']:,.2f} (Limit: ₹{cfg['max_loss_per_trade_inr']:,.2f})")
    print(f"  Expected Gain:        ₹ {order['target_profit_inr']:,.2f}")
    print("=" * 65)
    
    if args.write:
        os.makedirs("trader", exist_ok=True)
        with open("trader/orders.json", "w", encoding="utf-8") as f:
            json.dump({"orders": [order], "created_at": datetime.datetime.now().isoformat()}, f, indent=2)
        print("Written to trader/orders.json")
        
    if args.json:
        print(json.dumps(order, indent=2))
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
