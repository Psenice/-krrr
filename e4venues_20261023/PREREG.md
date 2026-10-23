# PREREG — cce4v: E4 supply on more venues (Bybit, OKX, Bitget, Gate) — e4venues_20261023

_Claude Code cloud session cce4v, 2026-10-23, Prague ~11:55. Ledger block C2200–C2219 → `LEDGER_ROWS_cce4v_PENDING.csv`. All numbers are backtest. Written before any event return, funding sum, placebo or price-agreement number was computed. The venue gate (step 1) fetched daily candles only to read first/last bar timestamps (listing dates); no price was looked at or used._

## 0. Question and inputs
E4 (short 7 days after a Korean listing notice) is event-limited: it trades only coins with a perp on Hyperliquid (HL) or Aster. Does the frozen E4 rule pay on the notices whose coin had no HL/Aster perp but did have a USDT perp on Bybit, OKX, Bitget or Gate — and does adding them keep the pooled E4 book positive in 2026?
- Notice census: Drive `korea_supply_events.csv` (325 rows, 2025-01-02 → 2026-10-15), transcribed without titles to `data/census_slim.csv`. Check: 325 rows; G1 class (`f_HL != S and f_Aster == S`) = 66 (= G1); `f_HL == S` 98; neither 161.
- HL events: Drive `e4x_rebuild_events.csv` (166; 126 from 2025-01-01 to 2026-10-15) → `data/e4x_hl_events.csv`. Aster events: K9 `events_scored_slim.csv` → `data/k9_aster_scored.csv` (66; 65 scored). Check: HL ≥2025 N168 mean +1,042 (n 126); Aster N168 +751 (n 65), excess +1,293 (n 64); pooled 191 +943 = K10 gate exactly.
- `S`/`D` flags in the census mean: perp live ≥ 24 h before T (`S`), or listed in the last 24 h (`D`).

## 1. Venue gate (C2200–C2202)
- Listing = first kline of the coin's USDT perp: OKX/Bitget/Gate daily candles from the public API (symbols `X-USDT-SWAP`, `XUSDT`, `X_USDT`, then the `1000X` variant); Bybit = first daily trade dump on public.bybit.com/trading (Bybit REST is geo-blocked here). A listing day that straddles T − 24 h is refined with 1h candles (Bybit: first trade).
- Status per notice × venue: **S** = first kline ≤ T − 24 h (same meaning as the HL/Aster `S` flag); D = in (T − 24 h, T + 1 h]; L = later; N = not found; S_delisted = S but the venue's last daily bar is before T + 9 d (not scoreable).
- Coin mapping: Upbit duplicate-ticker suffix stripped (GAME2→GAME, MET2→MET, UP2→UP, META2→META).
- **NEW event on venue V** = census notice with `f_HL != S` and `f_Aster != S`, status S on V, and no HL/Aster event of the same coin within ± 24 h. **OVERLAP event on V** = HL (2025-01-01 → 2026-10-15) or Aster-class event with status S on V.
- Report: NEW and OVERLAP counts per venue; union of NEW events; per-venue EU/Czechia access (fetched pages, [verify]).
- Known bias: OKX, Bitget and Gate APIs do not serve delisted contracts, so coins later delisted there are invisible (likely losers for a long → the missing events would tend to help the short; the bias is against E4). Bybit dumps keep delisted symbols.

