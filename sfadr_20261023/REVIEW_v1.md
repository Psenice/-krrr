# Blind review v1 (one Opus subagent, 2026-10-23 ~11:50 Prague, before scoring; it computed no outcomes)
MUST-FIX: (1) FX Open = same-day Close in yfinance → look-ahead in H/prem/x2/x3; (2) stale zero-volume home holiday rows;
(3) dividends not adjusted (ex-date mismatch makes fake fade profit); (11) newest-slice verdict code missing, F2 = one family.
SHOULD-FIX: stale ADR/ETF opens sensitivity; concurrent opens in mSPY/mETF/F4 e (disclose); rolling windows on valid rows;
backward-only FX cleaning; NW lag for overlap; shared-permutation placebo; bootstrap blocks by trading day; F4 fit nights
excluded + |w| filter; reverse report years/NW/Driscoll-Kraay/FX Close(D).
Checked fine: signs, hold alignment, lags of ref/sd/bc, survivor rule, home close times precede the US open, costs.
All items applied in AMENDMENT_A1.md (sha256 daab2f79…ac20). The placebo built on the leaky FX was discarded (out/placebo_v1_LEAKYFX_DISCARDED.json).
