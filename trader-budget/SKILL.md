---
name: trader-budget
description: >-
  Position Sizing and Budget Manager for Indian Equities. Sizes trades to your INR account budget
  and max loss per trade. Enforces whole integer share constraints (no fractional shares) and SEBI 5x MIS leverage.
  Writes trader/orders.json.
argument-hint: "[--write] [--limit PRICE]"
---

# trader-budget (NSE / BSE)

Sizes positions with precision mathematical constraints.

```bash
python trader-budget/size.py                                        # Sizes trader/plan.json
python trader-budget/size.py --write                                # Writes trader/orders.json
python trader-budget/size.py --limit 2950.00 --write                # Sized at specified limit price
```

## Sizing Formula
Whole shares only:
$$\text{Shares} = \min \left( \lfloor \frac{\text{Max Loss}}{\text{Risk / Share}} \rfloor, \lfloor \frac{\text{Budget} \times \text{Position Cap}}{\text{Entry}} \rfloor, \lfloor \frac{\text{Buying Power}}{\text{Entry}} \rfloor \right)$$
Fractional shares are strictly rejected.
