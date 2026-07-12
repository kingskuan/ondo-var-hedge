"""Delta-neutral hedge monitor — Railway service.

Serves an HTTP endpoint (Railway requires a listening web server) AND runs
the monitoring loop in the background. Read-only: no trades are placed.

Endpoints:
  GET /            -> latest monitor report (text)
  GET /health      -> "ok" (Railway healthcheck)
"""
from __future__ import annotations

import sys
import time
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from . import config
from .var_client import fetch_stats, listing_map
from .ondo_client import fetch_funding, fetch_contracts
from .hedge_metrics import build_report


# Shared latest report (updated by the background loop)
LATEST = {"text": "starting...", "ts": 0.0}
LATEST_LOCK = threading.Lock()
LOOP_INTERVAL_S = 900  # 15 min


def _ondo_mark(contracts, sym):
    for c in contracts:
        if c.get("symbol") == f"{sym}-USD.P":
            try:
                return float(c["markPrice"])
            except Exception:
                return None
    return None


def run_once() -> str:
    stats = fetch_stats()
    var_listings = listing_map(stats)
    contracts = fetch_contracts()
    notional = config.CAPITAL_PER_VENUE * config.LEVERAGE

    lines = []
    lines.append(
        f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] Variational markets: "
        f"{stats.get('num_markets')} | 24h vol "
        f"${float(stats['total_volume_24h'])/1e6:.0f}M"
    )
    lines.append(
        f"Notional/leg (${config.CAPITAL_PER_VENUE:.0f} x{config.LEVERAGE}x): "
        f"${notional:,.0f}\n"
    )

    rows = []
    for sym in config.SYMBOLS:
        v = var_listings.get(sym)
        if not v:
            lines.append(f"{sym:5} not listed on Variational — skip")
            continue
        try:
            of = fetch_funding(sym)
        except Exception as e:
            lines.append(f"{sym:5} Ondo funding ERR: {e}")
            continue
        of["mark_ondo"] = _ondo_mark(contracts, sym) or v["mark_price"]
        rows.append(build_report(sym, v, of, notional))

    hdr = f"{'SYM':5} {'Ondo8h':>9} {'Var8h':>9} {'net8h':>9} {'VarSpd':>7} {'RT$':>8} {'fund/rt':>8} {'payback':>8}  DIV"
    lines.append(hdr)
    lines.append("-" * len(hdr))
    for r in rows:
        lines.append(
            f"{r['symbol']:5} {r['ondo_funding_8h_%']:>9.4f} "
            f"{r['var_funding_8h_%']:>9.4f} {r['net_funding_8h_%']:>9.4f} "
            f"{r['var_spread_bps']:>7.2f} {r['cost_round_trip_usd']:>8.2f} "
            f"{r['funding_net_per_rt_usd']:>8.2f} {r['payback_round_trips']:>8} "
            f"{'⚠' if r['divergence_alert'] else ''}"
        )
    alerts = [r["symbol"] for r in rows if r["divergence_alert"]]
    if alerts:
        lines.append(f"\n⚠ MARK DIVERGENCE ALERT: {alerts}")
    return "\n".join(lines)


def loop():
    while True:
        try:
            text = run_once()
        except Exception as e:
            text = f"ERROR: {e}"
        with LATEST_LOCK:
            LATEST["text"] = text
            LATEST["ts"] = time.time()
        print(text, flush=True)
        time.sleep(LOOP_INTERVAL_S)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/health"):
            body = b"ok"
        else:
            with LATEST_LOCK:
                body = LATEST["text"].encode()
            if self.path != "/":
                body = (body.decode() + f"\n\n(path {self.path} not found, showing report)\n").encode()
        self.send_response(200)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def main() -> int:
    # start background monitor loop
    t = threading.Thread(target=loop, daemon=True)
    t.start()

    port = int(__import__("os").environ.get("PORT", "8080"))
    srv = ThreadingHTTPServer(("0.0.0.0", port), Handler)
    print(f"Listening on 0.0.0.0:{port}", flush=True)
    srv.serve_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
