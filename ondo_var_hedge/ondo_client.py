"""Ondo Perps read-only client (HMAC-SHA256, copied from ritmex-bot gateway).

Verified endpoints (public, no auth needed for market data):
  GET /v1/perps/contracts            -> all markets
  GET /v1/perps/funding_rates?market=XXXX-USD.P  -> current funding

Trading endpoints exist (/v1/perps/orders) but are NOT used yet — hedging
params must be approved before any order is placed.
"""
from __future__ import annotations

import hmac
import hashlib
import time
import requests

ONDO_BASE_URL = "https://api.ondoperps.xyz"


def _normalize_symbol(symbol: str) -> str:
    s = symbol.strip().upper().replace("/", "-")
    if s.endswith(".P"):
        return s
    if "-USD.P" in s:
        return s
    if s.endswith(("USDT", "USDC", "USD")) and len(s) > 3:
        return f"{s[:-3]}-USD.P"
    return f"{s}-USD.P"


def make_rest_signature(api_secret: str, timestamp: str, method: str,
                        request_path: str, body: str = "") -> str:
    message = f"{timestamp}{method.upper()}{request_path}{body}"
    return hmac.new(api_secret.encode(), message.encode(), hashlib.sha256).hexdigest()


def auth_headers(api_key_id: str, api_secret: str) -> dict:
    ts = str(int(time.time() * 1000))
    sig = make_rest_signature(api_secret, ts, "GET", "/v1/perps/funding_rates")
    return {"ONDO-KEY-ID": api_key_id, "ONDO-TIMESTAMP": ts, "ONDO-SIGN": sig}


def fetch_funding(market: str, base_url: str = ONDO_BASE_URL, timeout: int = 15) -> dict:
    """Public funding rate for a market, e.g. CRCL-USD.P."""
    m = _normalize_symbol(market)
    resp = requests.get(f"{base_url}/v1/perps/funding_rates",
                        params={"market": m}, timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Ondo funding error: {data}")
    r = data["result"]
    return {
        "market": r["market"],
        "rate": float(r["rate"]),          # decimal per interval
        "interval_ends": r.get("intervalEnds"),
    }


def fetch_contracts(base_url: str = ONDO_BASE_URL, timeout: int = 15) -> list[dict]:
    """Public market metadata (precision, tick size, etc.)."""
    resp = requests.get(f"{base_url}/v1/perps/contracts", timeout=timeout)
    resp.raise_for_status()
    data = resp.json()
    if not data.get("success"):
        raise RuntimeError(f"Ondo contracts error: {data}")
    return data["result"]


def contract_by_market(contracts: list[dict], market: str) -> dict | None:
    m = _normalize_symbol(market)
    for c in contracts:
        if c.get("market") == m:
            return c
    return None


if __name__ == "__main__":
    import json
    for sym in ["CRCL", "XAU", "XAG", "WTI"]:
        try:
            print(sym, fetch_funding(sym))
        except Exception as e:
            print(sym, "ERR", e)
