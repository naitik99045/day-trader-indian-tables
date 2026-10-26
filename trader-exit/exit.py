#!/usr/bin/env python3
"""Exit Planner for Indian Equities (trader-exit). Standard library only.

Sets the stop-loss and the profit target BEFORE you enter, so you know exactly when to get out.
Long side only. Enforces the 15:15 IST intraday auto-square-off cutoff. It never places an order.

    python3 exit.py plan                                    # From trader/entry.json: or-mid stop, 2R target
    python3 exit.py plan --stop or-mid --target 1.5R --write # -> trader/plan.json
    python3 exit.py plan --symbol RELIANCE.NS --entry 2950 --or-high 2940 --or-low 2910
    python3 exit.py show                                    # Displays current trader/plan.json
"""

import argparse
import datetime
import json
import math
import os
import sys

DEFAULT_FLAT_BY = "15:15"  # Indian brokers auto-square off between 15:15 and 15:25 IST


class ExitError(Exception):
    pass


def load_entry(path="trader/entry.json"):
    if not os.path.exists(path):
        raise ExitError(f"No entry found at {path}. Run trader-entry or pass --symbol and --entry.")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def calculate_plan(sym, entry, or_high=None, or_low=None, stop_rule="or-mid", target_rule="2R", flat_by=DEFAULT_FLAT_BY):
    entry = float(entry)
    
    # 1. Stop Calculation
    if stop_rule == "or-mid":
        if or_high is None or or_low is None:
            raise ExitError("or-mid stop requires or_high and or_low")
        stop = (float(or_high) + float(or_low)) / 2.0
    elif stop_rule == "or-low":
        if or_low is None:
            raise ExitError("or-low stop requires or_low")
        stop = float(or_low)
    elif stop_rule.startswith("pct:"):
        pct = float(stop_rule.split(":")[1])
        stop = entry * (1.0 - (pct / 100.0))
    elif stop_rule.startswith("price:"):
        stop = float(stop_rule.split(":")[1])
    else:
        try:
            stop = float(stop_rule)
        except ValueError:
            raise ExitError(f"Unknown stop rule: {stop_rule}")
            
    # Round down to nearest 5 paise (tick size 0.05 on NSE)
    stop = math.floor(stop * 20.0) / 20.0
    
    if stop >= entry:
        raise ExitError(f"Stop price (₹{stop:.2f}) must be strictly below entry price (₹{entry:.2f})")
        
    risk_per_share = round(entry - stop, 2)
    if risk_per_share < (entry * 0.0005):
        raise ExitError(f"Risk per share (₹{risk_per_share:.2f}) is too tight to survive spread (< 0.05%)")
        
    # 2. Target Calculation
    if target_rule.endswith("R"):
        r_mult = float(target_rule[:-1])
        target = entry + (r_mult * risk_per_share)
    elif target_rule.startswith("price:"):
        target = float(target_rule.split(":")[1])
    else:
        try:
            target = float(target_rule)
        except ValueError:
            raise ExitError(f"Unknown target rule: {target_rule}")
            
    # Round up to nearest 5 paise
    target = math.ceil(target * 20.0) / 20.0
    
    reward_per_share = round(target - entry, 2)
    rr_ratio = round(reward_per_share / risk_per_share, 2)
    
    return {
        "symbol": sym,
        "entry": round(entry, 2),
        "stop": round(stop, 2),
        "target": round(target, 2),
        "risk_per_share": risk_per_share,
        "reward_per_share": reward_per_share,
        "reward_risk_ratio": rr_ratio,
        "stop_rule": stop_rule,
        "target_rule": target_rule,
        "flat_by": flat_by,
        "exchange": "NSE",
        "created_at": datetime.datetime.now().isoformat()
    }


def main():
    p = argparse.ArgumentParser(description="Exit Planner for Indian Equities")
    sub = p.add_subparsers(dest="command")
    
    s_plan = sub.add_parser("plan", help="Generate an exit plan")
    s_plan.add_argument("--symbol")
    s_plan.add_argument("--entry", type=float)
    s_plan.add_argument("--or-high", type=float)
    s_plan.add_argument("--or-low", type=float)
    s_plan.add_argument("--stop", default="or-mid")
    s_plan.add_argument("--target", default="2R")
    s_plan.add_argument("--flat-by", default=DEFAULT_FLAT_BY)
    s_plan.add_argument("--write", action="store_true", help="Write to trader/plan.json")
    
    s_show = sub.add_parser("show", help="Show current plan")
    
    args = p.parse_args()
    
    if args.command == "plan":
        if args.symbol and args.entry:
            sym = args.symbol
            entry = args.entry
            or_h = args.or_high
            or_l = args.or_low
        else:
            e = load_entry()
            sym = e.get("symbol")
            entry = e.get("entry")
            or_h = e.get("or_high")
            or_l = e.get("or_low")
            
        plan = calculate_plan(sym, entry, or_h, or_l, args.stop, args.target, args.flat_by)
        
        print("=" * 60)
        print(f" TRADE EXIT PLAN (NSE): {plan['symbol']}")
        print("=" * 60)
        print(f"  Entry Price:       ₹ {plan['entry']:,.2f}")
        print(f"  Stop-Loss:         ₹ {plan['stop']:,.2f} ({plan['stop_rule']})")
        print(f"  Target:            ₹ {plan['target']:,.2f} ({plan['target_rule']})")
        print(f"  Risk / Share:      ₹ {plan['risk_per_share']:,.2f}")
        print(f"  Reward / Share:    ₹ {plan['reward_per_share']:,.2f}")
        print(f"  Reward:Risk Ratio: {plan['reward_risk_ratio']:.2f}R")
        print(f"  Intraday Flat By:  {plan['flat_by']} IST (Mandatory Square-off)")
        print("=" * 60)
        
        if args.write:
            os.makedirs("trader", exist_ok=True)
            with open("trader/plan.json", "w", encoding="utf-8") as f:
                json.dump(plan, f, indent=2)
            print("Saved to trader/plan.json")
        return 0
    elif args.command == "show":
        if not os.path.exists("trader/plan.json"):
            print("No active plan in trader/plan.json")
            return 1
        with open("trader/plan.json", "r", encoding="utf-8") as f:
            print(f.read())
        return 0
    else:
        p.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
