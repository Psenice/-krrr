# AMENDMENT_A1 — sfretail_20261023 (before any real-data outcome)
Written after the blind review (one fresh Opus subagent, PREREG + scripts, no outcomes) and the data gate. No real-data P&L, t or mean has been computed. Smoke runs used shuffled pageviews and shuffled OS only (counts, no P&L read). sha256 in AMENDMENT_A1.sha256.

## Review MUST-FIX, adopted
1. Placebo shuffle (F1, F2, F4): replaced the full random permutation with a CIRCULAR SHIFT of each name's development-period pageview series (dates ≤ 2025-12-31) by a random offset ≥ 90 days. This keeps the trend, clustering and event count; holdout values are never moved into development (also fixes SHOULD-FIX 6). Placebo event counts are logged next to the real ones.
2. F3 placebo: the same circular shift (≥ 90 trading days) of each name's OS series, so the placebo keeps OS's autocorrelation and its turnover cost.
3. t statistic: Newey–West t on weekly means of net bp by entry week, lag ⌈h/5⌉ (h = 1 → lag 1). Used for real cells and the placebo alike.
4. F4_all is a CONTROL: reported, not in the F4 placebo bar (the bar is max t over F4_top and F4_bottom), not eligible to survive.
5. Runner `scripts/run.py` written and frozen with this amendment (modes placebo / dev / holdout; holdout writes out/HOLDOUT_OPENED and refuses a second run). Newest slice = entries in 2025 with exit ≤ 2025-12-31. K = 100 shifts per family, seed 20261023.

## Review SHOULD-FIX
6. Adopted (see 1–2). 7. Checked: no interior price NaN for any of the 40 names after reindexing to the SPY calendar. 8. Exploratory (label only): F1/F2 best cell re-run with entry one trading day later (pageview publication lag). 9. Exploratory: fade cells re-run with GME/AMC/BB/... meme names' 2021-01-01 → 2021-03-31 trades removed, and with borrow ×3 on the 20 % tier. 10. Noted: the ≥ 50 trades/yr gate does not bind for F3/F4 (legs/nights are counted). 11. Adopted: every cell reports placebo mean and real mean − placebo mean (same names, shifted dates). 12. Noted, left as is (F3 requires the exit price to exist at selection; hedge cost slightly over-charged). 13. Stated: four families each at a 95 % bar → about 19 % chance of at least one false survivor across the session.

## Data gate (DATA_GATE.md / out/data_gate_v1.csv)
- RIOT dropped from F1/F2/F4: "Riot Platforms"/"Riot Blockchain" return no pageview series (404 / one day).
- AI (C3.ai) dropped from F1/F2/F4: the article is ~0 views until 2023-03 and falls 10× again in 2025-10 (two moves not covered by the title list).
- Truncated (series set missing before the date, because the company article lived under an uncovered title and the 60-day median steps ≥ 10×): META < 2020-02-01 (company article split from "Facebook" in 2019-12), SMCI < 2017-11-01 (2017-06/08 gap), MARA < 2025-02-01 (article only from 2024-12), PTON < 2022-04-01 (article from 2022-02).
- ZM 2020-03/04 (×34) is real COVID attention, kept. ARM 2023-10 (IPO) kept.
- F3 keeps all 40 names.
- Attention families: 38 names.

## Engine fixes made after the freeze, before any outcome (code hashes in AMENDMENT_A1.sha256)
- cells.py f4: column reindex to NAMES (crashed when a name has no series); `.dropna()` after stack (pandas 2 kept empty rows, all three F4 cells had identical rows); beta for F4 shifted to the close before the entry close.
- cells.py f3: rewritten with numpy arrays (27 s → 1 s per run, needed for 100 placebo shifts); same rules, row counts identical on the smoke input.
- sflib.py: TRUNC dict (data gate).
