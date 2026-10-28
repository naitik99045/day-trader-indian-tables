# NIFTY 50 Options Trading & Greeks Knowledge Base
**Living Reference Document for AI Agents & Traders**

This document provides the mathematical foundations, empirical market rules, and quantitative models fed into the Indian Stock AI Agent for NIFTY 50 options trading.

---

## 1. Black-Scholes-Merton Options Model & The Greeks

European options on the NIFTY 50 index are modeled using the standard Black-Scholes-Merton (BSM) differential framework:

### Core Notation & Standard Parameters
* $S$ = Current NIFTY Spot Index price (e.g. 24,500)
* $K$ = Option Strike price (50-point intervals: 24450, 24500, 24550...)
* $r$ = Risk-free interest rate (RBI 91-day T-Bill rate $\approx 6.5\%$ or $0.065$)
* $\sigma$ = Implied Volatility (annualized, derived from India VIX, e.g. $14\% = 0.14$)
* $T$ = Time to expiry in years ($\text{Days to Expiry} / 365$)
* $N(x)$ = Cumulative standard normal distribution function:
  $$N(x) = \frac{1}{2} \left[1 + \text{erf}\left(\frac{x}{\sqrt{2}}\right)\right]$$
* $N'(x)$ = Standard normal probability density function (PDF):
  $$N'(x) = \frac{1}{\sqrt{2\pi}} e^{-\frac{x^2}{2}}$$

### Standard Intermediate Variables $d_1$ and $d_2$
$$d_1 = \frac{\ln\left(\frac{S}{K}\right) + \left(r + \frac{\sigma^2}{2}\right)T}{\sigma \sqrt{T}}$$

$$d_2 = d_1 - \sigma \sqrt{T} = \frac{\ln\left(\frac{S}{K}\right) + \left(r - \frac{\sigma^2}{2}\right)T}{\sigma \sqrt{T}}$$

---

## 2. Greeks Definitions & Formulas

### 1. Delta ($\Delta$) — Directional Sensitivity
Measures how much the option price moves for a ₹1 change in the underlying NIFTY index:
$$\Delta = \frac{\partial V}{\partial S}$$
* **Call Option (CE):** $\Delta_{\text{call}} = N(d_1)$ (Ranges from $0.0$ to $+1.0$)
* **Put Option (PE):** $\Delta_{\text{put}} = N(d_1) - 1$ (Ranges from $-1.0$ to $0.0$)
* *At-The-Money (ATM):* $\Delta \approx +0.50$ (Call), $\Delta \approx -0.50$ (Put).

