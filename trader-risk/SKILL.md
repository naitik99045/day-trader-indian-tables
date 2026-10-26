---
name: trader-risk
description: >-
  Pre-trade Risk Gatekeeper for Indian Equities. Validates proposed orders against max loss in INR,
  daily loss limits, SEBI 5x MIS margin requirements, circuit limit proximity (5%/10%/20%), and
  verifies net profitability after deducting statutory transaction charges (STT, Stamp Duty, GST, Brokerage).
argument-hint: "[--no-write] [--orders PATH]"
---

# trader-risk (NSE / BSE)

The risk gatekeeper ensures no reckless trades are executed. Every order receives `PASS` or `BLOCK`.

```bash
python trader-risk/check.py                                         # Validates trader/orders.json
python trader-risk/check.py --now "2026-10-19 10:15"
```

## Checks Performed
1. Max loss per trade & daily loss limit in INR.
2. SEBI Peak Margin compliance (MIS 5x leverage requirement).
3. Integer whole-share verification.
4. Circuit Limit Proximity Guard (blocks entries within 1.0% of upper/lower circuit).
5. Breakeven statutory cost audit (STT, Exchange fees, SEBI charges, Stamp duty, GST).
6. IST session windows (09:30 to 15:00 IST).
