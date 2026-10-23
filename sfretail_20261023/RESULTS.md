# RESULTS — sfretail_20261023 (ccsp3): retail-attention single stocks
2026-10-23, manual Claude Code cloud session. **All numbers are backtest.** Ledger C2180–C2196 (C2197–C2199 free). PREREG sha d35ac85a, AMENDMENT_A1 540f9926 (blind review + data gate), A2 (holdout code) — all frozen before any real outcome. Code and outputs: GitHub Psenice/-krrr, branch ccr-cee21774-idoot3, folder sfretail_20261023/.

## Verdict
**Nothing passes. 0 of 27 cells survives development, so the holdout confirms nothing. No money.** The best attention cell (F2: after an attention spike on an up day, go long and hold 20 days) is +212 bp net in development, but its t of 2.14 is below the placebo bar of 2.45. It lost −313 bp in 2025 and −467 bp in the 2026 holdout. Its edge is mostly the hindsight-picked universe drifting up: random dates on the same names, with pageviews time-shifted, give +116 bp.

## Data
- **Prices:** yfinance daily, 2015-01 → 2026-10-22, open and close. Dividends are added to the overnight leg on the ex-date. SPY is the hedge. No interior gaps.
- **Pageviews:** Wikimedia REST, en.wikipedia, agent = user, 2015-07-01 → 2026-10-22. Views are summed over the current article title and its former titles (page moves); the list is in scripts/fetch_wiki.py.
- **Rate limit:** the Wikimedia API rate-limited the cloud proxy (HTTP 429 on about half the calls). Retry with backoff got every title.
- **Data gate (A1):**
  - RIOT dropped: no usable article series.
  - AI (C3.ai) dropped: two page moves not covered.
  - Truncated where the company article lived under another title: META before 2020-02, SMCI before 2017-11, MARA before 2025-02, PTON before 2022-04.
  - 38 names in F1/F2/F4; all 40 in F3.
- **Fee basis:**
  - 5 bp per side on the stock.
  - 1 bp per side × beta on the SPY hedge.
  - Borrow 0.5 / 5 / 20 % a year by tier [verify]; the 20 % tier is GME, AMC, UPST, AI, DJT.
  - Unadjusted price ≥ $3.
- **Hedge:** beta from 252 days, clipped to [0, 3].
- **Entry:** the open of the first trading day after the UTC pageview day.

## Placebo bars
Each name's development pageviews (F3: its overnight-share series) are circularly shifted by ≥ 90 days. 100 shifts. The bar is the 95th percentile of the family's maximum Newey–West t on weekly means.

| Family | F1 | F2 | F3 | F4 (top/bottom) |
|---|---|---|---|---|
| Bar | 2.36 | 2.45 | 1.41 | −1.48 |

## Per-family best cell (development = exits ≤ 2025-12-31; holdout = 2026-01-01 → 10-22)
| Family | Best cell | Dev n | Dev net bp [95 % 30-day-block range] | NW t vs bar | Names + | Fires/month | 2025 (newest) | 2026 holdout net [range], n | Verdict |
|---|---|---|---|---|---|---|---|---|---|
| F1 shock (z ≥ 3) | continue (long) 20 d | 806 | +110 [−66, +283] (gross +128) | 1.57 < 2.36 | 65 % | 6.6 | −194 (n 114) | −441 [−818, −54], 76 | NOT-ESTABLISHED dev → dead in holdout |
| F2 shock × sign | up day, continue (long) 20 d | 504 | +212 [−12, +424] (gross +229) | 2.14 < 2.45 | 75 % | 4.1 | −313 (n 65) | −467 [−891, +109], 58 | NOT-ESTABLISHED (fails bar, newest, 50/yr) |
| F3 tug of war (overnight − intraday, 20 d) | long high / short low, weekly | 5,026 legs | +22 [−34, +103] (gross +34) | 0.57 < 1.41 | 35 % | 40 legs (~4.3 rebalances) | +14 (n 686) | −31 [−123, +45], 560 | NOT-ESTABLISHED; trim-5 −16, all of it from 2021 (+351) |
| F4 overnight only, top attention tercile | buy close, sell open | 21,377 name-nights | −4.8 [−10.9, +3.4] (gross +8.7) | −1.04 > −1.48 (bar meaningless: everything is below cost) | 26 % | 172 | −15 (n 3,010) | −21.4 [−33.9, −7.6], 2,467 | KILL |

