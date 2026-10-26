---
name: trader-entry
description: >-
  Entry Timer for Indian Equities. Watches 5-minute candle closes in IST bar-by-bar and triggers
  the exact moment a stock breaks out above its opening range or technical level. Writes trader/entry.json.
argument-hint: "check SYMBOL [--setup orb|level] [--write]"
---

# trader-entry (NSE / BSE)

Watches setup bars and signals valid breakout confirmations.

```bash
python trader-entry/entry.py check RELIANCE.NS                      # Check 15m ORB trigger
python trader-entry/entry.py check RELIANCE.NS --write              # Writes trader/entry.json on trigger
python trader-entry/entry.py check TCS.NS --setup level --level 4150.00
```

## Logic
- A breakout is confirmed only when a completed 5-minute candle CLOSES above the opening range high.
- Wicks or intra-candle spikes do not trigger entries.
