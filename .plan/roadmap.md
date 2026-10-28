# Project Execution Roadmap
**Status:** Active (Phase 7: Live Signal Generator & Real Calls Queued)
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
- [x] **Task 3.6: Smart Money Flow Tracker (`trader-fii-dii`)**
- [x] **Task 3.7: Indian Market Alerts & IST Clock (`trader-alerts`)**

## Phase 4: UI Polish, Edge Cases & Interactive States
- [x] **Task 4.1: Claude & Antigravity Skill Packaging & Manifests**
- [x] **Task 4.2: Comprehensive Offline Test Suite with Real NSE Fixtures**

## Phase 5: Security Audit & Production Readiness
- [x] **Task 5.1: Defensive Audit & Final Verification**

## Phase 6: NIFTY 50 Options Greeks Engine
- [x] **Task 6.1: NIFTY Option Strike Selector & Greeks Engine (`trader-options/greeks.py`)**
- [x] **Task 6.2: Spot-to-Option Taylor Series Stop-Loss & Target Engine**
- [x] **Task 6.3: Options Lot Sizing (75 qty) & SEBI 0.1% STT Friction Calculation**
- [x] **Task 6.4: Claude Desktop MCP Server Integration (`mcp_server.py`) & Tests**

## Phase 7: Autonomous Live Signals & Real-Time Calls
- [ ] **Task 7.1: Live NIFTY Spot & Option Quote Streamer (`trader-options/streamer.py`)**
  - *Action:* Implement live quotes fetcher for NIFTY 50 Spot (`^NSEI`) and nearest ATM strikes via Yahoo Finance / NSE public endpoint / DhanHQ free API with offline mock fallback.
  - *Target Files:* `trader-options/streamer.py`
  - *Done When:* Running `python trader-options/streamer.py` outputs live spot price, ATM strike quotes, and PCR without external pip packages.
- [ ] **Task 7.2: Triple-Confluence Signal Generator (`trader-options/signals.py`)**
  - *Action:* Implement signal detector evaluating: (1) 15m ORB breakout on Spot, (2) VWAP trend confirmation, (3) Put-Call Ratio (PCR > 1.1 for CE, < 0.85 for PE), and (4) Delta sweet-spot filter.
  - *Target Files:* `trader-options/signals.py`
  - *Done When:* Emits high-probability `BUY_CE` or `BUY_PE` signals with spot trigger, option entry, stop-loss, and target levels.
- [ ] **Task 7.3: Claude Desktop Real-Time Call MCP Tool (`mcp_server.py`)**
  - *Action:* Register `nifty_options_get_live_call` in `mcp_server.py` and add unit test coverage in `tests/test_nifty_signals.py`.
  - *Target Files:* `mcp_server.py`, `tests/test_nifty_signals.py`
  - *Done When:* Invoking `nifty_options_get_live_call` via MCP returns formatted trade recommendations with exact premiums, stop-losses, and profit targets.
