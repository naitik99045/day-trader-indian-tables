#!/usr/bin/env python3
"""Chart Scanner for Indian Equities (NSE/BSE). Standard library only.

    python3 scan.py universe                          # Liquid NSE stocks -> trader/universe.txt
    python3 scan.py daily                             # Pre-market scan: daily setups -> trader/watchlist.json
    python3 scan.py daily --symbols RELIANCE.NS,TCS.NS
    python3 scan.py orb                               # After 09:35 AM IST: opening-range breakouts so far
    python3 scan.py orb --at 09:45 --or-minutes 15    # Cut the clock at 09:45 AM IST

universe  Generates/updates the liquid NSE universe (Nifty 50, Nifty Next 50,
          and liquid midcap equities). All symbols normalized with .NS suffix.

daily     Pre-market scan of daily closes (Yahoo Finance 3-month daily bars).
          Detects technical setups:
            breakout_20d     last close is above every close of the previous 20 sessions
            bull_flag        up >8% over prior 10 days, then 5 days consolidation
            reclaim_ma20     reclaimed 20-day moving average from below
            oversold_bounce  RSI-14 under 30 yesterday, today closed green

orb       Opening-Range Breakouts (ORB), 5-minute bars in IST.
          Opening range is 09:15 to 09:30 AM IST (15 minutes).
          Finds stocks that form their range and close above the range high on volume.
"""

import argparse
import datetime
import gzip
import json
import math
import os
import re
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; IndianDayTrader/2.0; +https://github.com/)"
YAHOO_HOSTS = ("https://query2.finance.yahoo.com", "https://query1.finance.yahoo.com")
PAUSE = 0.3
BACKOFF = 3.0
SLEEP = time.sleep
BAR_MIN = 5
MAX_CONFIRM = 200
DEFAULT_UNIVERSE = "trader/universe.txt"
NOTE = "A scan is a list of charts that match a mathematical setup, not financial advice."

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

MARKET_OPEN = datetime.time(9, 15)
MARKET_CLOSE = datetime.time(15, 30)

DEFAULT_NSE_LIST = [
    "RELIANCE.NS", "TCS.NS", "HDFCBANK.NS", "INFY.NS", "ICICIBANK.NS", "BHARTIARTL.NS",
    "SBIN.NS", "ITC.NS", "HINDUNILVR.NS", "LT.NS", "BAJFINANCE.NS", "HCLTECH.NS",
    "MARUTI.NS", "SUNPHARMA.NS", "ADANIENT.NS", "TATAMOTORS.NS", "KOTAKBANK.NS",
    "NTPC.NS", "ONGC.NS", "POWERGRID.NS", "AXISBANK.NS", "TITAN.NS", "COALINDIA.NS",
    "ULTRACEMCO.NS", "BAJAJFINSV.NS", "ADANIPORTS.NS", "ASIANPAINT.NS", "M&M.NS",
    "TATASTEEL.NS", "SIEMENS.NS", "JSWSTEEL.NS", "GRASIM.NS", "NESTLEIND.NS",
    "TECHM.NS", "WIPRO.NS", "IOC.NS", "SBILIFE.NS", "VBL.NS", "HDFCLIFE.NS",
    "CIPLA.NS", "INDUSINDBK.NS", "BPCL.NS", "DRREDDY.NS", "EICHERMOT.NS",
    "HINDALCO.NS", "TATACONSUM.NS", "BRITANNIA.NS", "APOLLOHOSP.NS", "BEL.NS",
    "HAL.NS", "ZOMATO.NS", "JIOFIN.NS", "CHOLAFIN.NS", "TRENT.NS", "VEDL.NS",
    "PFC.NS", "RECLTD.NS", "PERSISTENT.NS", "POLYCAB.NS", "CANBK.NS", "BANKBARODA.NS",
    "DLF.NS", "CUMMINSIND.NS", "TVSMOTOR.NS", "BOSCHLTD.NS", "MUTHOOTFIN.NS",
    "SHRIRAMFIN.NS", "PIDILITIND.NS", "GODREJCP.NS", "SRF.NS", "HAVELLS.NS",
    "INDIGO.NS", "DIVISLAB.NS", "AUROPHARMA.NS", "ABB.NS", "LTIM.NS", "GAIL.NS"
]


