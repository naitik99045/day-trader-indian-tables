# Project State & Context
**Last Updated:** 2026-10-28 21:30:00 IST

## 1. Project Overview
The **Indian Stock Market Day Trading Skill Suite (`day-trader-indian-tables`)** is currently fully functional for **Cash Equity Day Trading** (`MIS`/`CNC`) on liquid NSE stocks (`RELIANCE.NS`, `TCS.NS`, etc.).

Based on recent user demand and in-depth quantitative research from retail trading communities (Reddit r/IndianStreetBets, TradingQ&A, Sensibull, Zerodha Varsity), we are expanding the platform to support **NIFTY 50 Intraday Options Trading (Momentum & Scalping)** with institutional-grade risk controls.

## 2. NIFTY Options Feasibility & Quant Research Summary

### Can the current bot trade Nifty options right now?
* **Current Status:** Not natively for options contracts. The existing code trades whole shares of equities (`RELIANCE.NS`, `INFY.NS`). Options have non-linear pricing, contract lot sizes (75 / 65 qty), weekly expiries, strike prices (CE/PE), and Greeks (Delta, Theta, Gamma, Vega).
* **Why Naked Retail Option Buying Usually Fails:**
  1. **The "Theta Trap" & Cheap OTM Lottery Tickets:** 90% of retail option buyers buy cheap Out-of-the-Money (OTM) calls/puts with Delta < 0.35. Even if Nifty moves in their direction, Theta (time decay) and IV crush wipe out the premium.
  2. **Union Budget 2024 / SEBI STT Hike:** STT on the sale of options was raised to **0.1% of premium**, increasing transaction drag on scalping.
  3. **SEBI Lot Size Revisions:** Contract lot size recalibrated (baseline ₹15-20 Lakhs contract size).

### How the Upgraded Bot Gains True Accuracy in NIFTY Options:
To achieve high win-rate and asymmetric risk/reward in fast intraday options trading, the bot incorporates the 6 quant pillars identified from profitable retail scalpers:
1. **Dual-Chart Architecture (NIFTY Spot Index Trigger ➔ Strike Execution):**
   * Never trade based on option charts alone. The bot monitors the **NIFTY 50 Spot Index (`^NSEI`)** on 3m/5m candles for high-probability setups (15m ORB, VWAP + 9/21 EMA pullback, Supertrend breakout).
   * Bullish breakout on NIFTY Spot ➔ Auto-select **NIFTY Call (CE)**.
   * Bearish breakdown on NIFTY Spot ➔ Auto-select **NIFTY Put (PE)**.
2. **Strict Strike Selection (Delta 0.55 - 0.70 | Slight ITM or Strict ATM):**
   * Eliminates the OTM lottery trap. The bot selects either At-The-Money (ATM) or 1 strike In-The-Money (ITM) options.
   * High Delta ensures that a 30-point burst in Nifty instantly gives 18–22 points of premium expansion.
3. **Theta Decay & Time-in-Trade Guard (Momentum Timeout):**
   * Intraday option buying requires velocity. If the index consolidates for >15 minutes (3 candles) without momentum continuation, the bot triggers a warning or tightens the stop to breakeven to prevent time decay erosion.
4. **PCR & Open Interest (OI) Analysis Filter:**
   * Reads Put-Call Ratio (PCR): PCR > 1.2 indicates strong put-writing support (favouring CE); PCR < 0.8 indicates heavy call-writing resistance (favouring PE).
   * Identifies Call/Put OI strike walls to ensure the bot does not buy Call options directly under major resistance walls.
5. **Contract Lot Sizing & Statutory Cost Engine:**
   * Sizing calculated strictly in official NSE lot sizes (e.g. 75 qty / 65 qty).
   * Risk per trade capped (e.g. 1 lot with 15–20 point premium stop loss = ₹1,125 to ₹1,500 maximum risk).
   * Pre-trade deduction of 0.1% STT on sell side, exchange charges, GST, and brokerage.
6. **Execution via Dhan / Zerodha API or Local Paper Broker:**
   * Generates exact exchange ticker symbols (`NIFTY26OCT25000CE`, `NIFTY26OCT25000PE`) for DhanHQ or Zerodha Kite Connect F&O execution.

---

## 3. Current Progress
- [x] Phase 1–5 complete: 11 Cash Equity trading skills built, verified, and passing 100% tests.
- [x] Live trading tables dashboard (`trading_tables.py`) and Claude Desktop MCP server (`mcp_server.py`) operational.
- [x] Pushed to GitHub repository: `https://github.com/naitik99045/day-trader-indian-tables.git`.
- [ ] Phase 6 planned: NIFTY 50 Options Scalping & Momentum Engine.

---

## 4. Pending Work: Phase 6 (NIFTY Options Engine)
1. **Task 6.1: NIFTY Option Strike Selector & Greeks Engine (`trader-options/strikes.py`)**:
   - Calculates ATM / ITM strikes based on Nifty 50 spot price.
   - Estimates Delta (0.55–0.70), Gamma, and Theta decay per hour.
2. **Task 6.2: NIFTY Index Momentum & Confluence Signal (`trader-options/signals.py`)**:
   - 15m ORB + VWAP + 9/21 EMA breakout detector for NIFTY spot index (`^NSEI`).
   - PCR and Open Interest (OI) sentiment filter.
3. **Task 6.3: Options Risk, Lot Sizer & SEBI Cost Calculator (`trader-options/risk.py`)**:
   - Computes lot quantities (multiples of 75/65), premium stop-loss, and target in ₹.
   - Calculates 0.1% STT on premium, exchange turnover charges, and GST.
4. **Task 6.4: Integration with Claude Desktop MCP Server (`mcp_server.py`)**:
   - Exposes `nifty_options_scan`, `nifty_options_plan`, and `nifty_options_paper_execute` to Claude Desktop.
