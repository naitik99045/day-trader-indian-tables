---
name: trader-options
description: >-
  NIFTY 50 Options Greeks & Risk Engine. Calculates Black-Scholes Greeks (Delta, Gamma, Theta,
  Vega, Omega elasticity, Rho), maps Nifty Spot chart breakouts to exact option premium stop-loss
  and targets using Taylor expansion, selects high-delta (0.55-0.70) ATM/ITM strikes, enforces
  the 15-minute momentum timeout, and audits net profitability after SEBI statutory costs (0.1% STT).
argument-hint: "[calc | plan | recommend] [--spot PRICE] [--spot-entry ENTRY] [--type CE|PE]"
---

# trader-options (NIFTY 50 Options Engine)

Quantitative options trading engine for NIFTY 50 index options on NSE.

```bash
# Calculate Black-Scholes Greeks for any strike
python trader-options/greeks.py calc --spot 24500 --strike 24500 --type CE --days 2 --iv 14.0

# Generate full trade plan mapping Spot chart levels to Option Premium SL & Target
python trader-options/greeks.py plan --spot-entry 24500 --spot-sl 24460 --spot-target 24580 --type CE --lots 1

# Recommend optimal ATM / 1-strike ITM contracts (Delta 0.55 - 0.70)
python trader-options/greeks.py recommend --spot 24500 --days 2 --iv 14.0
```

## The Quant Edge: Why This Avoids Retail Option Traps
1. **Delta Mapping with Gamma Acceleration:**
   $$\Delta \text{Option} \approx (\Delta \times \Delta \text{Spot}) + \frac{1}{2} \Gamma (\Delta \text{Spot})^2$$
2. **Eliminates OTM Traps:** Selects Delta 0.55 – 0.70 (ATM/ITM) strikes with high liquidity and tight bid-ask spreads.
3. **Theta Hourly Decay Guard:** Displays exact rupee time decay per hour. If Nifty consolidates for >15 minutes, tightens SL to breakeven.
4. **SEBI F&O Statutory Cost Accounting:** Deducts 0.1% STT on option premium sale, exchange fees, GST, and ₹20 brokerage.
