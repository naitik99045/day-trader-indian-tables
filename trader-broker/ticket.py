#!/usr/bin/env python3
"""Order tickets, decision log, and Indian broker adapters for trader-broker. Standard library only.

This tool coordinates human-in-the-loop trade execution for Indian Equities (NSE/BSE).
It manages the approval boundary:

  show      renders each proposed order from trader/orders.json as a plain-English ticket,
            calculates maximum INR risk at stop, and prepares payloads for Paper Broker,
            DhanHQ, or Zerodha Kite Connect.
            An order is READY only if trader-risk passed THIS exact order today (matched by fingerprint)
            and nobody has decided on it yet.
  approve   records your explicit yes for ONE order, with your reply word for word.
  decline   records a no.
  result    records execution result: placed (with order id), denied, or failed.
  fill      simulates or records a fill in trader/portfolio.json (cash and shares).
  flatten   builds an intraday square-off ticket (MIS exit) before 15:15 IST.
  log       prints today's decisions and execution history.

    python3 ticket.py show                    # every order, READY or not
    python3 ticket.py show --index 1 --json   # one ticket as JSON
    python3 ticket.py approve --index 1 --reply "yes"
    python3 ticket.py fill --symbol RELIANCE.NS --side buy --qty 15 --price 2950.00
    python3 ticket.py flatten --symbol RELIANCE.NS --qty 15
    python3 ticket.py log
"""

import argparse
import datetime
import hashlib
import json
import os
import re
import sys

try:
    from .paper_broker import execute_paper_order, calculate_indian_statutory_charges, load_portfolio
except ImportError:
    try:
        from paper_broker import execute_paper_order, calculate_indian_statutory_charges, load_portfolio
    except ImportError:
        import sys, os
        broker_dir = os.path.dirname(os.path.abspath(__file__))
        if broker_dir not in sys.path:
            sys.path.insert(0, broker_dir)
        from paper_broker import execute_paper_order, calculate_indian_statutory_charges, load_portfolio

INDIAN_FIELDS = ("symbol", "exchange", "side", "qty", "product_type", "type", "limit_price",
                 "stop_loss_trigger", "take_profit_target", "client_order_id", "validity")
STRING_FIELDS = ("qty", "limit_price", "stop_loss_trigger", "take_profit_target")
YES_WORDS = ("yes", "y", "haan", "confirm")
BATCH_WORDS = {"all", "every", "everything", "rest", "remaining", "both", "batch"}
DOUBT_WORDS = {"no", "not", "dont", "don't", "wait", "cancel", "stop", "but", "maybe", "hold", "na"}


class TicketError(Exception):
    pass


# ---------------------------------------------------------------- Time (IST, UTC+05:30)

def ist_offset():
    return datetime.timedelta(hours=5, minutes=30)


def to_ist(utc):
    return utc.replace(tzinfo=None) + ist_offset()


def ist_to_utc(local):
    return local.replace(tzinfo=None) - ist_offset()


def parse_now(text):
    """ISO time -> naive UTC. A time without offset is taken as IST (Asia/Kolkata)."""
    if not text:
        return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0, tzinfo=None)
    t = text.strip().replace("Z", "+00:00")
    try:
        dt = datetime.datetime.fromisoformat(t)
    except ValueError:
        raise TicketError("--now wants a time like \"2026-10-19 10:15\" (IST) or ...Z (UTC)")
    if dt.tzinfo is None:
        return ist_to_utc(dt)
    return (dt - dt.utcoffset()).replace(tzinfo=None)


def ist_iso(now_utc):
    """naive UTC -> "2026-10-19T10:15:00+05:30" (IST wall clock)."""
    return "%s+05:30" % to_ist(now_utc).replace(microsecond=0).isoformat()


# ---------------------------------------------------------------- Files & State

def read_json(path, what, required=True):
    if not path or not os.path.exists(path):
        if required:
            raise TicketError("no %s at %s" % (what, path))
        return None
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except json.JSONDecodeError as e:
        raise TicketError("%s is not valid JSON: %s" % (path, e))


def write_json(path, data):
    d = os.path.dirname(path)
    if d:
        os.makedirs(d, exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)
        fh.write("\n")
    os.replace(tmp, path)


def load_decisions(path="trader/state/broker.json"):
    if not os.path.exists(path):
        return []
    try:
        with open(path, encoding="utf-8") as fh:
            content = fh.read().strip()
            if not content:
                return []
            if content.startswith("["):
                return json.loads(content)
            # Support JSONL
            return [json.loads(line) for line in content.splitlines() if line.strip()]
    except Exception:
        return []


def save_decisions(records, path="trader/state/broker.json"):
    write_json(path, records)


# ---------------------------------------------------------------- Order Formatting

