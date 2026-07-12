"""Hedging assumptions — edit freely, no money moves from this file."""
from __future__ import annotations

# Symbols to track (Variational tickers; Ondo uses SYMBOL-USD.P)
SYMBOLS = ["CRCL", "XAU", "XAG", "WTI", "NVDA", "TSLA"]

# Ondo fee schedule (from ritmex + user): maker 0.015%, taker 0.035%
ONDO_MAKER_FEE = 0.00015
ONDO_TAKER_FEE = 0.00035
# User referral discount 20% -> effective
ONDO_FEE_DISCOUNT = 0.80

# Example capital for payback math (USD). Split 50/50 across venues.
CAPITAL_PER_VENUE = 2500.0
LEVERAGE = 20.0

# Mark-price divergence risk threshold (fraction). If |mark_var - mark_ondo|
# / mark exceeds this, hedge is broken -> alert.
MARK_DIVERGENCE_ALERT = 0.01  # 1%

# Funding interval assumption (seconds) for annualization
FUNDING_INTERVAL_S = 28800  # 8h
