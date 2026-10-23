# RESULTS — ccsp2 sfadr_20261023: signal factory on Asian ADRs vs the home-market close (2026-10-23)

Session ccsp2 (cloud, manual). Ledger C2160–C2172 (C2173–C2179 unused). **All numbers are backtest.** Fee basis: 5 bp round trip per leg plus 50 bp/yr borrow on the short leg.
Population: 16 ADR/home pairs (TW 1, HK 4 from 2019–21, JP 5, IN 3, KR 3), yfinance daily 2011-06 → 2026-10-22, plus yfinance 1h/5m bars for the execution cells.
Hashes: PREREG 45b1f79b (frozen 11:09 Prague); A1 daab2f79 (applied after one blind Opus review, before scoring); A2/A3/A4 written before their own data. Time labels were corrected at 11:26 (no rule changed), see PREREG.sha256.

## Read this first
1. **The daily factory finds a real ADR open-premium fade.** It works when the ADR opens rich or cheap against the FX-adjusted home close: fade it from the open to the close.
   - Best F1 cell (k 1.5, open→close, unhedged): discovery 2012–21 t 5.83 vs the placebo bar 2.42.
   - Newest 2024–25: **+22.1 bp [+5.6, +39.7]**, n 813, 34 fires/month.
   - Holdout 2026: **+30.2 [+2.6, +59.7]**, n 414, 15/16 pairs positive.
   - 12/12 newest-SUPPORT cells were positive on the holdout.
2. **As built it cannot be traded.** The signal uses the opening print, and in 2026 the reversion happens in the first minutes after it.
   - Share of the open→close gross already earned before the delayed entry: 81 % with a 1h delay; with a 5-minute delay (Aug–Oct 2026) all of it.
   - A 5-minute-delayed entry earns −5.4 bp, n 74 (C2169).
3. **The executable twin is SUPPORT, post-holdout (C2170).** It computes the signal from the last pre-market ADR trade, enters market-on-open and exits at the close.
   - F1 k 1.5: **+20.3 bp [+4.3, +34.6]**, n 895, 2024-10-24 → 2026-10-22, 36 trades/month.
   - 2026 part: +22.6 [−1.9, +47.5], n 410. Plateau holds: k 1.0 +10.5, k 2.0 +27.9, k 2.5 +30.1.
   - **Weak spots:**
     - Country-ETF hedged it is +3.6 [−4.5, +12.0], so the edge is mostly a country-level premium reversal.
     - The top 5 days carry 65 % of the net.
     - At a 10 bp round trip it is +15.3 [−0.7, +29.6].
     - On the full 1h history (from 2023-11) it is +13.6 [+2.1, +24.7].
4. **F4 (the C213 sign rule ported to ADRs): KILL.** Newest −9.8 [−15.1, −3.4], n 4,724; holdout −11.3. So ADRs supply nothing to C213. The ADR's idiosyncratic gap against its country ETF continues rather than fades.
5. **Reverse direction (not traded).** The ADR's US-close divergence prices the home market's next open (slope 0.55, R² 0.38). The home open→close afterwards is barely predictable (slope 0.055, R² 0.003).

