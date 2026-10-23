# RESULTS — cce4v: E4 supply on more venues (e4venues_20261023)

_Claude Code cloud session cce4v, 2026-10-23, 11:07–12:30 Prague. PREREG sha256 bbf1424f…40b6 (frozen 11:39) + A1 (blind Opus review, 5 must-fix applied before scoring). Ledger C2200–C2214 → `LEDGER_ROWS_cce4v_PENDING.csv`. Every number is **backtest**. E4 = 7-day short after a Korean (Upbit/Bithumb) listing notice._

## Read this first
1. **New events per venue (C2200):** OKX 26, Bitget 57, Gate 75, Bybit 82. These are notices whose coin had no HL/Aster perp at T but had a USDT perp listed ≥ 24 h earlier on that venue. The union is **100 events / 78 coins** (2025: 81, 2026: 19). 20 events were on Bybit only.
2. **The new layer is NOT ESTABLISHED (C2207).** Excess vs a same-coin placebo is **+755 bp [−113, +1,523], n 71** (Gate 66, Bitget 4, OKX 1). N168 net is **+202 [−828, +1,128], n 67**. Funding costs −636 bp per event. Fees are each venue's VIP0 taker (OKX 31 / Bitget 33 / Gate 31 bp round trip).
3. **Pooled verdict (C2211): PASS by the frozen rule, but no money gain.** On 2026 the pooled N168 is **+749 [+197, +1,284], n 96**. HL+Aster alone is +874 [+273, +1,466], n 82. The new venues add 14 events in 2026 at **+21 bp [−2,084, +1,906]**. That passes condition 2 ("NEW 2026 mean > 0") by 21 bp. Money: $17.47 vs $17.43 per $100/month at 1×.
4. **Supply is shrinking.** New events with funding history fell from 4.4/month (2025) to 1.5/month (2026). Most new Korean listings now already have an Aster perp (G1 grew from 1.5/month in 2025 to 5/month in 2026), so they are no longer "new" here.
5. **EU/Czechia (C2202, [verify]):** Bybit and Gate are spot-only for EEA residents. OKX offers EU "X-Perps" (MiFID; 5-year-expiry perp-like contracts, appropriateness test). Bitget is unclear: it has no MiCA licence, and the CNB says unlicensed providers may not operate in Czechia after 2026-07-01. **Gate, which carries 66 of the 71 scored new events, is not reachable for perps from Czechia.**

## Step 1 — venue gate (C2200–C2202)
| venue | NEW | 2025 / 2026 | OVERLAP HL (of 126) | OVERLAP Aster (of 66) | notes |
|---|---|---|---|---|---|
| OKX | 26 | 19 / 7 | 83 | 34 | API hides delisted and re-created contracts (e.g. ENA swap starts 2025-09-17) |
| Bitget | 57 | 49 / 8 | 99 | 55 | delisted symbols = code 40309 (counted as absent) |
| Gate | 75 | 60 / 15 | 109 | 60 | 1h before ~2025-09 from download.gatedata.org dumps |
| Bybit | 82 | 72 / 10 | 116 | 53 | REST geo-blocked (CloudFront 403); listing from public trade dumps |
- Of the 161 notices with no HL/Aster perp at T, 100 had a perp ≥ 24 h earlier on at least one venue. 56 had none (19 listed within 24 h). 2 were dropped as within 24 h of an HL/Aster event of the same coin.
- Survivorship: OKX, Bitget and Gate do not serve delisted contracts. Coins delisted later are invisible; they probably fell, so the missing events would have helped the short. The bias works against E4.

## Step 2 — frozen E4 rule on new events (K9 rule, own code; ISO-week block bootstrap 2,000, seed 7)
| row | cell | n | mean | range | notes |
|---|---|---|---|---|---|
| C2203 | OKX excess | 26 | +468 | [−722, +1,501] | N168 n 4 only (OKX REST keeps 3 months of funding): +1,793 |
| C2204 | Bitget excess | 57 | **+959** | **[+149, +1,684]** | per-venue variant, not deciding; N168 n 6 (short funding history) |
| C2205 | Gate excess · N168 | 66 · 66 | +795 · +204 | [−84, +1,630] · [−772, +1,157] | funding −646; 9 no_entry |
| C2206 | Bybit-only, price only | 20 | +1,962 net of 32 bp, no funding | [+742, +2,897] | exploratory: no funding, no placebo (A1); 19 of 20 in 2025 |
| **C2207** | **NEW-layer excess (union)** | **71** | **+755** | **[−113, +1,523]** | **NOT-ESTABLISHED**; median +1,607; placebo mean +85; 2025 +782 (n 55), 2026 +663 (n 16) [−1,229, +2,404] |
| C2208 | NEW-layer N168 | 67 | +202 | [−828, +1,128] | capped −10,000: +324; worst −15,312 (FLOCK); 2025 +250 (n 53), **2026 +21 (n 14)**; trim-5 excess +445; top-5 share 0.45 |
- **Why Bitget passes and Gate does not:** on the 53 events listed on both, the two venues agree (ret168 correlation 1.00, median gap 19 bp; excess +997 Gate vs +958 Bitget). The 13 Gate-only events are worse. Bitget lists fewer, larger coins.
- **Symbol check:** no price mismatches. 35 events had no second venue to compare with (kept, flagged).
- **C2209 overlap agreement (reporting):** vs HL (4h closes over the hold), correlation median 0.999 on OKX, Bitget and Gate, mean gap −0.4 to −1.3 bp. vs Aster (1h), correlation 0.94–0.95, mean gap −3 to +14 bp, ret168 difference mean −27 to +21 bp (median |diff| 34–42 bp). The four venues price these coins the same as HL and Aster to within tens of bp.
- **C2210 depth today** (last 10 new-event coins per venue): $ sellable at ≤ 29 bp one-way is a median of **$43k on Bitget** (min $4.5k), **$21k on OKX** (min $2.8k) and **$2.3k on Gate** (MPLX, HNT: $0). One-way slippage at $500: 6 / 4 / 19 bp. Hold-period volume median: Gate $3.4M/day, Bitget $8.2M/day.

