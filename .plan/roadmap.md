# Project Execution Roadmap
**Status:** Active (Phase 7: Precision Options Trade Analysis & Confluence Copilot Queued)
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

## Phase 6: NIFTY 50 Options Greeks & Taylor Expansion Engine
- [x] **Task 6.1: NIFTY Option Strike Selector & Greeks Engine (`trader-options/greeks.py`)**
- [x] **Task 6.2: Spot-to-Option Taylor Series Stop-Loss & Target Engine**
- [x] **Task 6.3: Options Lot Sizing (75 qty) & SEBI 0.1% STT Friction Calculation**
- [x] **Task 6.4: Claude Desktop MCP Server Integration (`mcp_server.py`) & Tests**

## Phase 7: Quantitative Copilot & Precision Trade Analysis Card
- [ ] **Task 7.1: Pre-Trade Confluence Checklist Engine (`trader-options/checklist.py`)**
  - *Action:* Implement a checklist evaluator checking Spot 15m ORB, VWAP slope, PCR sentiment, and India VIX regime.
  - *Target Files:* `trader-options/checklist.py`
  - *Done When:* Running checklist gives a numerical score (0 to 100%) and clear Go / No-Go decision.
- [ ] **Task 7.2: Holding Duration & Time Decay Alert Generator**
  - *Action:* Enhance `plan_nifty_option_trade` in `trader-options/greeks.py` to output a precise 5m candle countdown (Candle 1-3: Ride momentum, Candle 4: 20-min breakeven trigger, 15:15 IST hard square-off).
  - *Target Files:* `trader-options/greeks.py`, `tests/test_nifty_options.py`
  - *Done When:* Output explicitly displays the time limit, decay per 5-minute bar, and trailing rule.
- [ ] **Task 7.3: Claude Desktop Analysis Prompt Templates & Documentation**
  - *Action:* Update `README.md` and `trader-options/SKILL.md` with copy-paste prompts designed purely for trade planning, stop-loss calculation, and target analysis without automated order execution.
  - *Target Files:* `README.md`, `trader-options/SKILL.md`
  - *Done When:* Claude Desktop returns structured, precision trade cards upon simple prompts.