## Per family: best cell vs placebo bar (bar 2.42 = max of independent / shared date-shuffle 95th pct over 144 cells, 200 runs each)
| family | best cell (by discovery t) | disc t | disc net, n | newest 2024–25 net [range], n | verdict | holdout 2026 |
|---|---|---|---|---|---|---|
| F1 premium fade | k1.5 H0 raw | 5.83 | +13.1, 3,386 | +22.1 [+5.6, +39.7], 813, 34/mo | SUPPORT (at print) | +30.2 [+2.6, +59.7], 414 |
| F2 residual after overnight proxy | SPY, fade, k1.0 H0 raw | 7.98 | +12.9, 7,493 | +10.1 [+0.4, +20.6], 1,929, 80/mo | SUPPORT (at print) | +14.9 [−4.1, +35.4], 848 |
| F2 continue side | best ≤ 0 net | — | — | — | NOTHING | — |
| F3 home move continuation | k1.0 H0 raw | 7.02 | +13.0, 7,992 | +8.4 [−0.6, +17.3], 1,993, 83/mo | NOT-EST | −2.0 [−22.9, +17.9], 973 |
| F4 C213 port (frozen) | H0 | −3.79 | −4.1, 20,094 | −9.8 [−15.1, −3.4], 4,724, 197/mo | **KILL** | −11.3 [−18.9, −2.8], 2,182 |
Survivors on discovery: 50 of 144 (all F1/F2 fade or F3, almost all H0/H1). Newest: 12 SUPPORT, 27 NOT-EST, 11 KILL. Holdout: 43/50 net > 0.
F1 yearly (k1.5 H0 raw, bp/trade): 2012 +9 · 13 +22 · 14 +12 · 15 +15 · 16 +7 · 17 +13 · 18 +13 · 19 +8 · 20 +22 · 21 +6 · 22 +32 · 23 −1 · 24 +13 · 25 +31 · 26 +30.
Stale-open exclusion changes no number by more than 0.3 bp. NW t with lag 2h equals the lag-h t for H0 cells.

## Execution cells (A2 / A3 / A4)
| cell | window | n | net bp [30-day block range] | note |
|---|---|---|---|---|
| C2169 F1 entry 10:30 (1h delay) | 2024-10-24..2025 | 461 | +23.1 [−1.5, +49.3] | 80 % of open→close edge left |
| C2169 F1 entry 10:30 | 2026 | 414 | +1.8 [−15.2, +23.8] | 81 % earned before 10:30 |
| C2169 F1 entry 09:35 (5m) | 2026-07-30..10-22 | 74 | −5.4 [−19.6, +9.2] | all earned in 5 min |
| C2169 F2 entry 10:30 | pre / 2026 | 1,103 / 847 | +7.4 / +0.4 | |
| **C2170 F1 pre-market signal, MOO→close** | 2024-10-24..2026-10-22 | 895 | **+20.3 [+4.3, +34.6]** | 13/16 pairs+, max pair 22 %, trim-5 +7.5 |
| C2170 F1 | 2026 only | 410 | +22.6 [−1.9, +47.5] | |
| C2170 F2 (SPY) | 2024-10-24..2026-10-22 | 1,891 | +7.8 [−1.8, +17.5] | NOT-EST |
| C2171 F1 k1.0 / k2.0 / k2.5 | same | 1,918 / 446 / 234 | +10.5 [+0.4, +19.9] / +27.9 [+11.1, +44.9] / +30.1 [+0.4, +55.1] | plateau holds |
| C2171 F1 k1.5 ETF-hedged | same | 895 | +3.6 [−4.5, +12.0] | edge is mostly country-level |
Pre-market bars: Yahoo prepost 1h, last bar 09:00–09:30 with High > Low (Yahoo pre-market volume reads 0). The bar close equals the official open on only 1–6 % of days, so there is no open-print contamination. The last pre-market print can fall after the 09:28 MOO cutoff (disclosed, up to 2 min).

## Money (C2170 F1 k1.5 only; backtest, before a live haircut of one third)
- $1k per trade: +$1,821 over 25 months = **$73/month**. Max drawdown $335. Longest underwater stretch 68 active days.
- Capital = 6 × the per-trade size, because p95 is 6 concurrent same-day trades (max 13). That gives ≈ 1.2 %/month on capital.
- Per $100 of capital: **$1.2/month**; $1k: $12; $5k: $61; $25k: $300. The range lower bound (4.3 bp) gives ≈ 0.26 %/month.
- Capacity, at ≤ 0.2 % of the ADR's daily $ volume (≈ 10 % of the opening auction): 100 % of trades fit at $5k per trade and 84 % at $25k per trade. KB, SHG, PKX, SMFG and HMC cap first ($14k–$59k median).
- Fills: auction to auction (MOO/MOC), so 5 bp RT is plausible. At 10 bp RT the range touches 0 (ours) / clears it (red-team).
- Red-team-adjusted planning (+12 bp instead of +20.3): ≈ $0.7/month per $100 of capital ($7 / $36 / $180 at $1k / $5k / $25k). Ex top-5 days the range includes 0, so the money is **not established** without forward paper.

