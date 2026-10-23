# PREREG — e4delay_20261023 (session cce4d): E4 delayed entry on big notice pumps

Frozen 2026-10-23 before any price outcome is fetched or seen. Backtest only. Ledger C2220–C2239.
Lead (exploratory, found after looking): ccB C1987 — on ccB's 102 Korean-notice events with a ≥ +20 % pump that
gave back ⅓, the after-peak short earned +817 bp vs +347 for E4's own short at T+1h (2026 +456 vs +218).
Those 102 events (E4 HL notices ≥ 2025-01-01 from e4x_rebuild_events.csv + E4 Aster notices from events_g1.csv)
are the known in-sample. They do not decide.

## 1. Why the rule must be gated at E4's entry time (design point, stated before data)
ccB compared the two entries on events selected by a pump that is only known AFTER E4's T+1h entry. That
comparison is biased against T+1h by construction (it keeps events where price rose after the T+1h short).
An entry change can only use what is known at E4's entry decision. So the ONE version tested here is:
"at E4's entry time, if the notice pump is already ≥ +20 %, do not short yet; short after a ⅓ give-back instead."
ccB's after-the-fact comparison is re-run on the deciding slice as a labeled, non-deciding secondary (S1).

## 2. Deciding slice (events ccB did NOT use)
D = A ∪ B, then one event per coin per 7 days (keep the earliest):
- A: the 40 E4 HL notice events dated before 2025-01-01 in `e4x_rebuild_events.csv` (2024-07-09 → 2024-12-24);
  ccB filtered to T ≥ 2025-01-01. File `data/a_hl_pre2025.csv`.
- B: Korean listing notices in `korea_supply_events.csv` (2025-01 → 2026-10) whose coin had a Binance USDT-M perp
  before the notice (f_BinanceFut = S), no HL perp (f_HL ≠ S), no Aster perp (f_Aster ≠ S), and not in events_g1.
  These coins are outside E4's HL/Aster universe, so neither E4 nor ccB ever scored them. 60 rows,
  file `data/b_bnonly_2025_26.csv` (built by hand from the CSV flags, listed in full).
Venue for ALL of D: Binance USDT-M perp, 1h klines + funding from data.binance.vision (one uniform venue;
HL 1h history does not reach 2024 and HL 4h does not reach July 2024). Symbol = COIN+USDT, else 1000COIN+USDT
(k-prefixed HL names lose the k). Perp must have a 1h bar ≥ 24 h before T, else drop "no perp".
The < +20 % pumps are not a decider: the rule does not change them (Δ = 0 by construction); they are counted.

## 3. Rules (one version, no variants)
Bars: 1h; b0 = bar containing T; p0 = open(b0).
- E4 baseline (T+1h): entry at the open of the first bar with open time ≥ T + 1h (et_E4). Short, hold 168 bars,
  exit at the close of the 168th bar. Missing bars inside the hold → drop "no exit".
- Gate (known at et_E4): R = max(high of bars b0 … the bar before et_E4) / p0 − 1. Gated if R ≥ +20 %.
- Delayed entry (gated events only): running peak P starts at high(b0); for each bar t > b0 with t + 1h ≤ T + 7 d:
  P = max(P, high_t); trigger at the first t with P ≥ 1.2·p0 and close_t ≤ P − (P − p0)/3. Entry at the open of
  bar t + 1h; same 168-bar hold and exit as E4. No trigger within 7 days → no trade, net 0.
- Net bp = −(exit/entry − 1)·1e4 + funding received by the short over the hold − 20 bp (Binance taker RT incl.
  slippage allowance, as ccB). Floored: −10,000 bp if max high over the hold ≥ entry × 1.90 (1× liquidation).
  Liquidation counts at 1× (max high ≥ +90 %) and 2× (≥ +45 %) on 1h highs, for both legs.
- Funding not yet published (Oct 2026 monthly file) → 0 and flagged.

## 4. Decider (C2221)
Paired difference Δ = floored net(delayed) − floored net(E4 T+1h), over gated events in D (untriggered → delayed 0).
Range: ISO-week block bootstrap 95 %, 2,000 draws (ccB's event_boot logic re-implemented).
- PASS (keep as an E4 entry change, still a proposal): n_gated ≥ 20 AND mean Δ > 0 AND lower range > 0 AND mean Δ
  without the single best event > 0.
- KILL: n_gated ≥ 20 and mean Δ ≤ 0.
- NOT-ESTABLISHED: anything else (including n_gated < 20).
Newest sub-slice (2026 events in D) reported; if n ≥ 5 and mean Δ ≤ 0, PASS is downgraded to NOT-ESTABLISHED.

## 5. Checks (reported, do not decide)
- S1 (C2222): ccB's after-the-fact comparison on D — events whose pump reaches ≥ +20 % at ANY time and trigger
  within 7 d (ccB's loop exactly, peak from b0), delayed vs E4 T+1h on those events. Labeled biased.
- S2 (C2223): random-delay placebo — for gated triggered events, replace the trigger entry by et_E4 + a delay drawn
  from the other gated events' delays (1,000 draws); report the percentile of the real mean Δ.
- S3 (C2224): same-coin placebo — mean gross short return over 168 h at 4h-grid times within ±90 d of the entry,
  excluding ±10 d around any event of that coin (≥ 20 placebo times). Excess = gross − placebo, both legs.
- S4 (C2225): liquidations 1×/2× both legs; worst event; unfloored Δ.
- S5 (C2226): by year (2024 / 2025 / 2026) and by sub-slice A / B; policy-level mean (Δ summed / all events in D);
  fires/month of gated events.
- S6: trim-5 of Δ (drop the 5 best).
Money ($100/$1k/$5k/$25k) only if PASS.
Variants counted: 1 decider + S1 + S2 = 3 rule evaluations.
