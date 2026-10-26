---
name: trader-news
description: >-
  News Monitor for Indian Equities. Tracks breaking corporate news, SEBI regulatory notices,
  earnings declarations, and catalysts across Indian business media and exchange feeds.
argument-hint: "--tickers RELIANCE.NS,TCS.NS [--hours 24]"
---

# trader-news (NSE / BSE)

Tracks news catalysts for Indian stocks before entering day trades.

```bash
python trader-news/news.py --tickers RELIANCE.NS,TCS.NS
python trader-news/news.py --tickers INFY.NS --hours 12
```

## Tagged Categories
- `[earnings]`: Quarterly financial results (Q1–Q4), PAT, revenue
- `[deal]`: M&A, strategic investments, major contracts
- `[regulatory]`: SEBI circulars, compliance notices, audit reports
- `[capital]`: Dividends, bonus shares, stock splits, buybacks
- `[management]`: Executive and Board appointments/resignations
