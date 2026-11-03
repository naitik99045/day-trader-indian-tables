# Project State & Context
**Last Updated:** 2026-11-03 10:55:00 IST

## 1. Project Overview
The **Indian Stock Market Day Trading Skill Suite (`day-trader-indian-tables`)** is explicitly positioned as a **Pure Quantitative Trade Analyst & Copilot** for manual retail traders. 
The system does **NOT** execute auto-trades or place orders autonomously. Instead, it provides precision mathematical analysis for **NIFTY 50 Intraday Options (CE & PE)**:
- Exact Spot-to-Option Stop-Loss mapping.
- Gamma-boosted Target setting.
- Definite Time-in-Trade limits (15–20 minutes momentum window) and rupee-per-hour Theta decay tracking.
- Pre-trade confluence checklist (Spot ORB, VWAP, India VIX, PCR, OI Strike Walls).
- SEBI statutory friction audit (0.1% STT, GST, Exchange charges, Brokerage).

---

## 2. Brainstormed Analysis: The Precision Options Analyst Architecture

### A. Role Definition: 100% Analyst Copilot (No Auto-Trading)
The user retains full manual execution control through their broker terminal (Zerodha Kite, Dhan, Groww, AngelOne). Claude Desktop acts as the quantitative brain:
1. **Inputs from Trader:** Trader observes NIFTY 50 Spot index chart and feeds 3 numbers into Claude:
   - Spot Entry (e.g. 24,500)
   - Technical Spot Stop-Loss (e.g. 24,460)
   - Technical Spot Target (e.g. 24,580)
   - Direction (CE or PE)
2. **Analysis by Claude (via MCP Tool `nifty_options_plan_trade`):**
   - Strips away guesswork using Black-Scholes-Merton and second-order Taylor expansion.
   - Outputs an exact trade blueprint card.

### B. The 5 Confluence Checks Before Entering ("What All to See"):
1. **Spot Chart Structure:** 15m Opening Range Breakout (09:15–09:30 candle high/low breached on completed 5m bar).
2. **VWAP & Trend Confirmation:** Price trading above VWAP for Call (CE); below VWAP for Put (PE).
3. **PCR (Put-Call Ratio):** PCR > 1.10 indicates bullish put-writing support; PCR < 0.85 indicates bearish call-writing resistance.
4. **India VIX (Implied Volatility):** Stable or rising VIX supports option buyers; plunging VIX causes IV crush.
5. **Open Interest (OI) Walls:** Ensure entry is not directly into a massive Call OI strike (e.g., round 24,500/24,600 numbers).

### C. Precision Mathematical Formulations:
1. **Target Premium Formulation (Delta + Gamma Acceleration):**
   $$V_{\text{target}} = V_0 + (\Delta S \cdot \Delta) + \frac{1}{2}\Gamma(\Delta S)^2$$
2. **Stop-Loss Premium Formulation (Linear Delta Protection):**
   $$V_{\text{sl}} = V_0 - |\Delta S_{\text{risk}}| \cdot \Delta$$
3. **Time-in-Trade Decay Limit ("For How Much Time"):**
   - Standard intraday option buying window: **15 to 20 minutes (3 to 4 five-minute candles)**.
   - Hourly Decay Rate: $\Theta_{\text{hourly}} = \frac{\Theta_{\text{daily}} / 365}{6.25 \text{ hrs}}$.
   - If NIFTY consolidates for >15 mins without hitting Target, decay accelerates $\rightarrow$ Trail SL to Breakeven or Exit Flat.
   - Hard Cutoff: **15:15 IST** (mandatory exit to avoid broker MIS penalties).

---

## 3. Current Progress
- [x] Phase 1–5: Cash Equities skills and live trading tables complete.
- [x] Phase 6: NIFTY 50 Options Greeks Engine (`trader-options/greeks.py`) complete.
- [x] MCP Server (`mcp_server.py`) registered with 3 options tools.
- [x] All 17 unit tests passing 100% offline.
- [x] Repository pushed and synced to GitHub (`https://github.com/naitik99045/day-trader-indian-tables.git`).

---

## 4. Pending Work: Phase 7 (Interactive Analysis Card & Confluence Enhancer)
1. **Task 7.1: Visual Confluence Checklist Generator (`trader-options/checklist.py`)**:
   - Generates a 5-point go/no-go visual table (Spot Breakout, VWAP, PCR, India VIX, Time-of-Day).
2. **Task 7.2: Time-in-Trade Timer & Decay Card in MCP Tool**:
   - Enhances `nifty_options_plan_trade` output with an explicit "Time-in-Trade Countdown" and hourly decay cost breakdown.
3. **Task 7.3: Claude Desktop "Analyze My Trade" Prompt Preset**:
   - Documented and tested standardized prompt templates for 1-click trade auditing.
