#!/usr/bin/env python3
"""Entry Timer for Indian Equities (trader-entry). Standard library only.

Watches a setup bar by bar (5m) in IST and signals the exact moment to enter. Long side only.
It never places an order.

    python3 entry.py check RELIANCE.NS                       # Opening-range breakout, 5-minute bars
    python3 entry.py check RELIANCE.NS --now "2026-10-19 09:45"
    python3 entry.py check RELIANCE.NS --setup level --level 2980.00
    python3 entry.py check RELIANCE.NS --write               # -> trader/entry.json
"""

import argparse
import datetime
import gzip
import json
import os
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; IndianDayTrader/2.0; +https://github.com/)"
YAHOO_HOSTS = ("https://query2.finance.yahoo.com", "https://query1.finance.yahoo.com")
MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)
BAR_MINUTES = 5


class EntryError(Exception):
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
        raise EntryError("--now wants a time like \"2026-10-19 10:15\" (IST) or ...Z (UTC)")
    if dt.tzinfo is None:
        return ist_to_utc(dt)
    return (dt - dt.utcoffset()).replace(tzinfo=None)


def to_yahoo_sym(sym):
    sym = sym.strip().upper()
    return sym if (sym.endswith(".NS") or sym.endswith(".BO")) else sym + ".NS"


def fetch_chart(sym):
    path = f"/v8/finance/chart/{to_yahoo_sym(sym)}?range=1d&interval=5m"
    for host in YAHOO_HOSTS:
        try:
            req = urllib.request.Request(host + path, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = resp.read()
                if resp.info().get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return json.loads(data.decode("utf-8"))
        except Exception:
            continue
    raise EntryError(f"Could not fetch intraday chart for {sym}")


def parse_bars(data):
    chart = data["chart"]["result"][0]
    ts = chart.get("timestamp", [])
    quote = chart["indicators"]["quote"][0]
    bars = []
    for i in range(len(ts)):
        if ts[i] and quote["close"][i] is not None:
            bars.append({
                "ts": ts[i],
                "open": quote["open"][i],
                "high": quote["high"][i],
                "low": quote["low"][i],
                "close": quote["close"][i],
                "volume": quote["volume"][i] or 0
            })
    return bars


def check_entry(sym, setup="orb", level=None, or_minutes=15, now_ist=None, offline_file=None):
    if offline_file:
        with open(offline_file, "r", encoding="utf-8") as f:
            data = json.load(f)
        bars = parse_bars(data)
    else:
        bars = parse_bars(fetch_chart(sym))
        
    session_bars = []
    for b in bars:
        bar_ist = datetime.datetime.fromtimestamp(b["ts"], datetime.timezone.utc) + ist_offset()
        bar_naive = bar_ist.replace(tzinfo=None)
        if bar_naive.date() == now_ist.date():
            if bar_naive + datetime.timedelta(minutes=BAR_MINUTES) <= now_ist:
                session_bars.append((bar_naive, b))
                
    if not session_bars:
        return {"status": "waiting", "reason": "No completed bars today yet"}
        
    if setup == "orb":
        or_end = datetime.time(9, 15 + or_minutes)
        or_bars = [b for (dt, b) in session_bars if dt.time() < or_end]
        post_bars = [b for (dt, b) in session_bars if dt.time() >= or_end]
        
        if not or_bars:
            return {"status": "waiting", "reason": "Opening range still forming"}
            
        or_high = max(b["high"] for b in or_bars)
        or_low = min(b["low"] for b in or_bars)
        
        for dt, b in post_bars:
            if b["close"] > or_high:
                return {
                    "symbol": sym,
                    "status": "triggered",
                    "setup": "orb",
                    "entry": round(b["close"], 2),
                    "or_high": round(or_high, 2),
                    "or_low": round(or_low, 2),
                    "triggered_at": dt.strftime("%H:%M IST"),
                    "date": now_ist.date().isoformat()
                }
        return {
            "symbol": sym,
            "status": "waiting",
            "setup": "orb",
            "or_high": round(or_high, 2),
            "or_low": round(or_low, 2),
            "reason": f"Waiting for 5m close above range high (₹{or_high:.2f})"
        }
    elif setup == "level":
        if not level:
            raise EntryError("--setup level requires --level PRICE")
        for dt, b in session_bars:
            if b["close"] > level:
                return {
                    "symbol": sym,
                    "status": "triggered",
                    "setup": "level",
                    "entry": round(b["close"], 2),
                    "level": level,
                    "triggered_at": dt.strftime("%H:%M IST"),
                    "date": now_ist.date().isoformat()
                }
        return {"symbol": sym, "status": "waiting", "reason": f"Price below level ₹{level:.2f}"}


def main():
    p = argparse.ArgumentParser(description="Entry Timer for Indian Equities")
    p.add_argument("--now", help="Simulate current IST time")
    p.add_argument("--offline", help="Path to offline chart JSON")
    p.add_argument("--setup", default="orb", choices=["orb", "level"])
    p.add_argument("--level", type=float, help="Breakout level price")
    p.add_argument("--or-minutes", type=int, default=15)
    p.add_argument("--write", action="store_true", help="Write to trader/entry.json on trigger")
    
    sub = p.add_subparsers(dest="command")
    s_check = sub.add_parser("check", help="Check entry status for a symbol")
    s_check.add_argument("symbol")
    
    args = p.parse_args()
    now_utc = parse_now(args.now)
    now_ist = to_ist(now_utc)
    
    if args.command == "check":
        res = check_entry(args.symbol, setup=args.setup, level=args.level,
                          or_minutes=args.or_minutes, now_ist=now_ist, offline_file=args.offline)
        print("=" * 60)
        print(f" ENTRY CHECK: {args.symbol} | Status: {res.get('status').upper()}")
        print("=" * 60)
        for k, v in res.items():
            print(f"  {k}: {v}")
            
        if args.write and res.get("status") == "triggered":
            os.makedirs("trader", exist_ok=True)
            with open("trader/entry.json", "w", encoding="utf-8") as f:
                json.dump(res, f, indent=2)
            print("\nSaved triggered state to trader/entry.json")
        return 0 if res.get("status") == "triggered" else 1
    else:
        p.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