### 2. Gamma ($\Gamma$) — Delta Acceleration
Measures the rate of change of Delta for a 1-point move in NIFTY ($\frac{\partial^2 V}{\partial S^2}$). Identical for Calls and Puts:
$$\Gamma = \frac{N'(d_1)}{S \sigma \sqrt{T}}$$
* **Impact:** Gamma increases as expiry approaches (0DTE/1DTE) and is highest At-The-Money. It causes winning options to gain delta rapidly ("Gamma blast").

### 3. Theta ($\Theta$) — Time Decay
Measures the loss in option value due to the passage of time ($\frac{\partial V}{\partial t}$):
* **Call Option (CE):**
  $$\Theta_{\text{call}} = -\frac{S \sigma N'(d_1)}{2\sqrt{T}} - r K e^{-rT} N(d_2)$$
* **Put Option (PE):**
  $$\Theta_{\text{put}} = -\frac{S \sigma N'(d_1)}{2\sqrt{T}} + r K e^{-rT} N(-d_2)$$
* **Daily Decay:** $\Theta_{\text{daily}} = \Theta / 365$
* **Hourly Decay (Indian Trading Hours):**
  $$\Theta_{\text{hourly}} = \frac{\Theta_{\text{daily}}}{6.25 \text{ hours}}$$
  *(NIFTY trades from 09:15 to 15:30 IST = 6.25 hours per day).*

### 4. Vega ($\mathcal{V}$) — Volatility Sensitivity
Measures how much the option price changes for a 1% change in Implied Volatility / India VIX:
$$\mathcal{V} = S \sqrt{T} N'(d_1) \times 0.01$$
* High India VIX increases both CE and PE premiums; a sudden IV crash after an event crushes long options.

### 5. Omega ($\Omega$) — Option Elasticity & Effective Leverage
Measures the **percentage change** in option price relative to a $1\%$ change in the NIFTY spot index (also known as Gearing / Lambda):
$$\Omega = \frac{\% \Delta \text{Option}}{\% \Delta \text{Index}} = \frac{\Delta \times S}{V}$$
* **Example:** If NIFTY is 24,500, Call price is ₹105, and Delta is 0.51:
  $$\Omega = \frac{0.5158 \times 24500}{105.69} = 119.5\times \text{ Effective Leverage}$$
  A 1% move in Nifty creates a ~120% surge in the option premium!

### 6. Rho ($\rho$) — Interest Rate Sensitivity
* **Call:** $\rho_{\text{call}} = K T e^{-rT} N(d_2) \times 0.01$
* **Put:** $\rho_{\text{put}} = -K T e^{-rT} N(-d_2) \times 0.01$

---

## 3. Stop-Loss & Target Setting Methods for Nifty Options

Setting arbitrary stop-losses on an option chart often leads to getting stopped out by fake spikes or theta chop. The bot implements three mathematical methods:

### Method 1: Spot-Derived Taylor Delta/Gamma Mapping (Primary Engine)
Instead of watching the option chart, the trader places the technical Stop-Loss and Target on the **NIFTY Spot Index Chart** (e.g. 15m ORB high/low or swing low). The bot projects this into exact option premiums using a second-order Taylor expansion:

$$\Delta \text{Option Premium} \approx (\Delta \times \Delta S) + \frac{1}{2} \Gamma (\Delta S)^2$$

* **Target Premium Calculation:**
  $$\text{Target Premium} = \text{Entry Premium} + (\text{Spot Target} - \text{Spot Entry}) \times \Delta + \frac{1}{2} \Gamma (\text{Spot Target} - \text{Spot Entry})^2$$
* **Stop-Loss Premium Calculation:**
  $$\text{Stop-Loss Premium} = \text{Entry Premium} - (\text{Spot Entry} - \text{Spot SL}) \times \Delta$$
  *(Note: For SL, Gamma works slightly against you as delta decreases, keeping your exit conservative).*

### Method 2: Hourly Theta Decay Momentum Timeout (15-Minute Rule)
* **The Rule:** An intraday option buy is entered ONLY for explosive momentum.
* If NIFTY Spot consolidates sideways for **more than 15–20 minutes (3 to 4 consecutive 5-minute candles)**, the hourly theta decay begins eating profits.
* **Bot Action:** Signals a **Momentum Timeout**—instructing the trader to trail the stop-loss to breakeven or exit immediately.

### Method 3: Net Realized Profitability after SEBI Statutory Taxes
An option trade is invalid if the gross profit does not exceed statutory friction.
* **Brokerage:** Flat ₹20 buy + ₹20 sell = ₹40 per roundtrip.
* **STT (Securities Transaction Tax):** **0.1% on the sell turnover** of the option premium (effective October 1, 2024).
* **Exchange Turnover Charge:** 0.05% of turnover.
* **GST:** 18% on (Brokerage + Exchange fees).
* **Bot Action:** Subtracts all statutory fees from gross profit before calculating the Net Reward-to-Risk ratio. Refuses orders with Net R:R < 1.5.

---

## 4. Retail Reddit & Quant Trading Insights (r/IndianStreetBets)

1. **Never Buy OTM (Delta < 0.35):**
   * Buying cheap ₹15-₹30 strikes is an expected-value trap. Theta decay and spread slippage consume over 85% of these positions.
2. **The Sweet Spot: 1-Strike In-The-Money (ITM) or Strict ATM:**
   * Delta between **0.55 and 0.70**.
   * Provides rapid 1:1 index tracking, tightest bid-ask spreads, and lower percentage theta erosion.
3. **Open Interest (OI) & Put-Call Ratio (PCR) Filter:**
   * PCR > 1.2: Heavy institutional Put writing indicates strong floor support (Confirms CE buying).
   * PCR < 0.8: Heavy Call writing indicates strong overhead resistance (Confirms PE buying).
   * Never buy a Call option directly beneath the largest Call Open Interest strike wall.
4. **India VIX Regimes:**
   * **VIX < 12.0:** Low volatility, compressed premiums. Option buying is difficult due to slow movement.
   * **VIX 13.0 - 18.0:** Ideal regime for breakout momentum scalping.
   * **VIX > 22.0:** High IV; wide spreads, option premiums are expensive and vulnerable to sharp IV crush.
