# Indian Stock Market Day Trading Skill Suite (`NSE / BSE`)
### With Live Trading Tables for Claude Desktop, Claude Code & Antigravity

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Market: NSE / BSE](https://img.shields.io/badge/Market-NSE%20%2F%20BSE-blue.svg)](https://www.nseindia.com)
[![Timezone: IST (UTC+5:30)](https://img.shields.io/badge/Timezone-IST%20(UTC%2B5:30)-orange.svg)]()
[![Python: 3.8+](https://img.shields.io/badge/Python-3.8+-green.svg)]()

11 AI skills for Indian stock market day trading: scan liquid NSE charts, track market-moving news, time entries bar by bar in IST, plan stops with 15:15 IST auto-square-off enforcement, simulate 10,000 session paths before risking ₹1, calculate SEBI statutory friction (STT, GST, Stamp Duty, Brokerage), view live trading tables, and execute orders with 2-step human confirmation.

Free, MIT, zero mandatory pip dependencies (standard library Python only).

---

## ⚡ Quick Installation

### 1. In Claude Desktop (MCP Integration)
Claude Desktop connects to this suite using the Model Context Protocol (MCP):

1. Open your Claude Desktop configuration file on Windows:
   * Press `Win + R`, paste:
     ```
     %APPDATA%\Claude\claude_desktop_config.json
     ```
   * *(Path: `C:\Users\<username>\AppData\Roaming\Claude\claude_desktop_config.json`)*
2. Add the `day-trader-indian-tables` MCP server:
   ```json
   {
     "mcpServers": {
       "day-trader-indian-tables": {
         "command": "python",
         "args": [
           "C:/path/to/day-trader-indian-tables/mcp_server.py"
         ]
       }
     }
   }
   ```
   *(Note: Replace `C:/path/to/day-trader-indian-tables` with your actual cloned folder path, using forward slashes `/`).*
3. Restart **Claude Desktop**. You will see the hammer (tools) icon with all Indian market trading tools ready!

---

### 2. In Claude Code
Install as a plugin directly inside Claude Code:
```bash
/plugin marketplace add naitik99045/day-trader-indian-tables
/plugin install day-trader-indian-tables@day-trader-indian-tables
```

Or copy the skill folders directly to your global Claude skills directory:
```bash
git clone https://github.com/naitik99045/day-trader-indian-tables.git
cp -r day-trader-indian-tables/trader-* ~/.claude/skills/
```

Project-local (inside your project):
```bash
cp -r day-trader-indian-tables/trader-* .claude/skills/
```

---

### 3. In Google DeepMind Antigravity (`agy`)
Copy the skills into your Antigravity skills directory:
```bash
cp -r day-trader-indian-tables/trader-* ~/.gemini/antigravity-cli/skills/
```
Or place inside your workspace's `.agent/skills/`.

---

## 📊 Live Indian Trading Tables Dashboard

Launch the real-time visual trading tables dashboard in your terminal:
```bash
python trading_tables.py
```

### Features:
* **NSE Live Watchlist Table:** Displays live LTP, 15m Opening Range High & Low, Breakout %, Volume multiplier, and Breakout signals.
* **Positions & PnL Table:** Displays active MIS/CNC positions, average entry price, blocked margin, realized PnL, and total statutory taxes paid.
* **Excel & Google Sheets Live Sync:** Export real-time tables to CSV:
  ```bash
  python trading_tables.py export --csv trader/trading_tables.csv
  ```
  Link `trader/trading_tables.csv` into Excel (`Data > From Text/CSV`) with 1-minute auto-refresh.

---

## 🛠️ The 11 Skills

| Command / Skill | Job | Description |
| :--- | :--- | :--- |
| **`/trader-scanner`** | Chart Scanner | Scans liquid NSE equities for 15-minute Opening Range Breakouts (ORBs) between `09:15` and `09:30` AM IST, plus pre-market daily setups. |
| **`/trader-news`** | News Monitor | Tracks corporate announcements, quarterly results, SEBI regulatory notices, and market-moving headlines. |
| **`/trader-entry`** | Entry Timer | Monitors 5-minute candles in IST and signals the exact moment a stock closes above its range high. |
| **`/trader-exit`** | Exit Planner | Sets stop-loss (ORB midpoint, ATR) and profit targets (1R, 2R), and enforces the mandatory `15:15 IST` intraday auto-square-off cutoff. |
| **`/trader-timemachine`**| Time Machine | Replays 10,000 Monte Carlo paths of the session from the stock's own historical 5m bars, calculating objective win/loss odds in INR. |
| **`/trader-budget`** | Budget Manager | Sizes positions to your INR account budget and max risk. Enforces whole integer shares (no fractional shares) and 5x MIS leverage. |
| **`/trader-risk`** | Risk Manager | Pre-trade gatekeeper. Validates max loss, 1% circuit limit proximity guard, and calculates net profitability after statutory costs (STT, Stamp Duty, GST, Brokerage). |
| **`/trader-broker`** | Order Executor | Displays plain-English tickets with 2-step confirmation. Routes orders to the built-in Indian Paper Broker, or formats DhanHQ / Zerodha Kite payloads. |
| **`/trader-alerts`** | Alerts & Clock | Tracks IST market session phases (Pre-open, Live, 15:15 Square-off, Closed) and sounds alerts on stop, target, or time thresholds. |
| **`/trader-analyst`** | Fundamentals Analyst | Analyzes quarterly financial metrics, EBITDA margins, diluted EPS, and analyst consensus targets for NSE stocks. |
| **`/trader-fii-dii`** | Smart Money Tracker | Tracks daily FII/DII institutional net cash flows (₹ Cr) and prominent NSE Bulk & Block deals (>₹100 Cr). |

---

## 📈 The 8-Stage Pipeline: RELIANCE.NS Walkthrough

Every trade flows sequentially through a decoupled local state machine in `trader/`:

```
scanner -> news -> entry -> exit -> timemachine -> budget -> risk -> broker
alerts: stop, target, flat by 15:15 IST                                (while active)
fii-dii / analyst / news                                               (market context)
```

1. **`trader-scanner` at 09:35 AM IST**:
   `RELIANCE.NS` forms its 15-minute opening range between 09:15 and 09:30 AM IST: High ₹2,940.00, Low ₹2,910.00. The 09:30 candle closes at ₹2,944.00, confirming an Opening Range Breakout.
2. **`trader-news`**:
   Checks breaking news and filings for `RELIANCE.NS` over the past 24 hours.
3. **`trader-entry`**:
   Monitors completed 5m bars, confirms breakout, and writes `trader/entry.json`.
4. **`trader-exit`**:
   Calculates exit parameters:
   - Entry: ₹2,950.00
   - Stop-Loss: ₹2,925.00 (ORB midpoint, ₹25 risk/share)
   - Target: 2R at ₹3,000.00 (₹50 reward/share)
   - Mandatory Exit: `flat_by: 15:15 IST`
5. **`trader-timemachine`**:
   Replays 10,000 simulated paths: Target first 54.2%, Stop first 26.8%, Open at close 19.0%.
6. **`trader-budget`**:
   With a ₹1,00,000 account and ₹1,000 max risk:
   - Shares = $\lfloor 1000 / 25 \rfloor = 40$ shares (capped at 16 shares by 50% position limit).
   - Order value: $16 \times 2950 = \text{₹}47,200.00$.
   - Margin required under SEBI 5x MIS leverage: ₹9,440.00.
7. **`trader-risk`**:
   Verifies position is clear of the 10% Upper Circuit, calculates round-trip statutory costs (₹28.40), confirms Net R:R is 1.94R, and issues **`PASS`**.
8. **`trader-broker`**:
   Presents the plain-English confirmation ticket. You type **"yes"**. The order is executed against the **Indian Paper Broker**, recording fills and ledger updates in `trader/portfolio.json`.
9. **`trader-alerts`**:
   Monitors the active position and chimes if ₹3,000.00 or ₹2,925.00 is touched, or automatically at 15:15 IST.

---

## 🇮🇳 Indian Broker Integrations

* **Built-in Indian Paper Broker (Default):** Zero setup required. Runs completely offline or online with realistic execution slippage and SEBI statutory cost accounting in INR.
* **DhanHQ API & Webhook:** 100% free trading API for Dhan retail accounts. Compatible with Dhan Web and TradingView.
* **Zerodha Kite Connect:** Standardized payload format for Kite API bracket and MIS orders.

---

## 🏛️ SEBI Intraday Statutory Cost Structure

Every trade evaluation incorporates the official SEBI and Exchange statutory fee schedule:
- **Brokerage:** Flat ₹20 or 0.03% (whichever is lower) per executed order.
- **STT (Securities Transaction Tax):** 0.025% on sell side for equity intraday (MIS).
- **Exchange Turnover Charge:** 0.00297% (NSE Equity).
- **SEBI Turnover Fee:** ₹10 per crore (0.0001%).
- **Stamp Duty:** 0.003% on buy turnover.
- **GST:** 18% on (Brokerage + Exchange Charges + SEBI Turnover Fee).

---

## 🧪 Testing

Run the full offline test suite:
```bash
python -m unittest discover -s tests -v
```

---

## ⚠️ Disclaimer

**Not financial advice.** Day trading equities involves substantial risk of loss. Most retail traders lose money. This open-source software is for educational, analytical, and research purposes. Paper trading is strictly enabled by default. Never risk money you cannot afford to lose.
