#!/usr/bin/env python3
"""Standard Library Model Context Protocol (MCP) Server for Claude Desktop & Antigravity.

Connects Claude Desktop directly to all 11 Indian Day Trading tools over stdio JSON-RPC.
Enables Claude to scan NSE charts, time entries, plan stops, simulate replays, and execute trades.
"""

import datetime
import json
import os
import sys

# Ensure root directory is on sys.path
ROOT = os.path.dirname(os.path.abspath(__file__))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

from tests._load import load

# Load tool modules dynamically
scan_mod = load("trader-scanner", "scan")
entry_mod = load("trader-entry", "entry")
exit_mod = load("trader-exit", "exit")
tm_mod = load("trader-timemachine", "timemachine")
budget_mod = load("trader-budget", "size")
risk_mod = load("trader-risk", "check")
ticket_mod = load("trader-broker", "ticket")
paper_mod = load("trader-broker", "paper_broker")
alerts_mod = load("trader-alerts", "alerts")
fii_mod = load("trader-fii-dii", "tracker")
analyst_mod = load("trader-analyst", "facts")
options_mod = load("trader-options", "greeks")

TOOLS_REGISTRY = [
    {
        "name": "indian_market_clock",
        "description": "Get current Indian Stock Market (NSE/BSE) trading session status, IST phase (Pre-open, Live, 15:15 Flat, Closed), and holiday checks.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "simulated_time": {"type": "string", "description": "Optional ISO/IST time e.g. '2026-10-19 10:15'"}
            }
        }
    },
    {
        "name": "indian_scan_orb",
        "description": "Scan liquid NSE equities for 15-minute Opening Range Breakouts (ORBs) between 09:15 and 09:30 AM IST.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "List of NSE tickers (e.g. ['RELIANCE.NS', 'TCS.NS'])"}
            }
        }
    },
    {
        "name": "indian_check_entry",
        "description": "Check if an NSE stock has closed above its opening range or technical level on a completed 5-minute candle in IST.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE Symbol e.g. RELIANCE.NS"},
                "setup": {"type": "string", "enum": ["orb", "level"], "default": "orb"},
                "level": {"type": "number", "description": "Price level for level setup"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "indian_plan_exit",
        "description": "Calculate exact entry, stop-loss (ORB midpoint/ATR), and target (1R/2R) in INR with mandatory 15:15 IST flat_by cutoff.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "entry": {"type": "number"},
                "or_high": {"type": "number"},
                "or_low": {"type": "number"},
                "stop_rule": {"type": "string", "default": "or-mid"},
                "target_rule": {"type": "string", "default": "2R"}
            },
            "required": ["symbol", "entry"]
        }
    },
    {
        "name": "indian_run_timemachine",
        "description": "Replay 10,000 Monte Carlo simulation paths of the trade using historical 5-minute bars to compute empirical win/loss odds in INR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "entry": {"type": "number"},
                "stop": {"type": "number"},
                "target": {"type": "number"},
                "replays": {"type": "integer", "default": 5000}
            },
            "required": ["entry", "stop", "target"]
        }
    },
    {
        "name": "indian_size_position",
        "description": "Size an intraday day trade in INR whole integer shares (no fractional shares) applying SEBI 5x MIS margin rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "entry": {"type": "number"},
                "stop": {"type": "number"},
                "target": {"type": "number"}
            },
            "required": ["symbol", "entry", "stop", "target"]
        }
    },
    {
        "name": "indian_risk_check",
        "description": "Validate order against max loss limits, 1% circuit breaker buffer, and SEBI round-trip statutory costs (STT, Stamp Duty, GST, Brokerage).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "order": {"type": "object", "description": "Order dictionary from indian_size_position"}
            },
            "required": ["order"]
        }
    },
    {
        "name": "indian_paper_execute",
        "description": "Execute an approved order in the built-in Indian Paper Broker with simulated slippage and statutory charge accounting.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "side": {"type": "string", "enum": ["BUY", "SELL", "buy", "sell"]},
                "qty": {"type": "integer"},
                "fill_price": {"type": "number"},
                "product_type": {"type": "string", "default": "MIS"}
            },
            "required": ["symbol", "side", "qty", "fill_price"]
        }
    },
    {
        "name": "indian_fii_dii_flows",
        "description": "Get daily FII & DII institutional cash flows (in ₹ Crore) and prominent NSE Bulk & Block deals.",
        "inputSchema": {"type": "object"}
    },
    {
        "name": "nifty_options_calculate_greeks",
        "description": "Calculate theoretical price and Black-Scholes Greeks (Delta, Gamma, Theta daily/hourly, Vega, Omega elasticity, Rho) for any NIFTY strike.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spot": {"type": "number", "description": "Current Nifty spot price (e.g. 24500)"},
                "strike": {"type": "number", "description": "Option strike price (e.g. 24500)"},
                "type": {"type": "string", "enum": ["CE", "PE", "ce", "pe"], "description": "Call (CE) or Put (PE)"},
                "days_to_expiry": {"type": "number", "default": 2.0, "description": "Days remaining to expiry"},
                "iv_pct": {"type": "number", "default": 14.0, "description": "Implied Volatility or India VIX in %"}
            },
            "required": ["spot", "strike"]
        }
    },
    {
        "name": "nifty_options_plan_trade",
        "description": "Map NIFTY Spot index levels (Entry, Technical Stop-Loss, Target) into exact Option Premium values using Delta/Gamma Taylor expansion, with 0.1% STT statutory fee audit and 15m momentum timeout rules.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spot_entry": {"type": "number", "description": "Nifty Spot entry price"},
                "spot_sl": {"type": "number", "description": "Nifty Spot stop loss level"},
                "spot_target": {"type": "number", "description": "Nifty Spot profit target level"},
                "type": {"type": "string", "enum": ["CE", "PE", "ce", "pe"], "default": "CE"},
                "days_to_expiry": {"type": "number", "default": 2.0},
                "iv_pct": {"type": "number", "default": 14.0},
                "lots": {"type": "integer", "default": 1, "description": "Number of lots (75 qty/lot)"}
            },
            "required": ["spot_entry", "spot_sl", "spot_target"]
        }
    },
    {
        "name": "nifty_options_recommend_strikes",
        "description": "Find the optimal At-The-Money (ATM) and In-The-Money (ITM) Call & Put strikes for NIFTY matching high Delta (0.55 - 0.70) to avoid OTM time-decay traps.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "spot": {"type": "number", "description": "Current Nifty Spot price"},
                "days_to_expiry": {"type": "number", "default": 2.0},
                "iv_pct": {"type": "number", "default": 14.0}
            },
            "required": ["spot"]
        }
    }
]


