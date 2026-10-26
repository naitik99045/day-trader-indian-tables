# Project Execution Roadmap
**Status:** Completed
**Instruction for Execution Agent:** All phases and core functional modules have been implemented without placeholders and verified with 100% passing tests.

## Phase 1: Foundation, Config & Scaffolding
- [x] **Task 1.1: Indian Market Foundation & Configuration Schema**
  - *Action:* Establish root configuration models for the Indian market (`trader/config.example.json`), defining INR defaults, IST trading windows (`09:15` to `15:30`), `flat_by` at `15:15` IST, `no_entries_after` at `15:00` IST, NSE trading calendar (2026-2027 holidays & Muhurat trading), and brokerage/STT tax parameters.
  - *Target Files:* `trader-budget/config.example.json`, `trader/config.example.json`, `trader-alerts/alerts.py` (calendar constants)
  - *Done When:* Sample config validates cleanly under Python JSON parser with all Indian trading parameters present.
- [x] **Task 1.2: NSE/BSE Universe Generator & Symbol Normalization**
  - *Action:* Build Indian universe list containing liquid NSE symbols (Nifty 50, Nifty Next 50, Nifty Midcap 100) with `.NS` suffixes for Yahoo Finance integration, plus helper functions to strip/add suffixes across exchanges.
  - *Target Files:* `trader/universe.txt`, `trader-scanner/scan.py`
  - *Done When:* Universe file contains 150+ liquid NSE symbols and normalizer correctly maps `RELIANCE` <-> `RELIANCE.NS`.

## Phase 2: Data Layer, State & Broker Connectors
- [x] **Task 2.1: Indian Paper Broker Engine & Ticket Handler**
  - *Action:* Implement `trader-broker/ticket.py` and `trader-broker/paper_broker.py` for simulated trading with INR cash balance, whole-share validation, simulated execution slippage, order states (`PENDING`, `PLACED`, `REJECTED`, `FILLED`, `CANCELLED`), and DhanHQ / Zerodha Kite Connect JSON ticket schemas.
  - *Target Files:* `trader-broker/ticket.py`, `trader-broker/paper_broker.py`, `trader-broker/SKILL.md`
  - *Done When:* Running `python trader-broker/ticket.py show` and simulated fills updates `trader/portfolio.json` with accurate INR balance and holdings.
- [x] **Task 2.2: Pre-Trade Risk Engine with Statutory Tax & Circuit Guards**
  - *Action:* Implement `trader-risk/check.py` adapted for India: checks max loss in INR, daily loss limit, 5x MIS margin requirements, no fractional shares, upper/lower circuit limit proximity (5%, 10%, 20%), and verifies net profitability after deducting STT, exchange fees, SEBI charges, stamp duty, and GST.
  - *Target Files:* `trader-risk/check.py`, `trader-risk/SKILL.md`
  - *Done When:* Test orders trigger `PASS` or `BLOCK` with explicit statutory cost breakdowns and fingerprint generation in `trader/state/risk.json`.

## Phase 3: Core Feature Modules (Iterative Build)
- [x] **Task 3.1: Indian Market Scanner (`trader-scanner`)**
  - *Action:* Adapt `scan.py` to scan NSE universe (`.NS` tickers) for 15-minute Opening Range Breakouts (09:15 - 09:30 AM IST), pre-market gap-ups, and volume surges via Yahoo Finance Spark/Chart API with rate-limiting and fallback headers.
  - *Target Files:* `trader-scanner/scan.py`, `trader-scanner/SKILL.md`
  - *Done When:* `python trader-scanner/scan.py orb --at 09:45` successfully scans offline fixtures or live NSE quotes and outputs formatted table and `trader/watchlist.json`.
- [x] **Task 3.2: IST Entry Timer & Exit Planner (`trader-entry` & `trader-exit`)**
  - *Action:* Adapt `entry.py` and `exit.py` to monitor 5-minute candles starting at 09:15 AM IST, trigger on first completed candle close above ORB high, calculate stop at ORB midpoint or ATR in INR, target at 1R/2R, and enforce `flat_by: 15:15` IST.
  - *Target Files:* `trader-entry/entry.py`, `trader-exit/exit.py`, `trader-entry/SKILL.md`, `trader-exit/SKILL.md`
  - *Done When:* `entry.py check RELIANCE.NS` detects trigger and `exit.py plan --write` produces valid `trader/plan.json` with INR values.
