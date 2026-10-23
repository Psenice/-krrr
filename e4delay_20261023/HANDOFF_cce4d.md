# HANDOFF cce4d — 2026-10-23 (cloud Claude Code, E4 delayed entry)

**Verdict: NOT-ESTABLISHED (C2221).** The rule: if the notice pump is already ≥ +20 % at E4's T+1h, short after a ⅓
give-back instead. Paired against E4 T+1h on 40 gated events ccB never used: **+215 bp [−218, +831]**, ex-best −48,
trim-5 −202, ex-liquidation −48. Fee basis: Binance 20 bp RT + funding, unhedged. 1.5 fires/month. Backtest only.
- 25 of 40 pumps had already given back ⅓ by T+1h, so both entries are the same bar. The whole gain is one avoided
  E4 liquidation (LPT 2025-05, +10,447).
- Random-delay placebo: the real result is at the 87th percentile (p90 +241). The give-back timing is no better
  than a random wait.
- ccB's lead reproduces on the unseen slice only in ccB's after-the-fact form: +808 [+254, +1,447] n 56 (C2222). That
  form picks events by a pump that comes after E4 has already shorted, so it is a selection artifact.
- E4 T+1h itself holds on the unseen slice: +395 [−174, +939] n 88 floored; placebo excess +903 [+295, +1,509].

Slice: A = 40 E4 HL notices before 2025 (Binance proxy) + B = 60 Korean notices 2025–26 on Binance-only coins →
88 scored (9 no Binance perp, 3 censored). PREREG 6748e406…, AMENDMENTS 636436a6… (blind Opus review applied
before scoring), freeze commit 18a33a0.

Open / blockers: (1) ledger rows C2220–C2226 are in LEDGER_ROWS_cce4d_PENDING.csv; they need appending to
CLASSIC_LEDGER.csv on the PC (C2227–C2239 unused). (2) No HL bars for the 2024 slice, so Binance is the proxy.
(3) Generic tickers not hand-checked. (4) Optional: an E4 tail rule (liquidation guard), as its own PREREG.
Folder: Drive trading_cloud_2026-10-23/e4delay_20261023; git branch claude/e4-delayed-entry-korean-7rarmm.
