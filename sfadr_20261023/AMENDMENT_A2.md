# AMENDMENT A2 — execution-delay cell C2169 (written ~12:25 Prague, before any intraday bar is fetched)

Why: F1/F2 signals use the ADR Open print, which is also the H0 entry price. A trader sees the print only after it happens,
so part of the H0 edge may be opening-auction bounce that cannot be captured. Daily data cannot answer this.

Cells (frozen; the PREREG "best per family" SUPPORT cells): A = F1 fade k 1.5 H0 raw; B = F2 (SPY proxy) fade k 1.0 H0 raw.
Signal unchanged (daily, uses the Open). Exit unchanged (daily Close). Entry delayed:
- D60: entry at the close of the 09:30–10:30 ET 1h bar (yfinance interval 1h, ≈ 730 days). Pre-holdout window 2024-10-24 → 2025-12-31
  scored now; the 2026 part is scored only when the holdout opens.
- D5: entry at the close of the 09:30–09:35 5m bar (≈ last 60 days, all 2026) → scored only at the holdout opening.
Same cost (5 bp RT) and no borrow (intraday). Reported paired on the same trades: H0 net vs delayed net, and the share of the
H0 gross earned before the delayed entry.
Rule: a cell is EXECUTABLE only if its D60 net on 2024-10-24 → 2025-12-31 is > 0. If D60 ≤ 0, the cell's SUPPORT is
relabelled "SUPPORT-AT-PRINT-ONLY" (not tradeable as built; would need a sub-minute entry study). D5 is descriptive (n small).