## Three standing questions
- **Whose money:** pre-market and opening traders in Asian ADRs who push the US open away from the FX-adjusted home close, mostly at the country level (ETF-hedged it is ≈ 0). The day session pulls it back. Part of it may be the generic US open-gap reversal (F2 with SPY removed is weaker: +7.8).
- **Competition:** strong in principle. ADR/ordinary arbitrage desks with conversion rights own this band. What is left is a ~20 bp reversion on |z| ≥ 1.5 days, inside their conversion-cost band. The 2026 shift of the reversion into the first 5 minutes says faster players already take the post-print part.
- **Decaying:** the daily-bar edge is not decaying (2024 +13, 2025 +31, 2026 +30). The capturable window is shrinking: the edge left after a 1h delay fell from 80 % (2024–25) to ~20 % (2026). The pre-market/MOO version has held so far (2026 +22.6).

## Verdicts
C2162 F1 SUPPORT (at print, not executable) · C2163 F2 SUPPORT (at print) · C2164 F3 NOT-EST · C2165 F4 KILL · C2170 F1 pre-market MOO **EXECUTABLE-SUPPORT, red-team WEAKENED (crisis-day concentrated; written after the holdout opened)** · C2170 F2 NOT-EST · C2171 plateau holds, hedged ≈ 0 · C2172 red-team row.
**Next step (not a backtest): forward paper.** Each US day at 09:20 ET, compute x from the latest pre-market ADR quote and the home close + FX. Paper-place MOO / MOC orders at $1k for |z| ≥ 1.5.
Log the official open, the close and the 09:20 quote. Kill rules, written now:
- After ≥ 100 trades: KILL if net ≤ 0 or median trade ≤ 0.
- Early KILL after ≥ 40 trades if net ≤ −15 bp.
- GO to the $50–100 live step (Michael's call) only if net > 0 ex the top-5 days.

## Red-team (one Opus agent, independent code written before reading ours) — **WEAKENED**
- Rebuild: +22.4 bp [+13.0, +31.9], n 911 (ours +20.3, n 895; small diffs in FX cleaning and min_periods). 2026 +25.1, n 420.
- Timing: using only the 08:00 bar (ends by 08:59, safely before the MOO cutoff) gives +19.3 [+12.3, +26.1], n 836.
  The pre-market price sits a median 36 bp from the open print. Home closes all precede 09:30 ET.
- Whether the yfinance daily Open is the official auction price is UNVERIFIED.
- Mechanism: the naive rule with no home leg (fade the ADR's pre-market move vs its prior close) earns +4.7 [−19.2, +29.8].
  Main-rule trades the naive rule does not take earn +21.2. So it is home-close mispricing, not pre-market noise.
- Cost: 10 bp RT gives +17.4 [+7.8, +26.8] on its rebuild.
- **Concentration (the weakness):**
  - The top 5 days carry 62 % (2025-04-08/09 tariff shock, 2026-03-03, 03-19, 05-13).
  - Ex top-5 days: +8.9 [−2.0, +21.4]. Ex top-10: +3.6. Symmetric trims are steadier: ±5 days +15.3 [+6.1, +24.8]; ±10 days +15.2.
  - Without BABA and TSM: +14.1 [+6.6, +21.5]. India pairs are weak or negative (INFY −13, HDB −2).
  - Long side (buy the cheap ADR) +36.8 vs short side +8.8.
- Planning number: **+10 to +15 bp per trade in normal conditions**, with the headline lifted by crisis days.

## Blockers / deviations
- EWT/INDA were added as country proxies; the brief lists no Taiwan or India ETF.
- yfinance FX Open equals the same-day Close (look-ahead). Fixed to the previous FX bar's close (A1). The placebo built on the leaky series was discarded.
- Pre-market volume is not reported by Yahoo, so the A3b High > Low rule is used instead.
- Intraday history is ≈ 730 days for 1h and 60 days for 5m. So C2170 has no pre-2023 test, and its window overlaps the opened holdout.
- No Project attached. The mirrors go to Drive with Project file names.
