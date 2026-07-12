"""Read-only Variational Omni client.

IMPORTANT (verified 2026-07-12): Variational has NO public trading API.
Only GET /metadata/stats is available. This client is monitor-only.
"""
from __future__ import annotations

import requests

VAR_BASE_URL = "https://omni-client-api.prod.ap-northeast-1.variational.io"


def fetch_stats(base_url: str = VAR_BASE_URL, timeout: int = 20) -> dict:
    """Return raw Variational Omni /metadata/stats payload."""
    resp = requests.get(f"{base_url}/metadata/stats", timeout=timeout)
    resp.raise_for_status()
    return resp.json()


def listing_map(stats: dict) -> dict[str, dict]:
    """ticker -> {mark_price, funding_rate(frac), funding_interval_s, spread_bps, oi}"""
    out: dict[str, dict] = {}
    for l in stats.get("listings", []):
        oi = l.get("open_interest", {}) or {}
        long_oi = float(oi.get("long_open_interest", 0) or 0)
        short_oi = float(oi.get("short_open_interest", 0) or 0)
        out[l["ticker"]] = {
            "mark_price": float(l.get("mark_price", 0)),
            "funding_rate": float(l.get("funding_rate", 0)),  # decimal per interval
            "funding_interval_s": int(l.get("funding_interval_s", 0)),
            "spread_bps": float(l.get("base_spread_bps", 0)),
            "open_interest": long_oi + short_oi,
        }
    return out


def select(listings: dict[str, dict], symbols: list[str]) -> dict[str, dict]:
    return {s: listings[s] for s in symbols if s in listings}


if __name__ == "__main__":
    import json
    stats = fetch_stats()
    print("markets:", stats.get("num_markets"),
          "24h_vol_M:", round(float(stats["total_volume_24h"]) / 1e6, 1))
    print(json.dumps(select(listing_map(stats), ["CRCL", "XAU", "XAG", "WTI"]), indent=2))
