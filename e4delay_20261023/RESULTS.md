# RESULTS — e4delay_20261023 (session cce4d): E4 delayed entry on big notice pumps

_Backtest only. PREREG sha256 6748e406…29bd, AMENDMENTS 636436a6…a4c4 (blind Opus review: 0 must-fix, 5 should-fix,
all applied before scoring). Freeze commit 18a33a0 pushed before scoring. Ledger C2220–C2226 (`LEDGER_ROWS_cce4d_PENDING.csv`)._

## Verdict: NOT-ESTABLISHED (C2221); the ccB lead was mostly a selection artifact (C2222)
1. **Decider (C2221).** The rule: if the notice pump is already ≥ +20 % when E4 would enter (T+1h), wait and short
   after a ⅓ give-back. Paired against E4's short at T+1h on the same events, floored: **+215 bp [−218, +831], n 40
   gated events**. Without the single best event it is **−48**, trim-5 is **−202**, and without liquidations it is **−48**.
   That fails 4 of the 5 PASS conditions. Fee basis: Binance 20 bp round trip plus Binance funding, unhedged.
   Fires: 1.5 gated events/month in this slice.
2. **One event carries the result.** In 25 of 40 gated events the pump had already given back ⅓ before T+1h, so
   both entries are the same bar (Δ = 0). Of the other 15, 10 are worse than T+1h. The gain comes from LPT
   (2025-05-30): E4's T+1h short was liquidated at 1× (−10,000 bp), while the delayed short made +447.
3. **The timing does not beat random waiting (C2223).** Replacing each trigger with a random delay drawn from the other events'
   delays gives p50 +30 and p90 +241. The real +215 sits at the 87th percentile.
4. **ccB's comparison reproduces on unseen events, and the bias explains it (C2222).** Use events whose pump hits
   +20 % at any time in 7 days, then gives back ⅓. On those, delayed +523 vs E4 −285, Δ **+808 [+254, +1,447], n 56**,
   which is ccB's +817 almost exactly. But those events are picked by a pump that comes after E4's short is already
   on, so T+1h looks bad by construction. With the gate at entry time the edge disappears.
5. **The notice short itself still works on this unseen slice:** E4 T+1h floored +395 [−174, +939], n 88. Same-coin
   placebo excess on the gated events is +903 [+295, +1,509] for E4 and +906 for delayed. Both legs earn the same excess.

## Population
- D = A (40 E4 HL notices before 2025-01-01, ccB filtered these out; "HL notice, Binance proxy") ∪ B (60 Korean listing
  notices 2025-01 → 2026-10 on coins with a Binance perp but no HL/Aster perp, never scored by E4 or ccB).
- After dedupe 100 → no Binance perp ≥ 24 h before T 9 (all A: BRETT, GOAT, CHILLGUY, MOODENG …), censored 3
  (T+15 d after data end 10-22) → 88 scored; 40 gated (R ≥ +20 % by T+1h), all 40 triggered within 7 d.
- Bars: Binance USDT-M 1h (data.binance.vision); funding monthly files, no zero-filled trades in the scored set.

| row | cell | n | mean bp | 95 % range | ex-best | trim-5 |
|---|---|---|---|---|---|---|
| **C2221** | **Δ delayed − E4, gated, floored (decides)** | **40** | **+215** | **−218..+831** | **−48** | **−202** |
| C2221 | E4 leg / delayed leg (gated) | 40 / 40 | +315 / +529 | −503..+1,085 / −117..+1,144 | | |
| C2221 | Δ entries differ (delay > 0) / same bar | 15 / 25 | +573 / 0 | | | |
| C2221 | Δ ex-liquidation / ex-generic tickers / unfloored | 39 / 30 / 40 | −48 / +219 / +109 | −267..+199 / −334..+1,069 / −218..+506 | | |
| C2222 | S1 ccB-style any-time Δ (biased) | 56 | +808 | +254..+1,447 | +604 | +116 |
| C2223 | S2 random-delay placebo | 40 | real +215 | p50 +30, p90 +241 | 87th pct | |
| C2224 | S3 placebo excess E4 / delayed | 40 | +903 / +906 | +295..+1,509 / +299..+1,503 | | |
| C2225 | liquidations 1× / 2× | E4 1 / 5, delayed 0 / 4 | | | | |
| C2226 | Δ by year 2024 / 2025 / 2026 | 5 / 33 / 2 | −118 / +278 / 0 | | | |
| C2226 | Δ by sub-slice A / B | 5 / 35 | −118 / +262 | | | |
| C2226 | policy-level Δ per scored event | 88 | +98 | | | |

Money: not computed. The rule did not pass, so the PREREG gives no money line.

## Three standing questions
- **Whose money:** the same as E4's, Korean listing chasers. Waiting adds no new counterparty. It only changes when E4
  shorts the same buyers, and on most big pumps the move has already turned by T+1h.
- **Competition:** a fast first-hour round trip (25 of 40 gated pumps gave back ⅓ inside the first 1–2 h). Other traders
  fade these pumps within the hour, so a slow give-back trigger usually fires at E4's own bar.
- **Decay:** cannot be judged here. There are 2 gated events in 2026 (both Δ 0), and 2025 +278 rests on LPT.

## What would make this wrong
1. Binance is a proxy venue for the A events (HL notices). HL fills and funding would differ, and 9 A events had no
   Binance perp. A has only 5 gated events.
2. 1h bars: a 5-minute give-back trigger could separate the 25 same-bar entries. That would be a new PREREG, and it is
   exploratory, because the first-hour give-back is already faster than 1h.
3. Generic tickers (THE, RED, OPEN, HOME, LA, SUN, BOB, AVA, SHELL, B3, XAN) were not hand-checked for collisions.
   Excluding them gives +219 [−334, +1,069], the same reading.

## Proposal
Keep E4's T+1h entry. Close the delayed-entry lead (C1987) as a selection artifact. The one real effect is that waiting
avoided one liquidation in 40. That is a stop/size question for E4's tail, not an entry change.

Files: PREREG.md, AMENDMENTS.md, PREREG.sha256, RESULTS.md, LEDGER_ROWS_cce4d_PENDING.csv, events.csv, results.json,
scripts (fetch.py, score.py), data (a_hl_pre2025.csv, b_bnonly_2025_26.csv). Git branch claude/e4-delayed-entry-korean-7rarmm.
