---
name: trader-alerts
description: >-
  Price Alerts & IST Trading Clock. Monitors NSE trading phases (Pre-open, Live, 15:15 Intraday Square-off, Closed),
  tracks NSE holiday calendars, and rings terminal alerts on stop, target, or price threshold hits.
argument-hint: "clock | quote SYMBOL [--write] | add --from-plan | check | list"
---

# trader-alerts (NSE / BSE)

Monitors price thresholds and market clock transitions in IST.

```bash
python trader-alerts/alerts.py clock                                # View current NSE trading session status
python trader-alerts/alerts.py quote RELIANCE.NS --write            # Updates trader/prices.json
python trader-alerts/alerts.py add --from-plan                      # Registers stop, target & 15:15 flat alert
python trader-alerts/alerts.py check                                # Checks rules and sounds bell
python trader-alerts/alerts.py list                                 # View active alerts
```
