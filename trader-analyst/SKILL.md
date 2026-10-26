---
name: trader-analyst
description: >-
  Fundamentals & Earnings Analyst for Indian Equities. Summarizes quarterly corporate financial performance,
  EBITDA margins, revenue growth, P/E multiples, and analyst consensus targets for NSE-listed companies.
argument-hint: "SYMBOL [SYMBOL ...] [--metrics PATH]"
---

# trader-analyst (NSE / BSE)

Analyzes balance sheet health and quarterly earnings for Indian equities.

```bash
python trader-analyst/facts.py RELIANCE.NS
python trader-analyst/facts.py TCS.NS INFY.NS --metrics trader/metrics.json
```
