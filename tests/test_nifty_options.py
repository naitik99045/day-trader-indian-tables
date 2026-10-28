"""Unit Tests for NIFTY 50 Options Greeks & Quantitative Risk Engine."""

import math
import unittest
try:
    from ._load import load
except ImportError:
    from tests._load import load


class TestNiftyOptionsGreeks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.greeks = load("trader-options", "greeks")

    def test_01_normal_distribution(self):
        """Validates Standard Normal CDF and PDF calculations."""
        # N(0) = 0.5
        self.assertAlmostEqual(self.greeks.standard_normal_cdf(0.0), 0.5, places=5)
        # N(1.96) ≈ 0.9750
        self.assertAlmostEqual(self.greeks.standard_normal_cdf(1.96), 0.9750, places=3)
        # N'(0) ≈ 0.39894
        self.assertAlmostEqual(self.greeks.standard_normal_pdf(0.0), 0.39894, places=4)

    def test_02_black_scholes_atm_call_greeks(self):
        """Validates Black-Scholes Greeks for an At-The-Money Call option."""
        spot = 24500.0
        strike = 24500.0
        res = self.greeks.calculate_option_greeks(spot, strike, days_to_expiry=2.0, iv_pct=14.0, opt_type="CE")
        
        # Theoretical price should be positive
        self.assertGreater(res["theoretical_price"], 50.0)
        # ATM Delta is roughly around ~0.50 - 0.53
        self.assertGreater(res["delta"], 0.48)
        self.assertLess(res["delta"], 0.55)
        # Gamma is strictly positive
        self.assertGreater(res["gamma"], 0.0)
        # Theta is negative (decay)
        self.assertLess(res["theta_daily"], 0.0)
        self.assertLess(res["theta_hourly"], 0.0)
        # Vega is positive
        self.assertGreater(res["vega"], 0.0)
        # Omega (elasticity) > 50x
        self.assertGreater(res["omega_elasticity"], 50.0)

    def test_03_black_scholes_atm_put_greeks(self):
        """Validates Black-Scholes Greeks for an At-The-Money Put option."""
        spot = 24500.0
        strike = 24500.0
        res = self.greeks.calculate_option_greeks(spot, strike, days_to_expiry=2.0, iv_pct=14.0, opt_type="PE")
        
        self.assertGreater(res["theoretical_price"], 50.0)
        # ATM Put Delta is negative around -0.45 to -0.52
        self.assertLess(res["delta"], -0.45)
        self.assertGreater(res["delta"], -0.55)
        self.assertGreater(res["gamma"], 0.0)
        self.assertLess(res["theta_daily"], 0.0)

    def test_04_put_call_parity(self):
        """Verifies Put-Call Parity: C - P = S - K * exp(-r*T)."""
        spot = 24500.0
        strike = 24500.0
        days = 5.0
        iv = 15.0
        r = 0.065
        t_years = days / 365.0
        
        call_res = self.greeks.calculate_option_greeks(spot, strike, days, iv, "CE", r=r)
        put_res = self.greeks.calculate_option_greeks(spot, strike, days, iv, "PE", r=r)
        
        lhs = call_res["theoretical_price"] - put_res["theoretical_price"]
        rhs = spot - strike * math.exp(-r * t_years)
        self.assertAlmostEqual(lhs, rhs, delta=0.5)

    def test_05_spot_to_option_trade_plan(self):
        """Validates Taylor series mapping of Spot entry/SL/Target to Option Premium."""
        plan = self.greeks.plan_nifty_option_trade(
            spot_entry=24500.0,
            spot_sl=24460.0,      # 40 pt spot risk
            spot_target=24580.0,  # 80 pt spot target (1:2 Spot R:R)
            opt_type="CE",
            days_to_expiry=2.0,
            iv_pct=14.0,
            lots=1
        )
        
        # 1-strike ITM Call should be 24450 CE
        self.assertEqual(plan["strike"], 24450.0)
        self.assertEqual(plan["option_type"], "CE")
        self.assertEqual(plan["position_sizing"]["lot_size"], 75)
        
        # Check premium SL is strictly lower than entry
        entry_p = plan["premium_levels"]["entry_premium"]
        sl_p = plan["premium_levels"]["stop_loss_premium"]
        tp_p = plan["premium_levels"]["target_premium"]
        self.assertLess(sl_p, entry_p)
        self.assertGreater(tp_p, entry_p)
        
        # Net profit after statutory fees must be positive
        self.assertGreater(plan["position_sizing"]["net_profit_inr"], 0.0)
        self.assertGreater(plan["position_sizing"]["statutory_fees_inr"], 30.0)
        self.assertGreater(plan["position_sizing"]["net_reward_risk_ratio"], 1.5)

    def test_06_optimal_strike_recommendations(self):
        """Validates strike selector eliminates low-delta OTM lottery traps."""
        rec = self.greeks.find_optimal_strikes(spot=24500.0, days_to_expiry=2.0, iv_pct=14.0)
        ce = rec["recommended_ce"]
        pe = rec["recommended_pe"]
        
        # Delta should be >= 0.50
        self.assertGreaterEqual(ce["delta"], 0.50)
        self.assertIn(ce["moneyness"], ("ATM", "ITM"))
        
        self.assertLessEqual(pe["delta"], -0.50)
        self.assertIn(pe["moneyness"], ("ATM", "ITM"))


if __name__ == "__main__":
    unittest.main()
