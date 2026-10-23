# AMENDMENT A3 — executable pre-market cell C2170 (written ~12:45 Prague, before any pre-market bar is fetched)

Why: C2169 holdout shows the 2026 F1/F2 edge is earned at the open print (5-min delayed entry ≈ 0). An executable version must
know its signal before the open: compute it from the last pre-market ADR trade and enter at the official open (market-on-open,
NYSE accepts MOO until 09:28 ET), exit at the daily Close.

Cells (frozen, same k / side / hold / hedge as A2): A = F1 fade k 1.5 H0 raw; B = F2 (SPY proxy) fade k 1.0 H0 raw.
Signal: identical construction but log ADR Open(D) replaced by log P_pm(D) = Close of the last pre-market bar ending at or
before 09:30 ET (yfinance prepost=True; 1h bars ≈ 730 days, 5m bars ≈ 60 days) with Volume > 0 in the 08:00–09:30 window;
SPY's pre-market price likewise for F2's m. z uses the same lagged sd as the daily signal (sd of the daily x — fixed scale).
Days without a pre-market ADR trade in 08:00–09:30 → no trade. Return = side·(log Close(D) − log Open(D)) − 5 bp.
Windows: pre-holdout 2024-10-24 → 2025-12-31 (1h) decides together with 2026 (1h + 5m), since the holdout is already open
(stated: this cell is post-holdout and is exploratory-confirmatory, not a fresh holdout).
Rule: EXECUTABLE-SUPPORT if 1h-based net > 0 with the 30-day-block range clear of 0 on 2024-10-24 → 2026-10-22 AND the 2026 part > 0;
NOT-ESTABLISHED if the range spans 0; KILL if net ≤ 0.

A3b (12:55 Prague, before any C2170 outcome): Yahoo reports Volume 0 on every pre-market bar, so "Volume > 0" removes all days
(the first run returned zero trades). Replaced by: the bar must show a trade range High > Low. Nothing else changed.