## 2. Frozen E4 rule on NEW events, per venue (C2203–C2210) — K9 §1 rule, own code
- Entry: open of the first venue 1h candle with open ≥ T + 1 h; dropped (`no_entry`) if that candle opens more than 1 h after the first whole hour ≥ T + 1 h.
- Exit: close of the 1h candle with open = entry + 167 h (if missing, entry + 166 h; else `no_exit`).
- ret168 = exit close / entry open − 1. Funding: sum of the venue's funding prints with time in (entry + 0.5 h, entry + 168.5 h], short receives positive. Fewer than 10 prints → no N168 (`no_funding_cov`); the event still counts for the price-only excess (deviation from K9, where it was a full drop; needed because OKX REST serves only ~3 months of funding and Bybit's funding API is blocked).
- Cost (one round trip, bp of notional) = 21 + 2 × venue standard (VIP0) taker in bp, the formula that gives HL 30 / Aster 29: Bybit 5.5 → **32**, OKX 5.0 → **31**, Bitget 6.0 → **33**, Gate 5.0 → **31** [verify]. If today's fee page (checked before scoring) gives a different VIP0 taker, an amendment before scoring replaces the number.
- N168 = −ret168 × 10⁴ + funding × 10⁴ − cost.
- Placebo (K9 exactly, on 1h bars): every 4h-grid start s within ± 90 d of floor₄ₕ(entry), |s − any notice T of that coin (census + HL + Aster)| > 10 d, with 1h bars at s and s + 167 h; short return = −(close(s + 167 h) / open(s) − 1). Need ≥ 20 windows. **Excess = −ret168 × 10⁴ − placebo mean** (price only).
- Symbol check: an event is dropped (`symbol_mismatch`) if the venue's entry open differs by > 10 % from another of the four venues (or Aster/HL) at the same hour; with no second price it is kept and flagged.
- Ranges: ISO-week block bootstrap of the mean (2,000 resamples, seed 7, 2.5/97.5 %), as K9.
- Per venue cells: C2203 OKX, C2204 Bitget, C2205 Gate, C2206 Bybit — each: n, excess [range], N168 [range], funding mean, 2025 / 2026 split. Bybit: price from trade dumps; funding unavailable → excess only. If Bybit's NEW events are all also scoreable on another venue, Bybit gets counts only (no fetch of 180 days of trade dumps).
- **NEW-layer verdict (C2207, union of NEW events, one venue each)**: venue chosen per event by fixed priority among venues where it scores — Gate, Bitget, OKX, Bybit (full funding history first). SUPPORT if mean excess > 0 with range excluding 0 and n ≥ 20; NOT-ESTABLISHED if the range includes 0; KILL if mean excess ≤ 0.
- C2208: NEW-layer N168 (events with funding), funding mean, worst, loss-capped (−10,000) mean, trim-5 excess, top-5 share.
- C2209: overlap price agreement per venue vs reference (Aster 1h; HL 4h): per event correlation of returns over the hold, mean gap (venue close / reference close − 1, bp), and the difference in −ret168 (venue entry/exit on the venue's 1h grid vs the published reference gross). Reporting only, no verdict.
- C2210: today's depth for the last 10 NEW-event coins per venue (Bybit excluded: blocked): $ sellable with ≤ 29 bp one-way slippage vs mid (walking the bid side); hold-period quote volume per day (median, p25).

## 3. Pooled supply cell (C2211–C2214)
- Pooled = HL 126 (published N168) + Aster 65 (K9 N168) + NEW events with N168 (one venue each, §2 priority), notice T 2025-01-01 → 2026-10-15.
- **Verdict (C2211), newest slice 2026 (T 2026-01-01 → 2026-10-15) decides: PASS** if (1) pooled 2026 N168 mean > 0 with range excluding 0, AND (2) NEW-layer 2026 N168 mean > 0, AND (3) NEW-layer excess (all years) > 0. **NO-SUPPLY-GAIN** if (1) holds and (2) or (3) fails. **FAIL** if (1) fails.
- C2212: added events/month (NEW with N168, and NEW union with excess) 2025 / 2026; pooled events/month.
- C2213: capacity — NEW-event notional fillable at ≤ 29 bp one-way (C2210 median) vs HL/Aster.
- C2214 (only if PASS): money per $100 / $1k / $5k / $25k: E4 book as K10 (shared cap 3 open, slot = equity/3, 1×, booked at exit, N168 floored at −10,000 = slot lost), $/month on 2026 at 1× and scaled to $25 worst drawdown; $1k+ with NEW-event slots capped at the C2210 median capacity and HL/Aster at the NightA factors (0.94 / 0.97 / 0.56). Live third shown separately.

## 4. Variants counted
Per-venue cells 4 + NEW-layer 1 + N168 1 + pooled 1 = 7 counted; C2209/C2210/C2212–C2214 reporting.

## 5. What would make this wrong / kill it
- Ticker collisions (same ticker, different coin) → symbol check above.
- Survivorship (delisted contracts invisible on OKX/Bitget/Gate) → counted and stated.
- NEW-event coins are smaller and thinner than HL coins; today's books ≠ books at the event. Capacity is indicative.
- Kill: NEW-layer excess ≤ 0, or pooled 2026 N168 range through 0.

## 6. Prediction (written before data)
NEW events ~40–80 (mostly Bitget/Gate). Excess positive but smaller than Aster (+1,293) because many NEW coins are majors relisted on Upbit's KRW market; NEW-layer NOT-ESTABLISHED; pooled 2026 passes on HL alone.

## 7. Three standing questions — answered in RESULTS (whose money; competition; decay 2025 vs 2026).

## 8. Pre-freeze facts (not outcomes)
- Fee check (subagent, fetched today): VIP0 taker Bybit 0.055 % (secondary; Bybit pages blocked), OKX 0.05 %, Bitget 0.06 %, Gate 0.05 % (Gate API `taker_fee_rate` field says 0.075 %; Gate's fee announcement 43029 says 0.05 % for VIP0 USDT-M) → the cost table in §2 stands.
- Gate-run fixes before freezing (no returns involved): Bitget code 40309 ("symbol removed") = not found; Bitget daily candles come 90 per call (pagination fixed); OKX re-created instruments (e.g. ENA-USDT-SWAP starts 2025-09-17) only show the new instrument's history → earlier events count as not live on OKX.

sha256 (of the text above this line): bbf1424f4cd0f8513a35420edacd87036815a7353b33316ee2be466ad37f40b6 — frozen 11:39 Prague
