# HANDOFF — ccsp2 sfadr_20261023 (cloud, 2026-10-23 11:05–11:40 Prague)
**Item:** CLAIM_cc_PICKEDSTOCKS item 2, a signal factory on Asian ADRs vs the home close. Ledger C2160–C2172 (C2173–C2179 unused). All numbers backtest; 5 bp RT + 50 bp/yr borrow.

## Verdicts
- **F1 premium fade:** ADR open vs FX-adjusted home close, k 1.5, open→close. SUPPORT at print.
  Discovery t 5.83 vs bar 2.42; newest +22.1 [+5.6, +39.7] n 813; holdout 2026 +30.2 [+2.6, +59.7] n 414.
  Not executable as built: a 5-minute-delayed entry in 2026 earns −5.4 (n 74).
- **F2 residual after the SPY gap, fade:** SUPPORT at print, newest +10.1 [+0.4, +20.6]. The continue side is NOTHING.
- **F3 continuation:** NOT-EST, newest +8.4 [−0.6, +17.3]; holdout −2.0.
- **F4 (C213 rule on ADRs):** KILL, newest −9.8 [−15.1, −3.4] n 4,724; holdout −11.3. It gives C213 no supply.
- **Reverse (not traded):** the ADR US-close divergence prices the home next open (slope 0.55, R² 0.38). The home open→close is barely predictable (R² 0.003).
- **C2170 executable twin:** pre-market signal, MOO → close, F1 k 1.5. +20.3 [+4.3, +34.6] n 895 (2024-10 → 2026-10), 36 trades/month; plateau holds.
  - ETF-hedged ≈ 0, so the reversal is country-level.
  - Red-team: WEAKENED. Rebuild +22.4; ex top-5 days +8.9 [−2.0, +21.4]; planning +10 to +15 bp.
  - It was written after the holdout opened, so it is exploratory-confirmatory.
- **Money:** not established until forward paper. Indicative: $0.7–1.2/month per $100 of capital.

## Deviations / blockers
- The yfinance FX Open equals the same-day close. It was caught by the blind review and fixed before scoring (A1).
- The clock labels in the amendments were guessed and then corrected to file mtimes. No rule changed.
- Yahoo pre-market volume is 0, so the A3b High > Low rule is used instead.
- Intraday history is ≈ 730 days only.
- No claude.ai Project in this session, so the mirrors went to the Drive root with Project names.

## PC merge
- Append C2160–C2172 from LEDGER_ROWS_ccsp2_PENDING.csv after re-reading the tail.
- Copy the Drive folder to Desktop/trading/sfadr_20261023/. Scripts, data-free outputs and SCRIPTS.md/OUTPUTS.md are in GitHub psenice/-krrr, branch ccr-f2e6552f-b18rmu, folder sfadr_20261023/ (Drive holds the docs only).
- INDEX row: "ccsp2 sfadr — ADR vs home close: F1/F2 fade real at print; pre-market MOO twin SUPPORT/WEAKENED; F4 KILL".
- Proposal (Michael's call): add C2170 to the forward paper log, with the kill rules in RESULTS.
