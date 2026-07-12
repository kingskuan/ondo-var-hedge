# ondo-var-hedge

Delta-neutral hedge / funding-arbitrage monitor for **Ondo Perps** ↔ **Variational Omni**.

## Why
Farm rewards + points on two RWA perp venues at once by holding offsetting
positions (Long XAU@Ondo + Short XAU@Variational) so net market exposure ≈ 0,
while capturing the cross-venue funding-rate spread.

## Hard constraints (verified 2026-07-12)
- **Variational trading API is NOT public.** Only read-only `/metadata/stats`
  exists. Order placement is client wallet-signed + sequencer, no programmatic
  REST. → Var side must be opened MANUALLY; this bot only *monitors* it.
- **Ondo Perps** has a full public REST trading API (HMAC-SHA256). Bot can
  automate the Ondo leg once hedging params are approved.

## What this repo does NOW
Read-only monitor (no money moves):
- Pulls Variational `/metadata/stats` (funding, spread_bps, OI per listing)
- Pulls Ondo `/v1/perps/funding_rates` + `/v1/perps/contracts`
- Computes real delta-neutral cost: Ondo fees + Var spread + funding spread
- Estimates payback period and flags mark-price divergence risk
- (planned) pushes alerts to Telegram

## Layout
```
ondo_var_hedge/
  var_client.py      # read-only Variational stats
  ondo_client.py     # Ondo REST (HMAC) — monitor-only for now
  hedge_metrics.py   # cost / payback / divergence math
  monitor.py         # CLI entry, prints report
  config.py          # symbols, capital assumptions
```

## Run (local)
```
pip install -r requirements.txt
python -m ondo_var_hedge.monitor
```

## Status
- [x] Var read-only client
- [x] Ondo funding/contracts client
- [x] hedge cost math
- [ ] Telegram notifier
- [ ] Ondo auto-leg (BLOCKED on hedging-param approval)