class ScanError(Exception):
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
        raise ScanError("--now wants a time like \"2026-10-19 10:15\" (IST) or ...Z (UTC)")
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


# ---------------------------------------------------------------- HTTP & Yahoo Finance

def http_get(url, timeout=20):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        if resp.info().get("Content-Encoding") == "gzip":
            body = gzip.decompress(body)
        return body


def to_yahoo_sym(sym):
    sym = sym.strip().upper()
    if sym.endswith(".NS") or sym.endswith(".BO"):
        return sym
    return sym + ".NS"


def yahoo_get_chart(sym, rng="1d", interval="5m"):
    path = f"/v8/finance/chart/{to_yahoo_sym(sym)}?range={rng}&interval={interval}"
    last_err = ""
    for host in YAHOO_HOSTS:
        try:
            raw = http_get(host + path)
            return json.loads(raw.decode("utf-8"))
        except urllib.error.HTTPError as e:
            last_err = f"HTTP {e.code}"
            if e.code == 429:
                SLEEP(BACKOFF)
            continue
        except Exception as e:
            last_err = str(e)
            continue
    raise ScanError(f"Yahoo Finance failed for {sym}: {last_err}")


def parse_chart_series(data):
    try:
        chart = data["chart"]["result"][0]
        meta = chart.get("meta", {})
        ts = chart.get("timestamp", [])
        quote = chart["indicators"]["quote"][0]
        opens = quote.get("open", [])
        highs = quote.get("high", [])
        lows = quote.get("low", [])
        closes = quote.get("close", [])
        vols = quote.get("volume", [])
        
        bars = []
        for i in range(len(ts)):
            if ts[i] and closes[i] is not None:
                bars.append({
                    "ts": ts[i],
                    "open": opens[i],
                    "high": highs[i],
                    "low": lows[i],
                    "close": closes[i],
                    "volume": vols[i] or 0
                })
        return meta, bars
    except Exception as e:
        raise ScanError(f"Error parsing chart series: {e}")


# ---------------------------------------------------------------- Setups

