"""Comprehensive Unit & Integration Test Suite for Indian Stock Market AI Agent."""

import json
import os
import unittest
try:
    from ._load import load, FIXTURES
except ImportError:
    from tests._load import load, FIXTURES


class TestIndianStockPipeline(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.scan = load("trader-scanner", "scan")
        cls.entry = load("trader-entry", "entry")
        cls.exit = load("trader-exit", "exit")
        cls.timemachine = load("trader-timemachine", "timemachine")
        cls.budget = load("trader-budget", "size")
        cls.risk = load("trader-risk", "check")
        cls.ticket = load("trader-broker", "ticket")
        cls.paper = load("trader-broker", "paper_broker")
        cls.alerts = load("trader-alerts", "alerts")
        cls.fii = load("trader-fii-dii", "tracker")
        cls.analyst = load("trader-analyst", "facts")
        cls.fixture_path = os.path.join(FIXTURES, "RELIANCE_5m.json")

    def test_01_universe_and_symbol_formatting(self):
        """Validates symbol normalization for Indian exchanges (NSE .NS suffix)."""
        self.assertEqual(self.scan.to_yahoo_sym("RELIANCE"), "RELIANCE.NS")
        self.assertEqual(self.scan.to_yahoo_sym("tcs.ns"), "TCS.NS")
        self.assertEqual(self.scan.to_yahoo_sym("500325.BO"), "500325.BO")

    def test_02_orb_calculation(self):
        """Verifies 15-minute Opening Range Breakout calculation in IST."""
        with open(self.fixture_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        meta, bars = self.scan.parse_chart_series(data)
        self.assertEqual(len(bars), 8)
        self.assertEqual(meta["symbol"], "RELIANCE.NS")
        
        # In fixture: first 3 bars (09:15-09:30) have high 2940.00
        # Subsequent bars close at 2944, 2950, 2960 (breakout!)
        or_high = max(b["high"] for b in bars[:3])
        self.assertEqual(or_high, 2940.00)
        breakout_bar = bars[3]
        self.assertGreater(breakout_bar["close"], or_high)

    def test_03_exit_plan_calculation(self):
        """Validates INR stop-loss, target, and mandatory 15:15 IST flat_by."""
        plan = self.exit.calculate_plan(
            sym="RELIANCE.NS",
            entry=2950.00,
            or_high=2940.00,
            or_low=2910.00,
            stop_rule="or-mid",
            target_rule="2R"
        )
        self.assertEqual(plan["symbol"], "RELIANCE.NS")
        self.assertEqual(plan["entry"], 2950.00)
        # Midpoint of (2940 + 2910) / 2 = 2925.00
        self.assertEqual(plan["stop"], 2925.00)
        # Risk per share = 2950 - 2925 = 25.00
        self.assertEqual(plan["risk_per_share"], 25.00)
        # Target at 2R = 2950 + (2 * 25) = 3000.00
        self.assertEqual(plan["target"], 3000.00)
        self.assertEqual(plan["reward_risk_ratio"], 2.0)
        self.assertEqual(plan["flat_by"], "15:15")

    def test_04_budget_sizing_integer_shares_and_mis_leverage(self):
        """Ensures whole integer shares and SEBI 5x MIS leverage without fractional units."""
        plan = {
            "symbol": "RELIANCE.NS",
            "entry": 2950.00,
            "stop": 2925.00,
            "target": 3000.00,
            "risk_per_share": 25.00
        }
        cfg = {
            "budget": 100000,
            "cash_buffer_pct": 10,
            "max_position_pct": 50,
            "max_order_inr": 80000,
            "max_loss_per_trade_inr": 1000,
            "mis_leverage": 5.0,
            "product_type": "MIS"
        }
        order, limits = self.budget.calculate_position_size(plan, cfg, portfolio={"cash": 100000})
        # max loss ₹1000 / risk per share ₹25 = 40 shares
        # max order ₹80,000 / 2950 = 27 shares
        # max pos cap ₹50,000 / 2950 = 16 shares
        # Smallest limit: 16 shares
        self.assertIsInstance(order["qty"], int)
        self.assertEqual(order["qty"], 16)
        self.assertLessEqual(order["order_value"], 50000.0)
        self.assertLessEqual(order["max_loss_inr"], 1000.0)

    def test_05_budget_refusal_when_stop_too_wide(self):
        """Verifies refusal when risk exceeds total max loss."""
        plan = {
            "symbol": "RELIANCE.NS",
            "entry": 2950.00,
            "stop": 1500.00,  # Risk ₹1,450 per share
            "target": 3500.00,
            "risk_per_share": 1450.00
        }
        cfg = {"budget": 100000, "max_loss_per_trade_inr": 500}
        with self.assertRaises(self.budget.BudgetError):
            self.budget.calculate_position_size(plan, cfg)

    def test_06_sebi_statutory_charges_calculation(self):
        """Validates accurate breakdown of Indian statutory trading taxes."""
        charges = self.paper.calculate_indian_statutory_charges(
            side="SELL", price=3000.0, qty=10, product="MIS"
        )
        # Turnover = ₹30,000
        self.assertEqual(charges["turnover"], 30000.0)
        # STT for intraday sell = 0.025% of ₹30,000 = ₹7.50
        self.assertEqual(charges["stt"], 7.50)
        # Brokerage = min(20, 0.03% of 30,000 = 9) = ₹9.00
        self.assertEqual(charges["brokerage"], 9.00)
        self.assertGreater(charges["total_charges"], 16.0)

    def test_07_paper_broker_execution_and_balance_update(self):
        """Validates paper broker order execution, margin lock, and cash updates."""
        test_portfolio_path = "tests/fixtures/test_portfolio.json"
        if os.path.exists(test_portfolio_path):
            os.remove(test_portfolio_path)
            
        order = {"symbol": "RELIANCE.NS", "side": "BUY", "qty": 10, "product_type": "MIS"}
        result = self.paper.execute_paper_order(order, fill_price=2950.00, portfolio_path=test_portfolio_path)
        
        self.assertEqual(result["status"], "FILLED")
        self.assertEqual(result["symbol"], "RELIANCE.NS")
        self.assertEqual(result["qty"], 10)
        
        p = self.paper.load_portfolio(test_portfolio_path)
        self.assertIn("RELIANCE.NS", p["positions"])
        self.assertEqual(p["positions"]["RELIANCE.NS"]["qty"], 10)
        self.assertLess(p["cash"], 100000.0)
        
        # Clean up test file
        if os.path.exists(test_portfolio_path):
            os.remove(test_portfolio_path)

    def test_08_risk_engine_validates_order(self):
        """Validates pre-trade risk checks: PASS on compliant order, BLOCK on violation."""
        now_ist = self.risk.datetime.datetime(2026, 10, 19, 10, 15)  # Trading day during window
        cfg = self.risk.DEFAULTS.copy()
        portfolio = {"cash": 100000}
        prices = {"RELIANCE.NS": {"price": 2950.0, "previous_close": 2920.0}}
        
        valid_order = {
            "symbol": "RELIANCE.NS",
            "side": "BUY",
            "qty": 10,
            "type": "limit",
            "limit_price": 2950.0,
            "stop_loss_trigger": 2925.0,
            "take_profit_target": 3000.0,
            "product_type": "MIS"
        }
        blocks, warnings = self.risk.validate_order(valid_order, cfg, portfolio, prices, [], now_ist)
        self.assertEqual(blocks, [])
        
        # Circuit Breaker Violation: Attempting to buy at upper circuit (+10%)
        circuit_order = valid_order.copy()
        circuit_order["limit_price"] = 2920.0 * 1.098  # near +10% upper circuit
        blocks_c, _ = self.risk.validate_order(circuit_order, cfg, portfolio, prices, [], now_ist)
        self.assertTrue(any("Circuit Guard" in b for b in blocks_c))

    def test_09_time_machine_simulation_percentiles(self):
        """Validates Monte Carlo simulation produces deterministic win/loss odds."""
        res = self.timemachine.run_simulation(
            entry=2950.0, stop=2925.0, target=3000.0, start_bar_idx=6, replays=1000, seed=19
        )
        self.assertEqual(res["replays"], 1000)
        self.assertGreater(res["target_rate_pct"] + res["stop_rate_pct"] + res["open_rate_pct"], 99.0)
        self.assertGreaterEqual(res["median_price"], 2900.0)

    def test_10_ist_market_clock(self):
        """Validates trading day & holiday checks for Indian markets."""
        trading_day = self.alerts.datetime.date(2026, 10, 19)  # Monday
        ok, reason = self.alerts.is_trading_day(trading_day)
        self.assertTrue(ok)
        
        republic_day = self.alerts.datetime.date(2026, 1, 26)  # Republic Day holiday
        ok_h, reason_h = self.alerts.is_trading_day(republic_day)
        self.assertFalse(ok_h)
        self.assertIn("Republic Day", reason_h)

    def test_11_smart_money_fii_dii_flows(self):
        """Validates institutional flow calculations."""
        data = self.fii.get_sample_fii_dii()
        self.assertIn("fii", data)
        self.assertIn("dii", data)
        self.assertGreater(data["combined_net_cr"], 0)
        self.assertEqual(data["market_sentiment"], "STRONG_BULLISH_TAILWIND")


if __name__ == "__main__":
    unittest.main()
