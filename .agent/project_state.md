# Project State & Context
**Last Updated:** 2026-10-26 14:40:00 IST

## 1. Project Overview
The **Indian Stock Market Day Trading Skill Suite (`indian-day-trader-skill`)** provides 11 native AI tools adapted from `day-trader-skill` for the Indian Equities Market (NSE / BSE).

This update adds **Live Indian Trading Tables Dashboard** (`trading_tables.py`) and a native **Claude Desktop Model Context Protocol (MCP) Server** (`mcp_server.py`), enabling direct visual monitoring and conversational trade execution inside Claude Desktop, Excel/Google Sheets, and terminal environments.

## 2. Indian Trading Tables & Claude Desktop Integrations
1. **Interactive Trading Tables Dashboard (`trading_tables.py`)**:
   - Displays real-time NSE Watchlist Table with LTP, 15m ORB High/Low, Breakout %, and Volume multipliers.
   - Displays Open Positions & PnL Table in INR with blocked margin, realized PnL, and statutory taxes.
   - Exports live CSV (`trader/trading_tables.csv`) for seamless sync with Excel or Google Sheets tables.
2. **Claude Desktop MCP Server (`mcp_server.py`)**:
   - Stdio JSON-RPC bridge allowing Claude Desktop to discover and execute all Indian trading skills.
   - Connects to `%APPDATA%\Claude\claude_desktop_config.json`.
   - Exposes: `indian_market_clock`, `indian_scan_orb`, `indian_check_entry`, `indian_plan_exit`, `indian_run_timemachine`, `indian_size_position`, `indian_risk_check`, `indian_paper_execute`, and `indian_fii_dii_flows`.
3. **Broker Connectors for Indian Platforms**:
   - **DhanHQ API & Webhook**: Free retail API integration for order execution.
   - **Zerodha Kite Connect**: Automated bracket and MIS order payloads.
   - **Indian Paper Broker**: Zero-risk local simulated trading engine with accurate SEBI tax accounting.

## 3. Current Progress
- [x] All 11 trading skills implemented, tested, and passing 100% offline tests.
- [x] Live Indian Trading Tables dashboard created (`trading_tables.py`).
- [x] Native MCP server created for Claude Desktop (`mcp_server.py`).
- [x] Configuration example generated for Claude Desktop (`trader-broker/claude_desktop_config.example.json`).
- [x] Tested MCP handshake and tool calls over stdio JSON-RPC.

## 4. Next Steps & Usage
1. Configure Claude Desktop by adding `mcp_server.py` to `claude_desktop_config.json`.
2. Launch live trading table via `python trading_tables.py`.
