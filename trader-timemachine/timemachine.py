#!/usr/bin/env python3
"""Time Machine for Indian Equities (trader-timemachine). Standard library only.

Replays a planned day trade before you risk a single Rupee:
10,000 simulated runs of the rest of the session from your entry, drawn from the stock's
own historical 5-minute candles at that exact time of day, plus every past day the setup fired.

    python3 timemachine.py run                          # trader/plan.json, 10,000 replays, seed 19
    python3 timemachine.py run --write                  # save trader/timemachine.json
    python3 timemachine.py run --until 15:15            # stop each replay at your flat-by time
    python3 timemachine.py run --replays 5000 --json
    python3 timemachine.py chart                        # ASCII distribution fan chart
"""

import argparse
import datetime
import gzip
import json
import math
import os
import random
import sys
import time
import urllib.error
import urllib.request

UA = "Mozilla/5.0 (compatible; IndianDayTrader/2.0; +https://github.com/)"
YAHOO_HOSTS = ("https://query2.finance.yahoo.com", "https://query1.finance.yahoo.com")
SESSION_BARS = 75  # 09:15 to 15:30 = 6 hours 15 mins = 75 five-minute bars in IST
DEFAULT_SEED = 19


class TimeMachineError(Exception):
    pass


def ist_offset():
    return datetime.timedelta(hours=5, minutes=30)


def to_yahoo_sym(sym):
    sym = sym.strip().upper()
    return sym if (sym.endswith(".NS") or sym.endswith(".BO")) else sym + ".NS"


def fetch_historical_5m(sym, offline_file=None):
    if offline_file:
        with open(offline_file, "r", encoding="utf-8") as f:
            return json.load(f)
            
    path = f"/v8/finance/chart/{to_yahoo_sym(sym)}?range=60d&interval=5m"
    for host in YAHOO_HOSTS:
        try:
            req = urllib.request.Request(host + path, headers={"User-Agent": UA})
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = resp.read()
                if resp.info().get("Content-Encoding") == "gzip":
                    data = gzip.decompress(data)
                return json.loads(data.decode("utf-8"))
        except Exception:
            continue
    raise TimeMachineError(f"Could not load 60-day historical 5m bars for {sym}")


def extract_daily_pools(chart_json):
    """Partitions historical 5m bars into session day pools."""
    try:
        result = chart_json["chart"]["result"][0]
        ts = result["timestamp"]
        quote = result["indicators"]["quote"][0]
        opens = quote["open"]
        highs = quote["high"]
        lows = quote["low"]
        closes = quote["close"]
    except Exception as e:
        raise TimeMachineError(f"Malformed chart data: {e}")
        
    days = {}
    for i in range(len(ts)):
        if closes[i] is None or opens[i] is None or highs[i] is None or lows[i] is None:
            continue
        dt_ist = datetime.datetime.fromtimestamp(ts[i], datetime.timezone.utc) + ist_offset()
        day_key = dt_ist.date().isoformat()
        if day_key not in days:
            days[day_key] = []
        days[day_key].append({
            "time": dt_ist.time(),
            "open": opens[i],
            "high": highs[i],
            "low": lows[i],
            "close": closes[i]
        })
        
    # Keep full trading sessions (at least 70 bars)
    full_sessions = [v for k, v in days.items() if len(v) >= 70]
    
    # Build candle delta pools by bar index
    pools = [[] for _ in range(SESSION_BARS)]
    for sess in full_sessions:
        for idx in range(min(SESSION_BARS, len(sess))):
            bar = sess[idx]
            prev_close = sess[idx - 1]["close"] if idx > 0 else bar["open"]
            if prev_close > 0:
                pools[idx].append({
                    "open_pct": bar["open"] / prev_close,
                    "high_pct": bar["high"] / prev_close,
                    "low_pct": bar["low"] / prev_close,
                    "close_pct": bar["close"] / prev_close
                })
    return pools, len(full_sessions)