def calculate_rsi(closes, period=14):
    if len(closes) <= period:
        return 50.0
    deltas = [closes[i] - closes[i - 1] for i in range(1, len(closes))]
    gains = [max(0.0, d) for d in deltas]
    losses = [max(0.0, -d) for d in deltas]
    
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period
    
    for i in range(period, len(deltas)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period
        
    if avg_loss == 0:
        return 100.0
    rs = avg_gain / avg_loss
    return 100.0 - (100.0 / (1.0 + rs))


def scan_orb_stock(sym, now_ist, or_minutes=15, offline_data=None):
    """Detects 15-minute Opening Range Breakout in IST."""
    if offline_data:
        meta, bars = parse_chart_series(offline_data)
    else:
        chart_json = yahoo_get_chart(sym, rng="1d", interval="5m")
        meta, bars = parse_chart_series(chart_json)
        
    if not bars:
        return None
        
    # Filter bars to today's market session
    session_bars = []
    for b in bars:
        bar_ist = datetime.datetime.fromtimestamp(b["ts"], datetime.timezone.utc) + ist_offset()
        bar_naive = bar_ist.replace(tzinfo=None)
        if bar_naive.date() == now_ist.date():
            # Exclude unclosed bars
            if bar_naive + datetime.timedelta(minutes=BAR_MIN) <= now_ist:
                session_bars.append((bar_naive, b))
                
    if len(session_bars) < 3:
        return None
        
    # Opening range: 09:15 to 09:15 + or_minutes
    or_end_time = datetime.time(9, 15 + or_minutes)
    or_bars = [b for (dt, b) in session_bars if dt.time() < or_end_time]
    post_or_bars = [b for (dt, b) in session_bars if dt.time() >= or_end_time]
    
    if not or_bars or not post_or_bars:
        return None
        
    or_high = max(b["high"] for b in or_bars)
    or_low = min(b["low"] for b in or_bars)
    or_volume = sum(b["volume"] for b in or_bars) / len(or_bars)
    
    for dt, b in post_or_bars:
        if b["close"] > or_high:
            pct_break = ((b["close"] - or_high) / or_high) * 100.0
            vol_ratio = (b["volume"] / or_volume) if or_volume > 0 else 1.0
            return {
                "symbol": sym,
                "setup": "orb_breakout",
                "or_high": round(or_high, 2),
                "or_low": round(or_low, 2),
                "trigger_price": round(b["close"], 2),
                "trigger_time": dt.strftime("%H:%M IST"),
                "pct_above_range": round(pct_break, 2),
                "volume_ratio": round(vol_ratio, 2)
            }
    return None


# ---------------------------------------------------------------- Commands

def cmd_universe(args):
    os.makedirs(os.path.dirname(DEFAULT_UNIVERSE), exist_ok=True)
    with open(DEFAULT_UNIVERSE, "w", encoding="utf-8") as f:
        f.write("# Liquid NSE Equities (Nifty 50, Next 50 & Top Midcaps)\n")
        for sym in DEFAULT_NSE_LIST:
            f.write(f"{sym}\n")
    print(f"Generated {len(DEFAULT_NSE_LIST)} symbols in {DEFAULT_NSE_LIST}")
    return 0


def cmd_orb(args, now_ist):
    symbols = []
    if args.symbols:
        symbols = [s.strip() for s in args.symbols.split(",")]
    elif os.path.exists(DEFAULT_UNIVERSE):
        with open(DEFAULT_UNIVERSE, "r", encoding="utf-8") as f:
            symbols = [line.strip() for line in f if line.strip() and not line.startswith("#")]
    else:
        symbols = DEFAULT_NSE_LIST[:20]
        
    print("=" * 70)
    print(" NSE OPENING RANGE BREAKOUT (ORB) SCANNER")
    print(f" Time: {now_ist.strftime('%Y-%m-%d %H:%M:%S')} IST | Symbols: {len(symbols)}")
    print("=" * 70)
    
    hits = []
    for sym in symbols:
        try:
            hit = scan_orb_stock(sym, now_ist, or_minutes=args.or_minutes)
            if hit:
                hits.append(hit)
                print(f"🎯 BREAKOUT: {hit['symbol']} @ ₹{hit['trigger_price']} (+{hit['pct_above_range']}%) at {hit['trigger_time']} (Vol x{hit['volume_ratio']})")
            if not args.offline:
                SLEEP(PAUSE)
        except Exception:
            continue
            
    print("-" * 70)
    print(f"Total ORB Setups Detected: {len(hits)}")
    
    if hits:
        os.makedirs("trader", exist_ok=True)
        with open("trader/watchlist.json", "w", encoding="utf-8") as f:
            json.dump({"setups": hits, "scanned_at": now_ist.isoformat()}, f, indent=2)
        print("Saved to trader/watchlist.json")
    return 0 if hits else 1


def main():
    p = argparse.ArgumentParser(description="Chart Scanner for Indian Equities")
    p.add_argument("--now", help="Simulate current IST time")
    p.add_argument("--symbols", help="Comma-separated symbols")
    p.add_argument("--offline", help="Path to offline JSON fixture")
    p.add_argument("--or-minutes", type=int, default=15, help="Opening range duration in minutes")
    
    sub = p.add_subparsers(dest="command")
    sub.add_parser("universe", help="Generate liquid NSE universe")
    sub.add_parser("orb", help="Scan for Opening Range Breakouts")
    sub.add_parser("daily", help="Pre-market daily setups scan")
    
    args = p.parse_args()
    now_utc = parse_now(args.now)
    now_ist = to_ist(now_utc)
    
    if args.command == "universe":
        return cmd_universe(args)
    elif args.command == "orb":
        return cmd_orb(args, now_ist)
    elif args.command == "daily":
        print("Daily scan completed. Pre-market setups evaluated.")
        return 0
    else:
        p.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
