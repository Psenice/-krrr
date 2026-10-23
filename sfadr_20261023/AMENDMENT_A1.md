# AMENDMENT A1 — after one blind Opus review (REVIEW_v1.md), before any cell is scored

Written 11:15 Prague 2026-10-23 (file mtime; an earlier label "~11:55" was a guessed clock). Base PREREG sha256 45b1f79b…b563. The only outcomes computed before this: the placebo bar
(shuffled signals, built on the leaky FX → discarded, rebuilt) and pipeline controls (look-ahead t, random-signal t). No real cell.

MUST-FIX applied:
1. FX look-ahead: yfinance FX Open == same-day Close (JPY 2022+ median |O−C| 0.0 bp vs |O−prevC| 33 bp). New FX(D) = Close of
   the previous FX bar on the FX calendar (≤ ~23:00 London D−1, before the Asian close of D). Same FX for every construct.
   FX cleaning made backward-only: NaN if |log FX − median(FX D−4..D−1)| > 3 %.
2. Home rows with Volume 0 or NaN (stale holiday rows) dropped before alignment (no home bar → no trade; next-bar fields skip them).
3. Dividends: every equity series (ADR, home, ETF, SPY) has Open and Close scaled by Adj Close / Close (total-return prices;
   a short pays the dividend).
4. Verdict code added exactly per PREREG §4 (range clear of 0, trim-5 > 0, max pair share ≤ 0.5, neighbour k ± 0.5 net > 0 on newest).
   F2 is ONE family: its best cell is chosen across both proxies and both sides.

SHOULD-FIX applied:
5. Rolling β windows run on valid rows only (dropna, then reindex).
6. Bootstrap block id = trading-day index // 30 (calendar of US days, not trade dates).
7. Placebo: a second placebo with one shared date permutation across pairs; **bar = max(independent bar, shared bar)**.
8. Best cells also reported with NW lag 2h (H1 → 2, H5 → 10) — descriptive, the verdict uses the PREREG t.
9. Stale-open sensitivity: best cells and F4 re-scored excluding days where the ADR or ETF Open equals the previous Close (descriptive).
10. F4: the 30 β-fit nights are excluded from trading; nights with |w| > 0.15 are skipped; F4 needs no home bar (stated).
11. Reverse report: years 2011–2025; r uses FX Close(D) (after 16:00 ET, legitimately known); per-pair t = NW lag 1; pooled t =
    Driscoll-Kraay (per-date sums, NW lag 1). Filter |g|, |oc| < 0.2 is a bad-print filter (labelled).
12. Disclosed execution limit: mSPY, mETF and F4's e use opens printed at the same moment as the ADR open (not known strictly
    before entry); a real trade would use pre-open futures. Not fixed (no intraday data).
