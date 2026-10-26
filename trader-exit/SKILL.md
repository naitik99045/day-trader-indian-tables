---
name: trader-exit
description: >-
  Exit Planner for Indian Equities. Sets the stop-loss (ORB midpoint, ATR, swing low) and target (1R, 1.5R, 2R)
  BEFORE entering. Enforces the mandatory 15:15 IST intraday auto-square-off cutoff. Writes trader/plan.json.
argument-hint: "plan [--stop or-mid|pct:X|price:X] [--target 1R|2R] [--write]"
---

# trader-exit (NSE / BSE)

Pre-calculates exact exit rules in Indian Rupees before risking capital.

```bash
python trader-exit/exit.py plan                                     # Reads trader/entry.json: or-mid stop, 2R target
python trader-exit/exit.py plan --stop or-mid --target 1.5R --write # Writes trader/plan.json
python trader-exit/exit.py show                                     # Display current active plan
```

## Mandatory Indian Market Square-Off
- `flat_by: 15:15 IST`: Indian brokers automatically square off intraday MIS positions between 15:15 and 15:25 IST, levying penalty charges. This tool mandates flattening by 15:15 IST.