## Step 3 — pooled supply cell (newest slice 2026 decides)
| row | cell | value |
|---|---|---|
| **C2211** | pooled 2026 N168 | **+749 [+197, +1,284], n 96** (HL 35 at +1,243, Aster 47 at +599, NEW 14 at +21) → **PASS** by the frozen rule |
| | HL+Aster only 2026 | +874 [+273, +1,466], n 82 — adding the new venues lowers the 2026 mean |
| | pooled all years | +751 [+336, +1,144], n 258; 2025 +751 (n 162) |
| C2212 | events/month | NEW with N168: 4.42 (2025) → 1.48 (2026); any scored: 6.17 → 1.80; HL+Aster 9.08 → 8.67; pooled 13.50 → 10.15 |
| C2213 | capacity at 29 bp | new-event coins: median $13.6k, but Gate (the scoring venue for 66/71) $2.3k |
| C2214 | money 2026 (book: cap 3, slot = equity/3, 1×) | per $100: **$17.47/month** at 1× (worst DD $61) vs HL+Aster $17.43; at $25 DD **$7.15** vs $7.13. $1k: $165 vs $164. $5k: $850 vs $846. $25k: $2,651 vs $2,441. After the live third: $110 / $567 / $1,768 |
- The +$210/month at $25k is not edge: new-event slots were not haircut while HL/Aster run at the NightA factor 0.56. Gate's $2.3k median depth makes even that optimistic.
- Six new events moved +90 % against the short during the hold (1× isolated liquidation). The book floors losses at −100 % of the slot only at the exit, so it understates those losses.

## Verdict in plain words
Running E4 on Bybit, OKX, Bitget and Gate adds about 100 events since 2025. Their price edge points the right way (+755 bp vs placebo) but is not established. After crowded-short funding (−636 bp/event) the net is about +200 bp, and **zero in 2026 (+21, n 14)**. The pooled book passes only because HL and Aster carry it; the new layer adds no money. The scoring venue (Gate) is also both thin and closed to Czech retail for perps. **Do not add a new-venue sleeve to the E4 paper book.** The only open lead is Bitget (+959 [+149, +1,684] on 57 events, $43k depth). Its N168 can't be measured, because Bitget's funding history is short. It is also a per-venue variant, not the deciding cell, and its EU status is unclear.

## Three standing questions
- **Whose money:** Korean retail chasing the KRW listing pump, mirrored by offshore perp longs on Gate/Bitget. The short collects the fade but pays those longs carry (−636 bp/event, more than Aster's −550).
- **Competition:** strong. Shorts are crowded on these small coins (funding), and the 2026 net is about 0.
- **Decay:** yes, on two axes. The 2026 net is +21 vs +250 in 2025 (excess +663 vs +782, both ranges through 0). Supply is down: 4.4 → 1.5 events/month, as Aster lists new coins first.

## What would make this wrong
1. The census was transcribed without titles (325 rows; G1 count 66 and pooled 191 = +943 reproduce exactly).
2. Delisted contracts are invisible on OKX/Bitget/Gate; the bias is against the short.
3. Bybit has no placebo and no funding (trade dumps only), so its +1,962 price-only number is exploratory.
4. Bitget and OKX funding histories are short, so their N168 n is 6 and 4.
5. Books are today's, not at the event times.

## Blockers
- Bybit REST is geo-blocked from the cloud; only public trade dumps are reachable. There is no funding source, and placebo/overlap would need over 10 GB.
- OKX funding REST keeps about 3 months; I found no public history dump.
- Bitget's funding API returned too little history for most 2025 events. The cause is not yet traced.
- EU access is from fetched pages and secondary sources: [verify] by Michael in a browser from Czechia.

## Files
`PREREG.md`, `AMENDMENTS.md`, `scripts/{venues,gate,gate_counts,score,prefetch,depth,pooled}.py`, `data/` (transcribed inputs), `out/{gate_events,listings,new_scored,new_union,overlap_agreement,depth_books}.csv`, `out/report_step{1,2,3}.txt`, `out/report_depth.txt`, `LEDGER_ROWS_cce4v_PENDING.csv`, `HANDOFF_cce4v.md`.