All other cells are KILL or NOT-ESTABLISHED; the full table is in out/dev_v1.csv and out/holdout_v1.csv.
- **F1 fade:** −45 / −50 / −177 bp at 1 / 5 / 20 d.
- **F2 down-day cells:** all ≤ +19.
- **F3 reverse direction:** −46 to −140.
- **F3 daily:** −2.
- **F4 bottom tercile:** −11.6 [−15.1, −7.8] (gross +1.8).
- **F4 all names (control):** −8.2 (gross +5.3).

**F4 honesty note.** Cost is the killer. In development the high-attention tercile does earn more overnight, gross +8.7 bp a night against +1.8 for the low tercile, a spread of ~7 bp. The round trip costs 10 bp plus the hedge every night. Net was positive only in 2020 (+11) and 2021 (+36). Gross was −1 in 2025 and −7.3 in the 2026 holdout. Cutting cost to zero still would not rescue 2025 or 2026.

## Exploratory (labelled; changes no verdict)
- **F2 up-continue 20 d:**
  - Entry one day later (pageview publication lag): +230 [+2, +445].
  - Spike threshold z ≥ 2.5: +197; z ≥ 3.5: +195. Plateau OK.
  - Excess over the same-name shifted-pageview placebo: +96 bp.
- **F1 continue 20 d:** excess over placebo is −12 bp. F1's continuation is just the universe's drift: the 40 names were chosen in 2026 as retail winners, which is survivorship and hindsight. This repeats K11's lesson that the "edge" was beta and drift.
- **Regime flip (lead only, post-hoc):** fading up-day attention spikes for 5 days (F2_up_fade_h5) lost in the meme years. By year: 2020 −373, 2021 −758, 2022 −70, 2023 +25, 2024 +176, 2025 +128. In the 2026 holdout it made +123 [+20, +221] (n 65, 7.4 fires/month, names + 78 %). Pooled development is −86, so this is a KILL by the frozen rules. It was found after looking, so it is not evidence. The only clean test is a fresh universe (retail names outside the 40, 2023 → 2026) or forward paper, under a new PREREG.

## Three standing questions
1. **Whose money?**
   - Continuation would take from late shorts and fade traders during attention bursts. In practice it took the meme-era drift of names we picked because they won.
   - Fade takes from retail chasers. It only worked from 2023 on.
   - F4 would take the overnight premium that retail open-buying pays. Market makers keep that premium through the spread we pay.
2. **Is the competition strong?** Yes.
   - Pageview attention (Da–Engelberg–Gao 2011, Moat et al. 2013) and the overnight-vs-intraday split (Lou–Polk–Skouras 2019) are public and well known.
   - The signals are daily and free.
   - The open auction and the overnight book belong to wholesalers and HFT.
3. **Is it decaying?** Yes. Every positive cell owes its sign to 2020–21 (and 2024 for continuation).
   - F2 up-continue 20 d: 2020 +1,060, 2021 +656, then 2025 −313 and 2026 −467.
   - F4 top: 2021 +36 net, then 2025 −15.
   - F3: 2021 +351, the rest ≈ 0.

## Caveats
- Four families each at a 95 % bar give about a 19 % chance of at least one false survivor. None appeared.
- Borrow rates are tier guesses [verify]. GME/AMC in early 2021 were far above 20 %.
- Pageview day D is assumed usable at the next open. Hourly dumps make this feasible; the REST daily total can arrive later. Entry a day later was checked (exploratory) and does not change any conclusion.
- The Newey–West lag counts weeks that have trades.
- SIGFACTORY_* and K11SFSTOCKS_RESULTS were not readable: the claude.ai Project is not attached to this session. The method follows the prompt and CLAUDE_current.md.
