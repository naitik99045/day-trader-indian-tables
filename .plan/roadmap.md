# Project Execution Roadmap
**Status:** Active (Phase 6: NIFTY Options Engine Queued)
**Instruction for Execution Agent:** Pick the first unchecked `[ ]` task in the current active phase, implement it completely without placeholders, verify it, and mark it `[x]`.

## Phase 1: Foundation, Config & Scaffolding
- [x] **Task 1.1: Indian Market Foundation & Configuration Schema**
- [x] **Task 1.2: NSE/BSE Universe Generator & Symbol Normalization**

## Phase 2: Data Layer, State & Broker Connectors
- [x] **Task 2.1: Indian Paper Broker Engine & Ticket Handler**
- [x] **Task 2.2: Pre-Trade Risk Engine with Statutory Tax & Circuit Guards**

## Phase 3: Core Feature Modules (Iterative Build)
- [x] **Task 3.1: Indian Market Scanner (`trader-scanner`)**
- [x] **Task 3.2: IST Entry Timer & Exit Planner (`trader-entry` & `trader-exit`)**
- [x] **Task 3.3: Indian Equities Time Machine (`trader-timemachine`)**
- [x] **Task 3.4: Position Sizing & Budget Manager (`trader-budget`)**
- [x] **Task 3.5: Indian Market News & Analyst (`trader-news` & `trader-analyst`)**
- [x] **Task 3.6: Smart Money Flow Tracker (`trader-fii-dii` replacing `trader-pelosi`)**
- [x] **Task 3.7: Indian Market Alerts & IST Clock (`trader-alerts`)**

## Phase 4: UI Polish, Edge Cases & Interactive States
- [x] **Task 4.1: Claude & Antigravity Skill Packaging & Manifests**
- [x] **Task 4.2: Comprehensive Offline Test Suite with Real NSE Fixtures**

## Phase 5: Security Audit & Production Readiness
- [x] **Task 5.1: Defensive Audit & Final Verification**

## Phase 6: NIFTY 50 Options Scalping & Momentum Engine
- [ ] **Task 6.1: NIFTY Option Strike Selector & Delta/Theta Modeling**
  - *Action:* Implement `trader-options/strikes.py` to ingest Nifty Spot price (`^NSEI`), determine At-The-Money (ATM) and In-The-Money (ITM) strikes (50-point step intervals), calculate Black-Scholes Greeks (Delta 0.55-0.70, Theta decay/hour), and filter out illiquid/low-delta OTM traps.
  - *Target Files:* `trader-options/strikes.py`, `trader-options/SKILL.md`
  - *Done When:* Running `python trader-options/strikes.py --spot 24500` outputs optimal CE & PE strike symbols, premiums, and delta.
- [ ] **Task 6.2: NIFTY Spot Momentum & PCR/OI Sentiment Engine**
  - *Action:* Implement `trader-options/signals.py` to track Nifty 50 spot index 3m/5m candles for 15-minute Opening Range Breakouts (ORBs), VWAP cross, and 9/21 EMA trend alignment; cross-validate with Put-Call Ratio (PCR) and Open Interest (OI) support/resistance strike walls.
  - *Target Files:* `trader-options/signals.py`
  - *Done When:* Generates high-confidence directional signals (`BUY_CE` or `BUY_PE`) with spot trigger, index stop, and target levels.
- [ ] **Task 6.3: Options Lot Sizer & SEBI Cost Engine**
  - *Action:* Implement `trader-options/risk.py` to size positions strictly in NSE NIFTY contract lot sizes (multiples of 75/65), enforce rupee max loss caps (e.g., ₹1,500 per lot), calculate the revised 0.1% STT on option premium sale, exchange turnover fees, and GST, and enforce a 15-minute momentum decay timeout.
  - *Target Files:* `trader-options/risk.py`
  - *Done When:* Outputs sized option ticket with exact premium stop-loss, profit target, and net payoff after statutory taxes.
- [ ] **Task 6.4: Claude Desktop & Antigravity MCP Integration for Options**
  - *Action:* Update `mcp_server.py` and `trading_tables.py` to add `nifty_options_signal`, `nifty_options_plan`, and `nifty_options_execute` tools, plus a live NIFTY Options Chain & Watchlist table.
  - *Target Files:* `mcp_server.py`, `trading_tables.py`, `tests/test_nifty_options.py`
  - *Done When:* Claude Desktop exposes NIFTY options tools and all unit tests pass 100% offline.