- [x] **Task 3.3: Indian Equities Time Machine (`trader-timemachine`)**
  - *Action:* Adapt Monte Carlo simulation to pull 60 days of 5-minute bars for NSE stocks, partition daily sessions (09:15 to 15:30 IST = 75 bars), run 10,000 synthetic paths with conservative stop-first logic, and backtest historical setup outcomes.
  - *Target Files:* `trader-timemachine/timemachine.py`, `trader-timemachine/SKILL.md`
  - *Done When:* Running `timemachine.py run` prints the win/loss distribution, percentile fans, and saves `trader/timemachine.json`.
- [x] **Task 3.4: Position Sizing & Budget Manager (`trader-budget`)**
  - *Action:* Adapt `size.py` to read `trader/plan.json`, account cash, and risk limits in INR; compute integer whole shares using SEBI 5x MIS leverage without fractional units; write bracket/MIS order to `trader/orders.json`.
  - *Target Files:* `trader-budget/size.py`, `trader-budget/SKILL.md`
  - *Done When:* Sizing allocates exact integer shares matching INR risk budget and outputs valid ticket format.
- [x] **Task 3.5: Indian Market News & Analyst (`trader-news` & `trader-analyst`)**
  - *Action:* Adapt `news.py` to ingest Indian business headlines (Yahoo Finance India RSS, Moneycontrol, LiveMint) and corporate announcements; adapt `facts.py` to parse quarterly financial performance (Revenue, EBITDA, Net Profit, EPS, Promoter Holding).
  - *Target Files:* `trader-news/news.py`, `trader-analyst/facts.py`, `trader-news/SKILL.md`, `trader-analyst/SKILL.md`
  - *Done When:* `news.py` fetches relevant ticker news and `facts.py` outputs quarterly financial scorecard.
- [x] **Task 3.6: Smart Money Flow Tracker (`trader-fii-dii` replacing `trader-pelosi`)**
  - *Action:* Build `trader-fii-dii/tracker.py` to track daily NSE FII (Foreign Institutional Investors) and DII (Domestic Institutional Investors) cash flows, Bulk & Block deals, and SEBI insider trading (PIT) disclosures.
  - *Target Files:* `trader-fii-dii/tracker.py`, `trader-fii-dii/SKILL.md`
  - *Done When:* `tracker.py index` displays daily institutional net flow and active bulk deals.
- [x] **Task 3.7: Indian Market Alerts & IST Clock (`trader-alerts`)**
  - *Action:* Adapt `alerts.py` with NSE/BSE trading clock, market phase awareness (Pre-open, Live, Intraday Cutoff, Closed), NSE holiday calendar, price threshold alerts, and audio/terminal chimes.
  - *Target Files:* `trader-alerts/alerts.py`, `trader-alerts/SKILL.md`
  - *Done When:* `python trader-alerts/alerts.py clock` accurately displays current IST market state and next session milestone.

## Phase 4: UI Polish, Edge Cases & Interactive States
- [x] **Task 4.1: Claude & Antigravity Skill Packaging & Manifests**
  - *Action:* Create `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, Antigravity skill definitions (`SKILL.md` in each module directory), root `README.md` with complete Indian market quickstart, and interactive CLI menus.
  - *Target Files:* `.claude-plugin/plugin.json`, `.claude-plugin/marketplace.json`, `README.md`, all `SKILL.md` files
  - *Done When:* Both Claude Code and Google Antigravity recognize and load all 11 skills with working slash commands.
- [x] **Task 4.2: Comprehensive Offline Test Suite with Real NSE Fixtures**
  - *Action:* Construct offline test fixtures using real historical NSE 5-minute data (e.g., `RELIANCE.NS`, `TCS.NS`, `INFY.NS`) and implement unit tests across all 11 modules.
  - *Target Files:* `tests/test_*.py`, `tests/fixtures/...`
  - *Done When:* `python -m unittest discover -s tests -v` runs completely offline with 100% passing tests.

## Phase 5: Security Audit & Production Readiness
- [x] **Task 5.1: Defensive Audit & Final Verification**
  - *Action:* Execute security and boundary audit: ensure zero hardcoded secrets or API keys, verify input sanitization against command injection, enforce read-only safe defaults, confirm `paper: true` is enforced by default, and generate the final audit report.
  - *Target Files:* `.agent/security_report.md`
  - *Done When:* All high/medium vulnerabilities are `[FIXED]` and build succeeds.
