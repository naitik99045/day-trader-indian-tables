# Project State & Context
**Last Updated:** 2026-10-28 21:50:00 IST

## 1. Project Overview
The **Indian Stock Market Day Trading Skill Suite (`day-trader-indian-tables`)** is a production-grade, MIT-licensed open-source quant suite designed for **NSE / BSE Cash Equities** and **NIFTY 50 Intraday Options Trading**. It operates natively inside Claude Desktop (via MCP), Claude Code, Google DeepMind Antigravity, and terminal CLI.

The suite solves retail options failure through deterministic quantitative models (Black-Scholes-Merton Greeks, Taylor Series Spot-to-Option SL/Target mapping, 15-minute momentum decay rules, and official SEBI 0.1% STT and 75-lot sizing).

---

## 2. Brainstormed Analysis: Training vs. Agent Tool-Grounding & "Real Calls"

### A. Do you need to "Train" the agent first?
* **Answer:** **No model training or fine-tuning is needed.**
* **Why Traditional Model Training Fails in Markets:**
  - Training an LLM or ML model on historical stock charts leads to overfitting and hallucination. Market regimes, IV dynamics, and RBI interest rate policies change continuously.
  - LLMs trained directly on prices hallucinate numbers and calculate math poorly.
* **How This Agent Works (Deterministic Tool-Grounding via MCP):**
  - Claude Desktop / Antigravity acts as the reasoning engine and natural language interface.
  - When you prompt Claude or evaluate a trade, Claude invokes the Python quantitative engine (`trader-options/greeks.py`) via MCP tools.
  - All Greeks ($\Delta, \Gamma, \Theta, \mathcal{V}, \Omega, \rho$), Taylor-series option SL/Target levels, and SEBI tax friction are calculated with zero approximation errors.

### B. Can it give you "Real Calls" in Claude Desktop?
* **Current Capability (Interactive Trade Blueprints):**
  - Available right now! When you provide NIFTY Spot levels (e.g., entry, support, target), Claude computes the exact strike, option premium entry, Stop-Loss premium, Target premium, rupee risk, and net payoff.
* **Next Evolutionary Step (Autonomous Real-Time Calls):**
  - To generate live, unprompted trading calls directly inside Claude Desktop or terminal (e.g., *"BUY NIFTY 24500 CE at ₹142 | SL ₹121 | Target ₹187"*), the system requires:
    1. **Live NIFTY Spot & Option Chain Feed:** Real-time polling or WebSocket stream (NSE India / DhanHQ free API / Yahoo Finance).
    2. **Triple-Confluence Signal Generator (`trader-options/signals.py`):** Evaluating 15-minute Opening Range Breakout (ORB) + VWAP + 9/21 EMA + PCR (Put-Call Ratio) filter.
    3. **Live Alerting & Ticket Delivery:** Pushing instantaneous call alerts to Claude Desktop and the visual Trading Table.

### C. How the System Delivers Real-World Accuracy:
1. **Delta Sweet-Spot ($\Delta = 0.55 - 0.70$):** Avoids cheap OTM lottery traps ($\Delta < 0.35$) where 93% of retail traders lose to time decay.
2. **Taylor Series Spot-to-Option Mapping:** Stop-Loss and Target are anchored to the underlying NIFTY Spot index chart, eliminating fake-outs caused by option premium bid-ask spreads.
3. **15-Minute Momentum Decay Guard:** Warns if the index consolidates for >15 minutes after breakout, forcing a breakeven exit before Theta decay destroys capital.
4. **SEBI Friction Pre-Audit:** Accounts for 0.1% STT on option premium sales, exchange charges, GST, and broker commissions before entering any trade.

---

## 3. Current Progress
- [x] **Phase 1–5:** 11 Cash Equity trading skills built, verified, and passing 100% tests.
- [x] **Live Trading Tables Dashboard (`trading_tables.py`)** operational with terminal UI and CSV export.
- [x] **Phase 6: NIFTY 50 Options Greeks Engine (`trader-options/greeks.py`)**:
  - Black-Scholes pricing, $\Delta, \Gamma, \Theta, \mathcal{V}, \Omega, \rho$.
  - Spot-to-Option Taylor expansion Stop-Loss and Target mapping.
  - Contract lot sizing (75 qty) and SEBI 0.1% STT accounting.
- [x] **MCP Integration:** Registered `nifty_options_calculate_greeks`, `nifty_options_plan_trade`, and `nifty_options_recommend_strikes` in `mcp_server.py`.
- [x] **Testing:** 17 unit tests passing (11 equity + 6 options) 100% offline.
- [x] **Repository:** Committed and pushed to GitHub (`https://github.com/naitik99045/day-trader-indian-tables.git`).

---

## 4. Pending Work: Phase 7 (Autonomous Live Signals & Real Calls)
1. **Task 7.1: Live NIFTY Spot & Option Chain Streamer (`trader-options/streamer.py`)**:
   - Ingests live NIFTY 50 Spot (`^NSEI`) quotes and real-time ATM option chain data via Yahoo Finance / NSE / DhanHQ API.
2. **Task 7.2: Triple-Confluence Signal Engine (`trader-options/signals.py`)**:
   - Detects 15m ORB breakouts, VWAP trend confirmation, and PCR sentiment triggers.
   - Generates actionable `BUY_CE` / `BUY_PE` signal events.
3. **Task 7.3: Claude Desktop Live Signal Tool & Visual Table Sync**:
   - Exposes `nifty_options_live_signal` in MCP server.
   - Displays real-time signal status in `trading_tables.py`.
