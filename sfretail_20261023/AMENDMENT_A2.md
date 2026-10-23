# AMENDMENT_A2 — sfretail_20261023 (before any real-data outcome)
Second pass of the same blind reviewer on run.py + A1: no MUST-FIX. Adopted SHOULD-FIX:
- Holdout mode refuses to run unless out/dev_v1.csv exists; it assigns SUPPORT / NOT-ESTABLISHED / KILL by the PREREG §7 rules and the burst rule (top-5 share ≥ 100 % in development or holdout blocks SUPPORT); the HOLDOUT_OPENED lock is written after a successful compute (a crash does not burn the single run; a successful run cannot be repeated).
- Noted, not changed: the circular-shift join point can create a few placebo events (noise, not bias); the Newey–West lag counts weeks with trades, not calendar weeks (conservative for F3 h20, uneven for sparse F2 cells).
The placebo run (K = 100) started under A1 before this note; A2 does not touch placebo or dev code.
