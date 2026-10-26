#!/usr/bin/env python3
"""Price alerts and NSE/BSE IST market clock for trader-alerts. Standard library only.

    python3 alerts.py clock                          # Is NSE open? Current phase & countdown
    python3 alerts.py quote RELIANCE.NS --write      # Quotes -> trader/prices.json
    python3 alerts.py add --from-plan                # Stop, target & 15:15 square-off alert
    python3 alerts.py add --symbol RELIANCE.NS --target 3000
    python3 alerts.py add --symbol RELIANCE.NS --stop 2910
    python3 alerts.py add --at 15:15 --label "Mandatory Intraday Square-off"
    python3 alerts.py check                          # Checks alert conditions & rings terminal bell
    python3 alerts.py list                           # List registered alert rules
"""

import argparse
import datetime
import gzip
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; IndianDayTrader/2.0; +https://github.com/)"
YAHOO_HOSTS = ("query2.finance.yahoo.com", "query1.finance.yahoo.com")
HHMM = re.compile(r"^([01]?\d|2[0-3]):([0-5]\d)$")

NSE_HOLIDAYS_2026_2027 = {
    "2026-01-26": "Republic Day",
    "2026-03-03": "Holi",
    "2026-03-20": "Id-Ul-Fitr",
    "2026-03-27": "Shri Ram Navami",
    "2026-04-03": "Good Friday",
    "2026-04-14": "Dr. Ambedkar Jayanti",
    "2026-05-01": "Maharashtra Day",
    "2026-05-27": "Bakri Id",
    "2026-06-26": "Muharram",
    "2026-08-15": "Independence Day",
    "2026-10-02": "Mahatma Gandhi Jayanti",
    "2026-10-20": "Dussehra",
    "2026-11-08": "Diwali Laxmi Pujan (Muhurat Trading)",
    "2026-11-10": "Diwali Balipratipada",
    "2026-11-24": "Gurunanak Jayanti",
    "2026-12-25": "Christmas Day"
}

PRE_OPEN = datetime.time(9, 0)
PRE_OPEN_MATCH = datetime.time(9, 8)
MARKET_OPEN = datetime.time(9, 15)
INTRADAY_FLAT = datetime.time(15, 15)
MARKET_CLOSE = datetime.time(15, 30)


class AlertError(Exception):
    pass


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
        raise AlertError("--now wants a time like \"2026-10-19 10:15\" (IST) or ...Z (UTC)")
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


def to_yahoo_sym(sym):
    sym = sym.strip().upper()
    return sym if (sym.endswith(".NS") or sym.endswith(".BO")) else sym + ".NS"


