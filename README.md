# Polymarket Fair Value Model

Polymarket Fair Value Model is a quantitative finance project built to analyze prediction markets, mainly on Polymarket. The goal is simple: estimate what the “fair” probability of a price-based event should be, and compare it to the probability implied by the market price.

For example:

> *Will Bitcoin be above $100,000 on December 31?*

Instead of guessing, the model simulates thousands of possible future price paths using Monte Carlo methods based on Geometric Brownian Motion (GBM). From those simulations, it derives an estimated probability of the event happening and checks whether the market is overpricing or underpricing the outcome.

---

## What It Does

* Pulls live crypto price data from exchanges
* Fetches active event data from Polymarket
* Runs 5,000+ Monte Carlo simulations per event
* Estimates the probability of the target price condition being met
* Compares model probability vs. market-implied probability
* Flags potential mispricings
* Visualizes simulated price paths and outcome distributions

The dashboard is built in Streamlit and designed to make the analysis clear and fast to interpret.

---

## How It Works 

1. **Data Collection**
   Current spot prices and historical volatility are retrieved from crypto exchanges. Market odds are pulled from Polymarket.

2. **Modeling Assumption**
   Price dynamics are modeled using Geometric Brownian Motion:

   [
   dS_t = \mu S_t dt + \sigma S_t dW_t
   ]

   where volatility is estimated from historical data.

3. **Monte Carlo Simulation**
   Thousands of price paths are simulated up to the event expiry date.

4. **Probability Estimation**
   The percentage of simulated paths that satisfy the event condition becomes the model’s estimated probability.

5. **Arbitrage Logic**
   The model compares:

   * Market-implied probability (from token price)
   * Model-estimated probability

   Significant differences are highlighted as potential opportunities.

---

## How to Run

### Requirements

* Python 3.8+
* pip

### Installation

Clone the repository and install dependencies:

```bash
git clone <url>
cd arbitrage_pro
pip install -r requirements.txt
```

### Start the App

```bash
streamlit run app.py
```

The dashboard will open locally at:

```
http://localhost:8501
```

---

## Tech Stack

* Streamlit (dashboard framework)
* Python (core logic and simulation engine)
* Plotly (visualization of simulated paths)
* CCXT (crypto exchange data)
* Requests (Polymarket API integration)

---

## Disclaimer

This project is for educational and research purposes only. Prediction markets and crypto markets are highly volatile and risky. The model relies on GBM assumptions and historical volatility, which may not reflect real future dynamics. Use at your own risk.
