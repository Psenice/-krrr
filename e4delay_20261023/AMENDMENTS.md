# AMENDMENTS — applied after the blind Opus review, before any outcome was computed (prices fetched, not read)
A1 (censoring, should-fix 1): drops are event-level — if either leg lacks its full 168-bar hold, the event is dropped for
   both legs. Every gated event with T + 15 d after the data end is excluded up front ("censored").
A2 (ticker collisions, should-fix 2): generic tickers THE, RED, OPEN, HOME, LA, SUN, BOB, AVA, SHELL, B3, XAN are flagged;
   the decider is re-reported without them as a check. Binance perp must exist >= 24 h before T (already in PREREG).
   f_HL / f_Aster blank = no perp on that venue at the notice (CSV convention of korea_supply_events).
A3 (n realism, should-fix 3): stated in advance — NOT-ESTABLISHED is the likely outcome (few seasoned-perp coins pump
   +20 % within the first 1–2 h). The 2026 downgrade rule will rarely apply (few 2026 events in D).
A4 (floor, should-fix 4): PASS additionally requires trim-5 mean delta > 0 AND mean delta excluding events where either
   leg hit the 1x liquidation > 0.
A5 (venue, should-fix 5): sub-slice A is labelled "HL notice, Binance proxy"; drops for no Binance perp are counted.
A6 (notes): delta reported for triggered vs untriggered gated events separately; dedupe chains from the last KEPT event;
   bootstrap = resample ISO weeks with replacement, 2,000 draws, 2.5/97.5 percentiles of the mean; Oct-2026 funding
   zero-filled trades flagged; BTC 168 h move over each leg reported if BTC data available.
