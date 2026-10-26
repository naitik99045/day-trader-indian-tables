---
name: trader-scanner
description: >-
  Chart Scanner for Indian Equities (NSE/BSE). Scans liquid stocks for 15-minute Opening Range Breakouts (ORB)
  in IST (09:15-09:30 AM), pre-market daily setups (20-day high breakouts, bull flags, 20 EMA reclaim, oversold bounces),
  and volume surges using live Yahoo Finance intraday data. Writes trader/watchlist.json.
argument-hint: "[universe | daily | orb] [--symbols RELIANCE.NS,TCS.NS]"
---

# trader-scanner (NSE / BSE)

The Chart Scanner scans liquid Indian equities for high-probability intraday setups.
It evaluates Opening Range Breakouts (09:15 to 09:30 AM IST) and writes candidate stocks to `trader/watchlist.json`.

```bash
python trader-scanner/scan.py universe                       # Liquid NSE universe -> trader/universe.txt
python trader-scanner/scan.py daily                          # Pre-market scan -> trader/watchlist.json
python trader-scanner/scan.py orb                            # Scan 15m ORBs after 09:30 AM IST
python trader-scanner/scan.py orb --symbols RELIANCE.NS,TCS.NS,INFY.NS
```

## Session Constraints
- Market Open: 09:15 AM IST
- Opening Range Period: 09:15 – 09:30 AM IST (15 minutes)
- Universe: Nifty 50, Nifty Next 50, and liquid midcap equities