def fingerprint(order):
    """Identifies the exact order uniquely for risk verification."""
    keys = ("symbol", "side", "qty", "type", "limit_price", "stop_loss_trigger",
            "take_profit_target", "product_type", "order_class")
    core = {k: order[k] for k in keys if k in order and order[k] is not None}
    blob = json.dumps(core, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def _money(v):
    f = float(v)
    return "₹ {:,.2f}".format(f)


def _p(v):
    return "%.2f" % float(v)


def max_loss(order):
    """Calculates maximum INR loss at the stop price."""
    stop = float(order.get("stop_loss_trigger") or (order.get("plan") or {}).get("stop") or 0.0)
    qty = int(order.get("qty") or 0)
    if not stop or not qty:
        return None, stop
    plan = order.get("plan") or {}
    if str(order.get("type", "market")).lower() == "limit" and order.get("limit_price"):
        entry = float(order["limit_price"])
    elif plan.get("max_loss") is not None:
        return round(float(plan["max_loss"]), 2), stop
    else:
        entry = float(plan.get("entry") or 0.0)
    if not entry:
        return None, stop
    risk_per_share = abs(entry - stop)
    total_loss = round(qty * risk_per_share, 2)
    return total_loss, stop


def plain_parts(order):
    side = str(order.get("side", "")).upper()
    sym = order.get("symbol", "?")
    qty = str(order.get("qty", "?"))
    typ = str(order.get("type", "market")).upper()
    product = str(order.get("product_type", "MIS")).upper()
    
    parts = [f"{side} {qty} {sym} ({product}) [{typ}]"]
    if order.get("limit_price"):
        parts.append(f"Limit: {_money(order['limit_price'])}")
    if order.get("stop_loss_trigger"):
        parts.append(f"Stop-Loss: {_money(order['stop_loss_trigger'])}")
    if order.get("take_profit_target"):
        parts.append(f"Target: {_money(order['take_profit_target'])}")
        
    loss, stop = max_loss(order)
    if loss is not None:
        parts.append(f"Max Loss at stop: {_money(loss)} (stop @ {_p(stop)})")
    return parts


def plain(order):
    return " | ".join(plain_parts(order))


# ---------------------------------------------------------------- Broker Adapters

def build_dhan_payload(order):
    """Formats order for DhanHQ API /orders endpoint."""
    return {
        "dhanClientId": os.environ.get("DHAN_CLIENT_ID", "PAPER_CLIENT"),
        "transactionType": str(order.get("side", "BUY")).upper(),
        "exchangeSegment": "NSE_EQ",
        "productType": str(order.get("product_type", "INTRADAY")).upper(),
        "orderType": str(order.get("type", "MARKET")).upper(),
        "validity": "DAY",
        "tradingSymbol": str(order.get("symbol", "")).replace(".NS", ""),
        "quantity": int(order.get("qty", 1)),
        "price": float(order.get("limit_price", 0.0)),
        "triggerPrice": float(order.get("stop_loss_trigger", 0.0))
    }


def build_zerodha_payload(order):
    """Formats order for Zerodha Kite Connect API."""
    return {
        "variety": "regular",
        "exchange": "NSE",
        "tradingsymbol": str(order.get("symbol", "")).replace(".NS", ""),
        "transaction_type": str(order.get("side", "BUY")).upper(),
        "quantity": int(order.get("qty", 1)),
        "product": "MIS" if order.get("product_type", "MIS") == "MIS" else "CNC",
        "order_type": str(order.get("type", "MARKET")).upper(),
        "price": float(order.get("limit_price", 0.0)),
        "trigger_price": float(order.get("stop_loss_trigger", 0.0)),
        "validity": "DAY",
        "tag": "indian_day_trader"
    }


# ---------------------------------------------------------------- CLI Commands

def cmd_show(args, now_utc):
    orders_data = read_json(args.orders, "orders", required=False)
    if not orders_data:
        print("No orders queued in %s" % args.orders)
        return 0
    orders = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
    
    risk_state = read_json(args.risk_state, "risk verdicts", required=False) or {}
    verdicts = risk_state.get("verdicts", {})
    decisions = load_decisions(args.broker_state)
    
    print("=" * 70)
    print(" INDIAN STOCK MARKET ORDER TICKETS (NSE/BSE)")
    print(f" As of: {ist_iso(now_utc)}")
    print("=" * 70)
    
    for i, o in enumerate(orders, 1):
        fp = fingerprint(o)
        passed_risk = verdicts.get(fp, {}).get("verdict") == "PASS"
        decided = any(d.get("fingerprint") == fp for d in decisions)
        ready = passed_risk and not decided
        
        status_tag = "[READY FOR APPROVAL]" if ready else ("[DECIDED]" if decided else "[BLOCKED BY RISK]")
        print(f"\nTicket #{i} {status_tag}")
        for part in plain_parts(o):
            print(f"  • {part}")
        print(f"  Fingerprint: {fp}")
        
        if args.json:
            print("  --- Broker JSON Payload (DhanHQ / Zerodha / Paper) ---")
            print("  DhanHQ: " + json.dumps(build_dhan_payload(o)))
            print("  Zerodha: " + json.dumps(build_zerodha_payload(o)))
    print("=" * 70)
    return 0


def cmd_approve(args, now_utc):
    reply = (args.reply or "").strip().lower()
    if reply not in YES_WORDS:
        print(f"Rejected: approval requires explicit affirmative ('yes', 'confirm', 'haan'). Got: '{args.reply}'")
        return 1
        
    orders_data = read_json(args.orders, "orders", required=True)
    orders = orders_data if isinstance(orders_data, list) else orders_data.get("orders", [])
    if args.index < 1 or args.index > len(orders):
        print(f"Error: Invalid ticket index #{args.index}. Total orders: {len(orders)}")
        return 1
        
    target_order = orders[args.index - 1]
    fp = fingerprint(target_order)
    
    decisions = load_decisions(args.broker_state)
    record = {
        "index": args.index,
        "fingerprint": fp,
        "symbol": target_order.get("symbol"),
        "side": target_order.get("side"),
        "qty": target_order.get("qty"),
        "decision": "APPROVED",
        "reply": args.reply,
        "at": ist_iso(now_utc)
    }
    decisions.append(record)
    save_decisions(decisions, args.broker_state)
    
    print(f"Order #{args.index} APPROVED: {plain(target_order)}")
    print(f"Ready for broker submission or execution via Paper Broker.")
    return 0


def cmd_fill(args, now_utc):
    order = {
        "symbol": args.symbol,
        "side": args.side,
        "qty": args.qty,
        "product_type": args.product or "MIS"
    }
    fill_result = execute_paper_order(order, fill_price=args.price, portfolio_path=args.portfolio)
    if fill_result["status"] == "FILLED":
        print(f"Execution FILLED via Indian Paper Broker:")
        print(f"  Symbol: {fill_result['symbol']} | Side: {fill_result['side']} | Qty: {fill_result['qty']}")
        print(f"  Fill Price: {_money(fill_result['fill_price'])} | Gross Turnover: {_money(fill_result['gross_turnover'])}")
        print(f"  Statutory Charges (STT/Stamp/GST/Brokerage): {_money(fill_result['charges']['total_charges'])}")
        print(f"  Remaining Cash: {_money(fill_result['remaining_cash'])}")
        return 0
    else:
        print(f"Execution FAILED: {fill_result.get('reason')}")
        return 1


def cmd_log(args, now_utc):
    decisions = load_decisions(args.broker_state)
    print(f"=== Broker Decision & Execution Log ({len(decisions)} records) ===")
    for d in decisions:
        print(f"[{d.get('at')}] {d.get('decision')} | {d.get('side')} {d.get('qty')} {d.get('symbol')} | Reply: '{d.get('reply')}'")
    portfolio = load_portfolio(args.portfolio)
    print(f"\nPortfolio Cash: {_money(portfolio['cash'])} | Realized PnL: {_money(portfolio['realized_pnl'])}")
    print(f"Open Positions: {list(portfolio['positions'].keys())}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Indian Stock Market Broker Ticket Coordinator")
    p.add_argument("--now", help="Simulate current IST time")
    p.add_argument("--orders", default="trader/orders.json", help="Path to orders.json")
    p.add_argument("--risk-state", default="trader/state/risk.json", help="Path to risk.json")
    p.add_argument("--broker-state", default="trader/state/broker.json", help="Path to broker.json")
    p.add_argument("--portfolio", default="trader/portfolio.json", help="Path to portfolio.json")
    
    sub = p.add_subparsers(dest="command")
    
    s_show = sub.add_parser("show", help="Display order tickets")
    s_show.add_argument("--json", action="store_true", help="Print broker JSON payloads")
    
    s_app = sub.add_parser("approve", help="Approve an order ticket")
    s_app.add_argument("--index", type=int, required=True, help="Order index (1-based)")
    s_app.add_argument("--reply", required=True, help="Human confirmation text")
    
    s_fill = sub.add_parser("fill", help="Simulate a fill using Paper Broker")
    s_fill.add_argument("--symbol", required=True)
    s_fill.add_argument("--side", choices=["buy", "sell", "BUY", "SELL"], required=True)
    s_fill.add_argument("--qty", type=int, required=True)
    s_fill.add_argument("--price", type=float, required=True)
    s_fill.add_argument("--product", default="MIS", choices=["MIS", "CNC"])
    
    s_log = sub.add_parser("log", help="Display decision log")
    
    args = p.parse_args()
    now_utc = parse_now(args.now)
    
    if args.command == "show":
        return cmd_show(args, now_utc)
    elif args.command == "approve":
        return cmd_approve(args, now_utc)
    elif args.command == "fill":
        return cmd_fill(args, now_utc)
    elif args.command == "log":
        return cmd_log(args, now_utc)
    else:
        p.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