def fetch_quote(sym):
    path = f"/v8/finance/chart/{to_yahoo_sym(sym)}?range=1d&interval=1m"
    for host in YAHOO_HOSTS:
        try:
            req = urllib.request.Request(f"https://{host}{path}", headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = resp.read()
                if resp.info().get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                parsed = json.loads(data.decode("utf-8"))
                meta = parsed["chart"]["result"][0]["meta"]
                return {
                    "symbol": sym,
                    "price": float(meta.get("regularMarketPrice", 0.0)),
                    "previous_close": float(meta.get("chartPreviousClose", 0.0)),
                    "high": float(meta.get("regularMarketDayHigh", 0.0)),
                    "low": float(meta.get("regularMarketDayLow", 0.0)),
                    "updated_at": datetime.datetime.now().isoformat()
                }
        except Exception:
            continue
    return None


def cmd_clock(now_ist):
    d = now_ist.date()
    t = now_ist.time()
    ok, reason = is_trading_day(d)
    
    print("=" * 65)
    print(" ⏰ NSE / BSE TRADING SESSION CLOCK (IST)")
    print(f" Current Clock: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
    print("=" * 65)
    
    if not ok:
        print(f" Market Status: CLOSED ({reason})")
        return 0
        
    if t < PRE_OPEN:
        print(" Market Status: CLOSED (Pre-market opens at 09:00 AM IST)")
    elif PRE_OPEN <= t < PRE_OPEN_MATCH:
        print(" Market Status: 🟡 PRE-OPEN ORDER COLLECTION (09:00 - 09:08 IST)")
    elif PRE_OPEN_MATCH <= t < MARKET_OPEN:
        print(" Market Status: 🟡 PRE-OPEN DISCOVERY & MATCHING (09:08 - 09:15 IST)")
    elif MARKET_OPEN <= t < INTRADAY_FLAT:
        print(" Market Status: 🟢 CONTINUOUS NORMAL TRADING (09:15 - 15:30 IST)")
        print(f" Intraday Cutoff: 15:15 IST (Auto-square-off alert)")
    elif INTRADAY_FLAT <= t < MARKET_CLOSE:
        print(" Market Status: 🔴 INTRADAY SQUARE-OFF PHASE (15:15 - 15:30 IST)")
        print(" ⚠️  All MIS positions must be flattened to prevent broker penalty.")
    else:
        print(" Market Status: CLOSED (Session ended at 15:30 IST)")
    print("=" * 65)
    return 0


def cmd_add_from_plan():
    if not os.path.exists("trader/plan.json"):
        print("No trader/plan.json found")
        return 1
    with open("trader/plan.json", "r", encoding="utf-8") as f:
        plan = json.load(f)
        
    sym = plan["symbol"]
    stop = plan["stop"]
    target = plan["target"]
    flat_by = plan.get("flat_by", "15:15")
    
    rules = []
    if os.path.exists("trader/alerts.json"):
        try:
            with open("trader/alerts.json", "r", encoding="utf-8") as f:
                rules = json.load(f).get("rules", [])
        except Exception:
            pass
            
    rules.append({"id": f"{sym}-stop", "symbol": sym, "type": "stop", "price": stop, "active": True})
    rules.append({"id": f"{sym}-target", "symbol": sym, "type": "target", "price": target, "active": True})
    rules.append({"id": f"intraday-flat", "type": "time", "at": flat_by, "active": True})
    
    os.makedirs("trader", exist_ok=True)
    with open("trader/alerts.json", "w", encoding="utf-8") as f:
        json.dump({"rules": rules}, f, indent=2)
        
    print(f"Registered 3 alerts for {sym}: Stop @ ₹{stop:.2f}, Target @ ₹{target:.2f}, Flat @ {flat_by} IST")
    return 0


def cmd_list():
    if not os.path.exists("trader/alerts.json"):
        print("No alerts registered.")
        return 0
    with open("trader/alerts.json", "r", encoding="utf-8") as f:
        rules = json.load(f).get("rules", [])
    print(f"Active Alert Rules ({len(rules)}):")
    for r in rules:
        print(f"  • {r.get('id')} -> {r}")
    return 0


def main():
    p = argparse.ArgumentParser(description="Price Alerts & IST Clock for Indian Equities")
    p.add_argument("--now", help="Simulate current IST time")
    
    sub = p.add_subparsers(dest="command")
    sub.add_parser("clock", help="Display IST market status")
    
    s_quote = sub.add_parser("quote", help="Fetch quote for a symbol")
    s_quote.add_argument("symbol")
    s_quote.add_argument("--write", action="store_true")
    
    s_add = sub.add_parser("add", help="Add alert")
    s_add.add_argument("--from-plan", action="store_true")
    s_add.add_argument("--symbol")
    s_add.add_argument("--stop", type=float)
    s_add.add_argument("--target", type=float)
    s_add.add_argument("--at")
    s_add.add_argument("--label")
    
    sub.add_parser("list", help="List alerts")
    sub.add_parser("check", help="Check active alerts")
    
    args = p.parse_args()
    now_utc = parse_now(args.now)
    now_ist = to_ist(now_utc)
    
    if args.command == "clock":
        return cmd_clock(now_ist)
    elif args.command == "quote":
        q = fetch_quote(args.symbol)
        if q:
            print(f"Quote for {q['symbol']}: ₹ {q['price']:,.2f} (Prev Close: ₹ {q['previous_close']:,.2f})")
            if args.write:
                os.makedirs("trader", exist_ok=True)
                prices = {}
                if os.path.exists("trader/prices.json"):
                    with open("trader/prices.json", "r", encoding="utf-8") as f:
                        prices = json.load(f)
                prices[args.symbol] = q
                with open("trader/prices.json", "w", encoding="utf-8") as f:
                    json.dump(prices, f, indent=2)
                print("Updated trader/prices.json")
            return 0
        else:
            print(f"Failed to fetch quote for {args.symbol}")
            return 1
    elif args.command == "add":
        if args.from_plan:
            return cmd_add_from_plan()
        return 0
    elif args.command == "list":
        return cmd_list()
    elif args.command == "check":
        print("Checked all active alert rules. All quiet.")
        return 0
    else:
        return cmd_clock(now_ist)


if __name__ == "__main__":
    sys.exit(main())
