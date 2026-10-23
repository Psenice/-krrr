# PREREG — sfretail_20261023 (ccsp3): retail-attention single stocks
Session ccsp3, manual Claude Code cloud session, 2026-10-23. Ledger block C2180–C2199. All numbers are backtest.
Frozen before any outcome is computed; sha256 recorded in PREREG.sha256. Any change after freezing goes into AMENDMENT_A<n>.md with its own sha256.

## 1. Mechanism and the question
Retail attention buys at the open and chases spikes; institutions trade during the day. Inputs that are not the stock's own price: Wikipedia pageviews and the split of returns into overnight (close→open) and intraday (open→close).
Prior inside this project (K11SFSTOCKS, read from the plan text only, the file itself is not reachable from this session): price-only daily on single stocks = nothing; the "buy panic, hold a month" effect was beta. So every cell here is SPY-beta-hedged, and only a non-price input or the overnight/intraday split may carry the edge.
Literature lead (not a fact for us): Lou–Polk–Skouras "tug of war" (overnight vs intraday momentum), Aboody et al. 2018 (overnight returns as attention), Barber–Odean attention buying.

## 2. Universe (fixed now, 40 names) and Wikipedia articles
TSLA, NVDA, AMD, PLTR, GME, AMC, SOFI, RIVN, LCID, NIO, MSTR, COIN, HOOD, SMCI, ARM, AAPL, AMZN, META, NFLX, BABA, SNAP, UBER, SHOP, RBLX, DKNG, PLUG, MARA, RIOT, BB, CVNA, UPST, AFRM, AI, IONQ, RKLB, SOUN, CHWY, PTON, ZM, DJT. Hedge: SPY.
Article per ticker = the current English Wikipedia article about the company; its daily views are the SUM over the current title and its former titles (page moves split the per-title counts). Candidate titles (a title that returns 404 contributes nothing; the list is in `scripts/fetch_wiki.py` and is frozen):
TSLA Tesla, Inc. + Tesla Motors · NVDA Nvidia · AMD AMD + Advanced Micro Devices · PLTR Palantir Technologies · GME GameStop · AMC AMC Theatres · SOFI SoFi + Social Finance · RIVN Rivian + Rivian Automotive · LCID Lucid Motors + Lucid Group + Atieva · NIO Nio Inc. + NIO (car company) + NextEV + Nio (car company) · MSTR MicroStrategy + Strategy (company) + Strategy Inc + Strategy Inc. · COIN Coinbase · HOOD Robinhood Markets + Robinhood (company) · SMCI Supermicro + Super Micro Computer · ARM Arm Holdings + ARM Holdings + Arm Ltd · AAPL Apple Inc. · AMZN Amazon (company) + Amazon.com · META Meta Platforms + Facebook, Inc. · NFLX Netflix · BABA Alibaba Group + Alibaba Group Holding · SNAP Snap Inc. · UBER Uber + Uber (company) · SHOP Shopify · RBLX Roblox Corporation · DKNG DraftKings · PLUG Plug Power · MARA MARA Holdings + Marathon Digital Holdings + Marathon Patent Group · RIOT Riot Platforms + Riot Blockchain · BB BlackBerry Limited + BlackBerry Ltd · CVNA Carvana · UPST Upstart (company) + Upstart Holdings + Upstart Network · AFRM Affirm (company) + Affirm Holdings · AI C3.ai + C3 IoT + C3.ai (company) · IONQ IonQ · RKLB Rocket Lab + Rocket Lab USA · SOUN SoundHound + SoundHound AI · CHWY Chewy (company) + Chewy, Inc. + Chewy.com · PTON Peloton Interactive + Peloton (company) · ZM Zoom Communications + Zoom Video Communications · DJT Trump Media & Technology Group.
Drop rule (decided before outcomes, applied at the data gate, written into DATA_GATE.md): a name is dropped from the attention families (F1, F2, F4) if its summed series has < 365 valid days or a visible step ≥ 10× in the 60-day median that coincides with a page move not covered by the title list. F3 uses all 40 names (no pageviews).

## 3. Data
- Prices: yfinance daily, 2015-01-01 → 2026-10-22, `auto_adjust=False` (split-adjusted Open/Close) plus the Dividends and Stock Splits columns.
- ov_t = (Open_t + Div_t)/Close_{t-1} − 1; id_t = Close_t/Open_t − 1; open-to-open index I_t = Π(1+id_{t−1})(1+ov_t). Same for SPY.
- Beta: trailing 252 trading days of close-to-close returns vs SPY, ≥ 120 obs, clipped to [0, 3], taken at the close before entry.
- Price floor: unadjusted prior close ≥ $3 (split-adjusted close × later split factors).
- Pageviews: Wikimedia REST per-article, en.wikipedia, all-access, agent = user, daily 2015-07-01 → 2026-10-22. Days before the first non-zero day of the summed series are missing.
- Attention z for calendar day D: z_D = (x_D − mean(x_{D−60..D−1})) / sd(x_{D−60..D−1}) with x = log(1 + views), ≥ 50 valid days in the window.
- Timing: the UTC pageview day D is complete at 20:00 ET on D (after the US close). The first usable entry is the OPEN of the first trading day with date > D. F4's score at the close of trading day t uses calendar day t−1.

