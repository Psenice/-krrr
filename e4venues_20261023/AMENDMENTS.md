# AMENDMENTS — cce4v (e4venues_20261023)

PREREG sha256 bbf1424f…40b6 (frozen 11:39 Prague).

## A1 — after the blind review, BEFORE any scoring (~12:05 Prague)
Reviewer: independent Opus subagent, synthetic tests only (no raw data, no outputs). Verdict: §2 rule, funding sign, placebo, bootstrap, verdict thresholds and every venue's column mapping correct. 5 must-fix + 8 minor:
1. (must-fix, applied) `pick_union` could pick a top-priority row without excess over a lower-priority row with both → rank: N168 and excess > N168 > excess > priority.
2. (must-fix, applied) symbol check compared a `1000X` contract price with a plain one → price divided by 1000 for `1000X` symbols.
3. (must-fix, applied in part) Bybit rows: events scored elsewhere now get a `bybit_counts_only` row (C2206 count complete); "scored elsewhere" = a scored row with excess. **Not applied: Bybit placebo.** Bybit's only price source here is its daily trade dumps (event days 15–50 MB each); a placebo needs ~190 days per coin (> 10 GB for the 17 Bybit-only coins). Bybit-only events are therefore scored on price only: gross −ret168 and `net_nofund` = −ret168 − 32 bp (no funding, no placebo). They enter neither the NEW-layer excess verdict nor the pooled N168 (no funding) — reported in C2206 only. Deviation from PREREG §2 ("Bybit: excess only").
4. (must-fix, applied) Gate API pages started off the hour and lost one 1h bar per 1,900-h page → start aligned to the hour. All Gate 1h and funding caches deleted and re-fetched.
5. (must-fix, applied) a Gate funding REST error was cached as empty → now raises (never cached).
Minor applied: funding fetch error noted; `qv` sum with min_count (gatedata has no quote volume → NaN, not 0); Bybit timestamp unit check; NaN verdict → "NO DATA". Minor not applied: majority vote in the symbol check (no third-venue tie expected to matter; mismatches are listed); Bitget funding 100-page cap flag (8h/4h coins reach back ≥ 1.1 years); partial-funding coverage flag (≥ 10 prints rule kept as K9); overlap HL events are already ≥ 2025 (gate.py builds them from 2025 only).
Data end fixed at the 1h bar opening 2026-10-23 08:00 UTC (was "now", which changed the cache keys hourly).
- Also before scoring: C2209 overlap agreement skips Bybit (its only price source is trade dumps; HL-size coins are 50–200 MB per day). Bybit trade-dump bars are built per event window (T − 1 d → T + 9 d), not per coin.
