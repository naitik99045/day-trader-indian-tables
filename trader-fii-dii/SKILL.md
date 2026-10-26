---
name: trader-fii-dii
description: >-
  Smart Money & Institutional Flow Tracker for Indian Equities. Replaces US Congressional PTR tracking
  with daily FII/DII net institutional cash flows, prominent NSE Bulk & Block deals, and SEBI insider filings.
argument-hint: "flows | bulk"
---

# trader-fii-dii (NSE Smart Money Tracker)

Monitors Foreign and Domestic institutional capital movements.

```bash
python trader-fii-dii/tracker.py flows                              # Daily FII & DII net flows in INR Crore
python trader-fii-dii/tracker.py bulk                               # Large NSE bulk and block transactions
```

## Significance in Indian Day Trading
- Heavy FII Net Buying (> +₹1,500 Cr): Provides strong market breadth and bullish continuation on Opening Range Breakouts.
- Heavy FII Net Selling: Often causes intraday breakouts to fail or reverse rapidly.