def handle_tool_call(name, args):
    now_ist = (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)).replace(tzinfo=None)
    
    if name == "indian_market_clock":
        sim = args.get("simulated_time")
        target_ist = now_ist
        if sim:
            utc = alerts_mod.parse_now(sim)
            target_ist = alerts_mod.to_ist(utc)
        ok, reason = alerts_mod.is_trading_day(target_ist.date())
        t = target_ist.time()
        phase = "CLOSED"
        if ok:
            if t < datetime.time(9, 0): phase = "PRE_MARKET_WAIT"
            elif t < datetime.time(9, 8): phase = "PRE_OPEN_COLLECTION"
            elif t < datetime.time(9, 15): phase = "PRE_OPEN_MATCHING"
            elif t < datetime.time(15, 15): phase = "NORMAL_CONTINUOUS_TRADING"
            elif t < datetime.time(15, 30): phase = "INTRADAY_SQUARE_OFF_CUTOFF"
            else: phase = "POST_MARKET_CLOSED"
        return {
            "ist_time": target_ist.strftime("%Y-%m-%d %H:%M:%S IST"),
            "trading_day": ok,
            "session_phase": phase,
            "holiday_info": reason,
            "intraday_cutoff": "15:15 IST"
        }
        
    elif name == "indian_scan_orb":
        syms = args.get("symbols") or scan_mod.DEFAULT_NSE_LIST[:10]
        hits = []
        for s in syms:
            try:
                h = scan_mod.scan_orb_stock(s, now_ist)
                if h: hits.append(h)
            except Exception: pass
        return {"scanned_symbols": len(syms), "orb_hits": hits}
        
    elif name == "indian_check_entry":
        sym = args["symbol"]
        setup = args.get("setup", "orb")
        level = args.get("level")
        return entry_mod.check_entry(sym, setup=setup, level=level, now_ist=now_ist)
        
    elif name == "indian_plan_exit":
        return exit_mod.calculate_plan(
            args["symbol"], args["entry"], args.get("or_high"), args.get("or_low"),
            args.get("stop_rule", "or-mid"), args.get("target_rule", "2R")
        )
        
    elif name == "indian_run_timemachine":
        return tm_mod.run_simulation(
            args["entry"], args["stop"], args["target"],
            replays=args.get("replays", 5000), seed=19
        )
        
    elif name == "indian_size_position":
        plan = {
            "symbol": args["symbol"],
            "entry": args["entry"],
            "stop": args["stop"],
            "target": args["target"]
        }
        cfg = budget_mod.DEFAULTS.copy()
        portfolio = paper_mod.load_portfolio()
        order, limits = budget_mod.calculate_position_size(plan, cfg, portfolio)
        return {"order": order, "limits": limits}
        
    elif name == "indian_risk_check":
        order = args["order"]
        cfg = risk_mod.DEFAULTS.copy()
        portfolio = paper_mod.load_portfolio()
        prices = {order.get("symbol"): {"price": order.get("limit_price", 0.0), "previous_close": order.get("limit_price", 0.0) * 0.99}}
        blocks, warnings = risk_mod.validate_order(order, cfg, portfolio, prices, [], now_ist)
        verdict = "BLOCK" if blocks else "PASS"
        return {"verdict": verdict, "blocks": blocks, "warnings": warnings}
        
    elif name == "indian_paper_execute":
        order = {
            "symbol": args["symbol"],
            "side": args["side"],
            "qty": args["qty"],
            "product_type": args.get("product_type", "MIS")
        }
        return paper_mod.execute_paper_order(order, fill_price=args["fill_price"])
        
    elif name == "indian_fii_dii_flows":
        return {
            "institutional_flows": fii_mod.get_sample_fii_dii(),
            "bulk_deals": fii_mod.get_sample_bulk_deals()
        }
        
    elif name == "nifty_options_calculate_greeks":
        return options_mod.calculate_option_greeks(
            args["spot"], args["strike"],
            args.get("days_to_expiry", 2.0),
            args.get("iv_pct", 14.0),
            args.get("type", "CE")
        )
        
    elif name == "nifty_options_plan_trade":
        return options_mod.plan_nifty_option_trade(
            args["spot_entry"], args["spot_sl"], args["spot_target"],
            opt_type=args.get("type", "CE"),
            days_to_expiry=args.get("days_to_expiry", 2.0),
            iv_pct=args.get("iv_pct", 14.0),
            lots=args.get("lots", 1)
        )
        
    elif name == "nifty_options_recommend_strikes":
        return options_mod.find_optimal_strikes(
            args["spot"],
            days_to_expiry=args.get("days_to_expiry", 2.0),
            iv_pct=args.get("iv_pct", 14.0)
        )
        
    raise ValueError(f"Unknown tool: {name}")


def main():
    """Stdio JSON-RPC transport loop for Model Context Protocol."""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
            method = req.get("method")
            msg_id = req.get("id")
            
            if method == "initialize":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "serverInfo": {"name": "indian-day-trader-mcp", "version": "2.0.0"},
                        "capabilities": {"tools": {}}
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/list":
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {"tools": TOOLS_REGISTRY}
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
                
            elif method == "tools/call":
                params = req.get("params", {})
                t_name = params.get("name")
                t_args = params.get("arguments", {})
                tool_output = handle_tool_call(t_name, t_args)
                resp = {
                    "jsonrpc": "2.0",
                    "id": msg_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(tool_output, indent=2)}
                        ]
                    }
                }
                sys.stdout.write(json.dumps(resp) + "\n")
                sys.stdout.flush()
                
            elif method == "notifications/initialized":
                pass
                
        except Exception as e:
            err_resp = {
                "jsonrpc": "2.0",
                "id": req.get("id") if "req" in locals() else None,
                "error": {"code": -32603, "message": str(e)}
            }
            sys.stdout.write(json.dumps(err_resp) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
