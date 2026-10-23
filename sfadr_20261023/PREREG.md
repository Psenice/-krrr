# PREREG — ccsp2 sfadr_20261023: signal factory on Asian ADRs vs the home-market close

Written 2026-10-23 11:09 Prague (mtime), before any outcome is computed. Ledger C2160–C2179. All numbers will be backtest.
Data on disk (fetched 11:12 Prague, no return computed): yfinance daily OHLC, auto_adjust=False, 2011-06-01 → 2026-10-22,
16 ADRs + 16 home lines + TWD/HKD/JPY/INR/KRW=X + SPY EWJ EWY FXI EWT INDA.

## 1. Universe (fixed)
TSM/2330.TW, BABA/9988.HK, JD/9618.HK, BIDU/9888.HK, NTES/9999.HK, SONY/6758.T, TM/7203.T, HMC/7267.T, MUFG/8306.T,
SMFG/8316.T, INFY/INFY.NS, HDB/HDFCBANK.NS, IBN/ICICIBANK.NS, KB/105560.KS, SHG/055550.KS, PKX/005490.KS.
Country proxy: TW→EWT, HK→FXI, JP→EWJ, IN→INDA, KR→EWY (deviation from the brief's SPY/EWJ/EWY/FXI list: EWT and INDA added
because no listed ETF covers Taiwan or India). Global proxy: SPY. HK lines start 2019-11 → 2021-03 (listing dates).

## 2. Construction (log prices; D = US trading date; every input is known at the ADR open of D)
- FX(D) = Open of the yfinance FX bar dated D (≈ 00:00 London, before the US open; the bar's Close is after it → not used).
  FX glitch rule: a day whose |log FX(D) − median FX(D−2..D+2 excluded D)| > 3 % is NaN (uses neighbours for cleaning only, no signal uses future FX).
- H(D) = log home Close(D) − log FX(D). Requires a home bar dated D (home holiday → no trade that day).
- raw(D) = log ADR Close(D) − H(D). ref(D) = median raw(D−20..D−1) (≥ 10 valid) → ratio adjustment, absorbs ADR ratio and level.
- prem(D) = log ADR Open(D) − H(D) − ref(D). Day invalid if |prem| > 0.15 (ratio change / bad print) or any input NaN.
- Rolling z: z = x / sd(x over the previous 250 valid days, ≥ 60), lagged (sd excludes D).
- Hold returns from the ADR Open(D): H0 = Close(D)/Open(D); H1 = Close(D+1)/Open(D); H5 = Close(D+5)/Open(D) (trading days of the ADR).
- Hedge "raw" = ADR alone. Hedge "hdg" = ADR − β_c·(country ETF over the same window), β_c = rolling OLS slope of ADR on ETF
  close-to-close daily log returns over the previous 250 days (lagged).
- Cost: 5 bp RT per leg notional → 5·(1 + |β| if hedged) bp. Borrow 50 bp/yr on the short leg notional per overnight held
  (H0 = 0 nights, H1 = 1, H5 = 5 trading days). Net bp per trade is of the ADR notional (max exposure known at entry).

## 3. Families (grid counted: 144 cells + F4 frozen 3)
- **F1 premium fade:** x1 = prem(D). Side = −sign(x1) if |z1| ≥ k, k ∈ {1, 1.5, 2, 2.5}. 4 k × 3 holds × 2 hedges = 24.
- **F2 residual vs overnight futures proxy:** m(D) = proxy overnight gap log Open(D)/Close(D−1), proxy ∈ {SPY, country ETF}.
  β2 = rolling OLS slope (with intercept) of prem on m over the previous 250 valid days (≥ 60), lagged. x2 = prem − (α2 + β2·m).
  Sides: fade (−sign x2) and continue (+sign x2). 4 k × 3 holds × 2 hedges × 2 sides × 2 proxies = 96.
- **F3 home move not yet in the ADR's prior close (continuation):** x3 = H(D) + ref(D) − log ADR Close(D−1).
  Side = +sign(x3) if |z3| ≥ k. 4 k × 3 holds × 2 hedges = 24.
- **F4 C213 sign rule ported (frozen, no tuning):** w = log ADR Open(D)/Close(D−1); e = country ETF same gap;
  β4 = OLS with intercept of w on e on the pair's first 30 eligible nights, then frozen (C1922 spec). d = w − β4·e;
  trade if |d| ≥ 50 bp, side = −sign(d); gross = side·(ADR hold − β4·ETF hold). Primary hold H0 (closest to C213's 2-h hold);
  H1/H5 reported. Scored on its own (not in the grid max), cost 5·(1+|β4|) bp + borrow.
- **Reverse report (not traded, C2166):** r(D) = log ADR Close(D) − H(D) − ref(D) (US-session divergence). Regress the home
  next gap g = log homeOpen(D') − log homeClose(D) (D' = next home bar) and the home next day log homeClose(D')/homeOpen(D') on r,
  pooled and per pair: slope, NW t, R², on all years ≤ 2025. Note: yfinance Asian opens can be stale prints; reported as is.

## 4. Slices, statistics, placebo
- Discovery 2012-01-01 → 2021-12-31; middle 2022–2023; **newest 2024-01-01 → 2025-12-31 decides**; holdout 2026-01-01 → 2026-10-22 opened once at the end, for survivors and F4 only.
- Cell t: entry-date portfolio (mean net across firing pairs that day), Newey-West t with lag = hold length (0/1/5), on discovery.
- Ranges: 95 % bootstrap of mean net per trade by 30-trading-day blocks, 2,000 draws.
- **Placebo bar:** 200 runs; in each run every pair's signal series x (F1, F2 both proxies, F3) is date-shuffled within the pair
  on discovery (returns fixed); all 144 cells recomputed; bar = 95th percentile of the run-wise max t.
- **Survivor (discovery):** t ≥ bar AND net > 0 AND ≥ 60 % of pairs (with ≥ 10 trades) net-positive AND ≥ 50 trades/yr pooled.
- **Verdict on newest (2024–25):** KILL if mean net ≤ 0; NOT-ESTABLISHED if range spans 0; SUPPORT if range clear of 0 AND
  trim-5 (drop the 5 best entry dates) > 0 AND no pair > 50 % of net AND a neighbour k also net-positive (plateau).
- If no grid cell survives: family = NOTHING; the best cell per family (max discovery t) is still reported with its newest slice
  and yearly table, labelled exploratory.
- F4 verdict uses the same newest-slice rule, plus random-sign placebo (1,000 flips; share ≥ observed must be < 5 %).
  F4 "supplies C213" only if SUPPORT on newest and the 2026 holdout net > 0.
- Controls (C2161): look-ahead control (signal using Close(D) instead of Open(D) for F1 must show huge t → pipeline sees signals);
  random-signal control (|t| small).
- Money only for a SUPPORT cell that also holds on the holdout: $/month per $100 and at $1k/$5k/$25k, capacity from ADR $volume.

## 5. Ledger plan
C2160 PREREG+bar · C2161 controls · C2162 F1 · C2163 F2 · C2164 F3 · C2165 F4 · C2166 reverse report · C2167 blind review
· C2168 holdout · C2169+ spare. Three standing questions answered in RESULTS.
