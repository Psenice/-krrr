# HANDOFF — cce4v: E4 supply on more venues, 2026-10-23

Claude Code cloud session, 11:07–12:35 Prague. Drive `trading_cloud_2026-10-23/e4venues_20261023` (id 1pA8ggYvYnocjB1dIo9h21pgSh35Hzg1o). Ledger C2200–C2214 used (C2215–C2219 free), pending in `LEDGER_ROWS_cce4v_PENDING_v2_final.csv`. All numbers backtest.

## What ran
1. Gate (C2200–C2202): listing = first kline on OKX/Bitget/Gate (API daily candles), Bybit (public trade dumps; REST geo-blocked). NEW events: OKX 26, Bitget 57, Gate 75, Bybit 82; union 100 / 78 coins (2025 81, 2026 19); 20 Bybit-only.
2. PREREG frozen 11:39 (sha256 bbf1424f…40b6) → blind Opus review (5 must-fix: Gate page gap, Gate funding error cache, union pick order, 1000X symbol check, Bybit rows) → A1 before scoring.
3. NEW-layer excess vs placebo +755 [−113, +1,523] n 71 → NOT-ESTABLISHED; N168 +202 [−828, +1,128] n 67; funding −636; 2026 N168 +21 (n 14). Bitget alone +959 [+149, +1,684] n 57 (variant).
4. Pooled 2026 N168 +749 [+197, +1,284] n 96 → PASS by rule, but HL+Aster alone is +874 n 82; money unchanged ($17.47 vs $17.43 per $100/month at 1×). New events/month 4.4 → 1.5 (2025 → 2026).
5. EU: Bybit and Gate spot-only for EEA; OKX EU X-Perps (MiFID); Bitget unclear (no MiCA licence) [verify].

## Decision for Michael
None needed: no new-venue sleeve for E4 paper. Optional: Bitget-only follow-up if Bitget's EU status clears (needs a funding source for 2025).

## Blockers
Bybit REST geo-blocked (no funding/placebo). OKX funding API keeps ~3 months. Bitget funding history short (not traced). Project files can't be written from the cloud → mirrors are on Drive as `PROJECT_MIRROR_claude_CCE4V_RESULTS_2026-10-23.md` and `PROJECT_MIRROR_sessions_2026-10-23_cce4v.md`; copy them into the Project.

## Files
Drive: PREREG.md · AMENDMENTS_v1.md · RESULTS.md · LEDGER_ROWS_cce4v_PENDING_v2_final.csv · HANDOFF_cce4v.md. Scripts, transcribed inputs and output CSVs (new_scored, new_union, gate_events, depth_books, overlap_agreement): GitHub Psenice/-krrr, branch `ccr-d607812d-v6j7g2`, folder `e4venues_20261023/` (raw caches not committed; re-fetch ~40 min).