## 4. Families and cells (27 counted cells)
All positions are SPY-beta-hedged (stock ± beta × SPY over the same interval). Hold h = open of entry day E → open of day E+h (trading days). Per name, a new event trade cannot start while one is open (no overlap).
- **F1 attention shock** (6 cells): z_D ≥ 3. One trade per (name, entry day) (largest z kept). Fade = short, continue = long. h ∈ {1, 5, 20}. Cells F1_fade_h{1,5,20}, F1_cont_h{1,5,20}.
- **F2 shock × sign of same-day return** (12 cells): F1 events where D is a trading day; sign of D's close-to-close return. {up, down} × {fade, continue} × h ∈ {1, 5, 20}. Fade of an up day = short, fade of a down day = long.
- **F3 overnight–intraday tug of war** (6 cells): OS_t = Σ_{20 days} [log(1+ov) − log(1+id)]. At close t rank names (≥ 10 valid), enter at the open of t+1, top and bottom quintile (k = max(2, n//5)) equal weight, every name SPY-beta-hedged; rebalance every h ∈ {1, 5, 20} days (5 = the weekly cell named in the plan). hiLo = long highest OS / short lowest (the plan's direction); loHi = the mirror, counted. Turnover charged per name entering/leaving.
- **F4 overnight-only on the high-attention tercile** (3 cells): each trading day t, rank names by z of calendar day t−1 (≥ 9 valid names); buy the close of t, sell the open of t+1, SPY-overnight-hedged. Cells: top tercile (the plan's cell), bottom tercile and all names (controls, counted). Holds 5/20 do not apply to an overnight-only position.
Total counted cells: F1 6 + F2 12 + F3 6 + F4 3 = 27.

## 5. Costs (fee basis)
Stock 5 bp per side (10 bp round trip). SPY hedge 1 bp per side × beta. Borrow for stock shorts (annual, [verify]): 0.5 % for AAPL AMZN META NFLX NVDA AMD TSLA UBER SHOP BABA ARM COIN SNAP RBLX DKNG ZM PLTR HOOD SOFI CHWY; 5 % for SMCI MSTR RIVN LCID NIO MARA RIOT BB CVNA AFRM IONQ RKLB SOUN PTON PLUG; 20 % for GME AMC UPST AI DJT. Short SPY hedge 0.3 %/yr. Borrow accrues for h/252 years. Gross is reported next to net for every cell. F4 pays 10 bp + hedge every night.

## 6. Splits, statistics, placebo
- Development = trades with exit ≤ 2025-12-31 (pageviews from 2015-07). Yearly splits 2015…2025. Newest slice of development = 2025.
- Holdout = entries ≥ 2026-01-01 (to 2026-10-22). Opened ONCE at the end, for all cells in one run, after the development verdicts are written.
- Headline: mean net bp per trade (of the position notional at entry). Range: 95 % bootstrap over 30-day blocks of entry dates (1,000 draws). t: weekly means of net bp by entry week, t = mean/sd·√weeks.
- Placebo (per family): shuffle each name's pageview series across dates within the name (F1, F2, F4: recompute z and all cells of the family); for F3 shuffle each name's OS series across dates within the name. 100 shuffles, the statistic is the max t over the family's cells on development; the bar is the 95th percentile.
- Also reported: trim-5 (mean without the 5 best trades), top-5-trade share of total P&L, fraction of names positive (names with ≥ 3 trades), trades/yr, fires/month, per-year means.

## 7. Verdict rules (decided now)
A development cell SURVIVES only if all hold: t > its family placebo bar; mean net > 0 with the block range lower bound > 0; ≥ 60 % of names positive; ≥ 50 trades/yr; trim-5 > 0; newest slice (2025) mean net > 0 (newest slice decides: ≤ 0 → not a survivor).
Holdout: a survivor is SUPPORT if 2026 mean net > 0 with block range lower bound > 0; NOT-ESTABLISHED if 2026 mean > 0 but the range includes zero; KILL if 2026 mean ≤ 0.
Non-survivors: KILL if the development mean net ≤ 0 or the upper bound < 0; otherwise NOT-ESTABLISHED (with the failed gate named). Exploratory numbers (plateau z 2.5/3.5 on any survivor, gross-only views) are labelled exploratory and never change a verdict.
Burst rule (needed for KEEPER, decided now): if a survivor's top-5-trade share ≥ 100 % it cannot be SUPPORT. Max drawdown and underwater time are reported for a survivor.
Money ($/month per $100, $1k/$5k/$25k) is computed only for a cell with SUPPORT.

## 8. Standing questions to answer per family
Whose money are we taking? Is the competition strong? Is it decaying (yearly splits, newest slice)?

## 9. Ledger plan
C2180 PREREG + data gate; C2181 blind review; C2182–C2187 F1; C2188–C2193 F2 (grouped); C2194–C2195 F3; C2196 F4; C2197 placebo bars; C2198 holdout; C2199 close/handoff. Rows go to LEDGER_ROWS_ccsp3_PENDING.csv (the PC merges them into CLASSIC_LEDGER.csv).