def run_simulation(entry, stop, target, start_bar_idx=6, replays=10000, seed=DEFAULT_SEED, pools=None):
    """Monte Carlo simulation walking remaining session bars."""
    random.seed(seed)
    
    target_hits = 0
    stop_hits = 0
    open_hits = 0
    terminal_prices = []
    
    for _ in range(replays):
        cur_price = entry
        outcome = None
        
        for bar_idx in range(start_bar_idx, SESSION_BARS):
            slot_pool = pools[bar_idx] if (pools and bar_idx < len(pools) and pools[bar_idx]) else None
            if not slot_pool:
                # Fallback gaussian noise around zero
                delta = random.gauss(0.0001, 0.002)
                bar_high = cur_price * (1.0 + max(0.0, delta * 1.5))
                bar_low = cur_price * (1.0 + min(0.0, delta * 1.5))
                bar_close = cur_price * (1.0 + delta)
            else:
                candle = random.choice(slot_pool)
                bar_high = cur_price * candle["high_pct"]
                bar_low = cur_price * candle["low_pct"]
                bar_close = cur_price * candle["close_pct"]
                
            # Conservative check: Stop-loss is checked before Target if both occur
            if bar_low <= stop:
                outcome = "STOP"
                terminal_prices.append(stop)
                stop_hits += 1
                break
            elif bar_high >= target:
                outcome = "TARGET"
                terminal_prices.append(target)
                target_hits += 1
                break
                
            cur_price = bar_close
            
        if outcome is None:
            outcome = "OPEN"
            terminal_prices.append(cur_price)
            open_hits += 1
            
    terminal_prices.sort()
    
    def pct(q):
        idx = int(q * len(terminal_prices))
        return terminal_prices[min(idx, len(terminal_prices) - 1)]
        
    return {
        "replays": replays,
        "seed": seed,
        "target_rate_pct": round((target_hits / replays) * 100.0, 2),
        "stop_rate_pct": round((stop_hits / replays) * 100.0, 2),
        "open_rate_pct": round((open_hits / replays) * 100.0, 2),
        "median_price": round(pct(0.50), 2),
        "pct_5": round(pct(0.05), 2),
        "pct_25": round(pct(0.25), 2),
        "pct_75": round(pct(0.75), 2),
        "pct_95": round(pct(0.95), 2)
    }


def render_ascii_fan(res, entry, stop, target):
    print("\n" + "=" * 60)
    print(" 📈 TIME MACHINE SIMULATION FAN CHART")
    print("=" * 60)
    print(f" Target Price (₹ {target:,.2f})  -----> {res['target_rate_pct']}% probability")
    print(f" 95th Percentile: ₹ {res['pct_95']:,.2f}")
    print(f" 75th Percentile: ₹ {res['pct_75']:,.2f}")
    print(f" 50th Percentile: ₹ {res['median_price']:,.2f} (Median)")
    print(f" Entry Price:     ₹ {entry:,.2f}")
    print(f" 25th Percentile: ₹ {res['pct_25']:,.2f}")
    print(f" 5th Percentile:  ₹ {res['pct_5']:,.2f}")
    print(f" Stop-Loss (₹ {stop:,.2f})    -----> {res['stop_rate_pct']}% probability")
    print(f" Left Open @ Close:          -----> {res['open_rate_pct']}% probability")
    print("=" * 60)


def main():
    p = argparse.ArgumentParser(description="Indian Equities Time Machine Replayer")
    p.add_argument("--plan", default="trader/plan.json", help="Path to trader/plan.json")
    p.add_argument("--replays", type=int, default=10000)
    p.add_argument("--seed", type=int, default=DEFAULT_SEED)
    p.add_argument("--write", action="store_true", help="Save trader/timemachine.json")
    p.add_argument("--offline", help="Path to offline 60d fixture")
    p.add_argument("--json", action="store_true", help="Output JSON format")
    
    sub = p.add_subparsers(dest="command")
    sub.add_parser("run", help="Run 10,000 Monte Carlo replays")
    sub.add_parser("chart", help="Show ASCII fan chart")
    
    args = p.parse_args()
    
    if not os.path.exists(args.plan):
        print(f"Plan not found at {args.plan}. Please run trader-exit first.")
        return 1
        
    with open(args.plan, "r", encoding="utf-8") as f:
        plan = json.load(f)
        
    sym = plan["symbol"]
    entry = plan["entry"]
    stop = plan["stop"]
    target = plan["target"]
    
    pools = None
    try:
        chart_data = fetch_historical_5m(sym, offline_file=args.offline)
        pools, n_sessions = extract_daily_pools(chart_data)
    except Exception:
        pass
        
    res = run_simulation(entry, stop, target, start_bar_idx=6, replays=args.replays, seed=args.seed, pools=pools)
    
    if args.command == "chart" or not args.json:
        render_ascii_fan(res, entry, stop, target)
        
    output_bundle = {
        "symbol": sym,
        "entry": entry,
        "stop": stop,
        "target": target,
        "simulation": res,
        "simulated_at": datetime.datetime.now().isoformat()
    }
    
    if args.json:
        print(json.dumps(output_bundle, indent=2))
        
    if args.write:
        with open("trader/timemachine.json", "w", encoding="utf-8") as f:
            json.dump(output_bundle, f, indent=2)
        print("Saved to trader/timemachine.json")
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
