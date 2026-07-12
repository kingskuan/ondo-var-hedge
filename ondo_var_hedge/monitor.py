"""CLI: print a delta-neutral hedge monitor report (read-only).

Usage:
  python -m ondo_var_hedge.monitor            # single run
  python -m ondo_var_hedge.monitor --loop     # run every INTERVAL seconds (Railway)
"""
from __future__ import annotations

import sys
import time
from . import config
from .var_client import fetch_stats, listing_map, select
from .ondo_client import fetch_funding, fetch_contracts
from .hedge_metrics import build_report


LOOP_INTERVAL_S = 900  # 15 min


def run_once() -> int:
    stats = fetch_stats()
    var_listings = listing_map(stats)
    contracts = fetch_contracts()

    notional = config.CAPITAL_PER_VENUE * config.LEVERAGE

    print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Variational markets: "
          f"{stats.get('num_markets')} | 24h vol "
          f"${float(stats['total_volume_24h'])/1e6:.0f}M")
    print(f"Notional/leg (${config.CAPITAL_PER_VENUE:.0f} x{config.LEVERAGE}x): "
          f"${notional:,.0f}\n")

    rows = []
    for sym in config.SYMBOLS:
        v = var_listings.get(sym)
        if not v:
            print(f"{sym:5} not listed on Variational — skip")
            continue
        try:
            of = fetch_funding(sym)
        except Exception as e:
            print(f"{sym:5} Ondo funding ERR: {e}")
            continue
        of["mark_ondo"] = _ondo_mark(contracts, sym) or v["mark_price"]
        rows.append(build_report(sym, v, of, notional))

    _print_table(rows)
    alerts = [r for r in rows if r["divergence_alert"]]
    if alerts:
        print(f"\n⚠ MARK DIVERGENCE ALERT: {[r['symbol'] for r in alerts]}")
    return 0


def main() -> int:
    if "--loop" in sys.argv:
        print(f"Loop mode: every {LOOP_INTERVAL_S}s. Ctrl-C to stop.")
        while True:
            try:
                run_once()
            except Exception as e:
                print(f"ERROR: {e}")
            print(f"--- sleeping {LOOP_INTERVAL_S}s ---\n")
            time.sleep(LOOP_INTERVAL_S)
    return run_once()


def _ondo_mark(contracts, sym):
    for c in contracts:
        if c.get("market", "").startswith(sym):
            try:
                return float(c.get("lastPrice", 0))
            except (TypeError, ValueError):
                return None
    return None


def _print_table(rows: list[dict]) -> None:
    hdr = ["SYM", "OndoF%", "VarF%", "NetF%", "VarSpd", "CostRT$", "FundRT$", "PaybackRT"]
    widths = [5, 8, 8, 8, 8, 9, 9, 10]
    line = "  ".join(h.ljust(w) for h, w in zip(hdr, widths))
    print(line)
    print("-" * len(line))
    for r in rows:
        vals = [
            r["symbol"], f"{r['ondo_funding_8h_%']:.4f}", f"{r['var_funding_8h_%']:.4f}",
            f"{r['net_funding_8h_%']:.4f}", f"{r['var_spread_bps']:.2f}",
            f"{r['cost_round_trip_usd']:.2f}", f"{r['funding_net_per_rt_usd']:.2f}",
            str(r["payback_round_trips"]),
        ]
        print("  ".join(str(v).ljust(w) for v, w in zip(vals, widths)))


if __name__ == "__main__":
    sys.exit(main())
