# SCRIPTS — sfadr_20261023 (run: python3 -I scripts/<x>.py data out <mode>)

## scripts/delay.py
```python
# C2169 execution-delay cell per AMENDMENT_A2. Usage: python delay.py DATADIR OUTDIR WINDOW (pre | holdout)
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import engine as E
DATA, OUT, WIN = sys.argv[1], sys.argv[2], sys.argv[3]
panels = E.build(DATA)
CELLS = {"A_F1_k1.5": ("x1", 1.5), "B_F2SPY_k1.0": ("x2SPY", 1.0)}
res = []
for iv, lab in (("1h", "D60"), ("5m", "D5")):
    if WIN == "pre" and iv == "5m": continue
    for cn, (sig, k) in CELLS.items():
        rows = []
        for pr, p in panels.items():
            raw = pd.read_csv(os.path.join(DATA, pr + ".csv"), index_col=0, parse_dates=True)
            raw.index = raw.index.normalize()
            ib = pd.read_csv(os.path.join(DATA, "intraday", f"{pr}_{iv}.csv"), index_col=0, parse_dates=True)
            first = ib[ib.index.time == pd.Timestamp("09:30").time()]
            ent = pd.Series(first.Close.values, index=first.index.normalize())
            x = p[sig]; z = E.zs(x)
            fire = (z.abs() >= k) & x.notna()
            d = fire[fire].index
            d = d[d.isin(ent.index) & d.isin(raw.index)]
            if WIN == "pre": d = d[(d >= "2024-10-24") & (d <= "2025-12-31")]
            else: d = d[d.year == 2026]
            s = -np.sign(x[d])
            o, c, e = np.log(raw.Open[d]), np.log(raw.Close[d]), np.log(ent[d])
            rows.append(pd.DataFrame({"date": d, "pair": pr, "h0": (s * (c - o)).values - 5e-4,
                                      "dl": (s * (c - e)).values - 5e-4, "pre": (s * (e - o)).values}))
        tr = pd.concat(rows)
        for col in ("h0", "dl"):
            t2 = tr.rename(columns={col: "net"})[["date", "pair", "net"]]
            lo, hi = E.block_ci(t2)
            res.append(dict(window=WIN, delay=lab, cell=cn, leg=col, n=len(tr), net=t2.net.mean() * 1e4, lo=lo, hi=hi,
                            pairs_pos=(t2.groupby("pair").net.mean() > 0).mean()))
        g = tr.h0.mean() + 5e-4
        res.append(dict(window=WIN, delay=lab, cell=cn, leg="share_of_H0_gross_before_entry", n=len(tr),
                        net=(tr.pre.mean() / g) if g else np.nan))
df = pd.DataFrame(res); print(df.round(2).to_string())
df.to_csv(os.path.join(OUT, f"DELAY_v1_{WIN}.csv"), index=False)
```

## scripts/download.py
```python
# download yfinance daily OHLC (unadjusted for splits only = yfinance auto_adjust=False) for all legs
import yfinance as yf, pandas as pd, time, sys, os
OUT = sys.argv[1]
PAIRS = [("TSM","2330.TW"),("BABA","9988.HK"),("JD","9618.HK"),("BIDU","9888.HK"),("NTES","9999.HK"),
 ("SONY","6758.T"),("TM","7203.T"),("HMC","7267.T"),("MUFG","8306.T"),("SMFG","8316.T"),
 ("INFY","INFY.NS"),("HDB","HDFCBANK.NS"),("IBN","ICICIBANK.NS"),("KB","105560.KS"),("SHG","055550.KS"),("PKX","005490.KS")]
EXTRA = ["TWD=X","HKD=X","JPY=X","INR=X","KRW=X","SPY","EWJ","EWY","FXI","EWT","INDA"]
tick = [a for a,_ in PAIRS]+[h for _,h in PAIRS]+EXTRA
for t in tick:
    fn = os.path.join(OUT, t.replace("=","_")+".csv")
    if os.path.exists(fn): continue
    for k in range(5):
        try:
            df = yf.Ticker(t).history(start="2011-06-01", end="2026-10-23", interval="1d", auto_adjust=False, actions=True)
            if len(df) > 100: break
        except Exception as e: print(t, e)
        time.sleep(3*(k+1))
    df.index = df.index.tz_localize(None).normalize()
    df.to_csv(fn); print(t, len(df), df.index.min().date(), df.index.max().date()); time.sleep(1)
```

## scripts/engine.py
```python
# sfadr engine: builds per-pair panels and scores cells per PREREG.md (sha256 45b1f79b...)
import numpy as np, pandas as pd, os

PAIRS = [("TSM","2330.TW","TWD=X","EWT"),("BABA","9988.HK","HKD=X","FXI"),("JD","9618.HK","HKD=X","FXI"),
 ("BIDU","9888.HK","HKD=X","FXI"),("NTES","9999.HK","HKD=X","FXI"),("SONY","6758.T","JPY=X","EWJ"),
 ("TM","7203.T","JPY=X","EWJ"),("HMC","7267.T","JPY=X","EWJ"),("MUFG","8306.T","JPY=X","EWJ"),
 ("SMFG","8316.T","JPY=X","EWJ"),("INFY","INFY.NS","INR=X","INDA"),("HDB","HDFCBANK.NS","INR=X","INDA"),
 ("IBN","ICICIBANK.NS","INR=X","INDA"),("KB","105560.KS","KRW=X","EWY"),("SHG","055550.KS","KRW=X","EWY"),
 ("PKX","005490.KS","KRW=X","EWY")]
COST_BP = 5.0; BORROW_YR = 0.005
HOLDS = {"H0": 0, "H1": 1, "H5": 5}
KS = [1.0, 1.5, 2.0, 2.5]

def load(d, t, home=False, fx=False):
    df = pd.read_csv(os.path.join(d, t.replace("=", "_") + ".csv"), index_col=0, parse_dates=True)
    df = df[~df.index.duplicated(keep="last")]
    if home:  # A1-2: drop stale holiday rows
        df = df[df.Volume.fillna(0) > 0]
    if not fx:  # A1-3: total-return scaling
        f = df["Adj Close"] / df["Close"]
        df["Open"] = df.Open * f; df["Close"] = df.Close * f
    df = df[["Open", "High", "Low", "Close", "Volume"]]
    df[["Open", "Close"]] = df[["Open", "Close"]].replace(0, np.nan)
    return df

def roll_sd_lag(x, n=250, mn=60):
    return x.rolling(n, min_periods=mn).std().shift(1)

def roll_beta_lag(y, x, n=250, mn=60):
    # OLS slope + intercept of y on x over previous n valid obs (both valid), lagged one valid obs (A1-5)
    m = y.notna() & x.notna()
    a, b = _rb(y[m], x[m], n, mn)
    return a.reindex(y.index), b.reindex(y.index)

def _rb(yy, xx, n, mn):
    mx = xx.rolling(n, min_periods=mn).mean(); my = yy.rolling(n, min_periods=mn).mean()
    cov = (xx * yy).rolling(n, min_periods=mn).mean() - mx * my
    var = (xx * xx).rolling(n, min_periods=mn).mean() - mx * mx
    b = cov / var; a = my - b * mx
    return a.shift(1), b.shift(1)

def clean_fx(fx):
    # A1-1: backward-only median of D-4..D-1
    lf = np.log(fx)
    nb = pd.concat([lf.shift(k) for k in (1, 2, 3, 4)], axis=1).median(axis=1)
    return fx.where((lf - nb).abs() <= 0.03)

def build(datadir):
    global CAL
    spy = load(datadir, "SPY")
    CAL = spy.index
    out = {}
    for adr, home, fxt, etf in PAIRS:
        A = load(datadir, adr); Hm = load(datadir, home, home=True); FX = load(datadir, fxt, fx=True); E = load(datadir, etf)
        idx = spy.index
        A = A.reindex(idx)
        p = pd.DataFrame(index=idx)
        p["Ao"], p["Ac"] = np.log(A.Open), np.log(A.Close)
        p["Avol"] = A.Close * A.Volume
        fxc = clean_fx(FX.Close.dropna())
        fx = fxc.shift(1).reindex(idx)          # A1-1: previous FX bar's Close
        fx_now = fxc.reindex(idx)               # FX Close(D): after the US close, reverse report only
        hc = Hm.Close.reindex(idx); ho = Hm.Open.reindex(idx)
        p["H"] = np.log(hc) - np.log(fx)
        raw = p.Ac - p.H
        p["ref"] = raw.rolling(20, min_periods=10).median().shift(1)
        prem = p.Ao - p.H - p.ref
        prem = prem.where(prem.abs() <= 0.15)
        p["prem"] = prem
        p["Eo"], p["Ec"] = np.log(E.Open.reindex(idx)), np.log(E.Close.reindex(idx))
        p["So"], p["Sc"] = np.log(spy.Open.reindex(idx)), np.log(spy.Close.reindex(idx))
        p["mSPY"] = p.So - p.Sc.shift(1)
        p["mETF"] = p.Eo - p.Ec.shift(1)
        # hedge beta: ADR on ETF close-to-close, rolling 250, lagged
        _, bc = roll_beta_lag(p.Ac.diff(), p.Ec.diff(), 250, 60)
        p["bc"] = bc.ffill()
        # signals
        p["x1"] = prem
        for nm, m in (("SPY", p.mSPY), ("ETF", p.mETF)):
            a2, b2 = roll_beta_lag(prem, m, 250, 60)
            p["x2" + nm] = prem - (a2 + b2 * m)
        x3 = p.H + p.ref - p.Ac.shift(1)
        p["x3"] = x3.where(prem.notna())
        # hold returns from ADR open
        for h, k in HOLDS.items():
            p["r" + h] = p.Ac.shift(-k) - p.Ao
            p["e" + h] = p.Ec.shift(-k) - p.Eo
        # reverse-report fields (home next bar after D)
        hm = pd.DataFrame({"ho": np.log(Hm.Open), "hc": np.log(Hm.Close)}).dropna()
        hm["g_next"] = hm.ho.shift(-1) - hm.hc
        hm["oc_next"] = hm.hc.shift(-1) - hm.ho.shift(-1)
        p["r_rev"] = (p.Ac - (np.log(hc) - np.log(fx_now)) - p.ref).where(prem.notna())
        p["Ao_stale"] = (A.Open - A.Close.shift(1)).abs().reindex(idx) < 1e-9
        p["Eo_stale"] = (E.Open - E.Close.shift(1)).abs().reindex(idx) < 1e-9
        p["g_next"] = hm.g_next.reindex(idx); p["oc_next"] = hm.oc_next.reindex(idx)
        p["pair"] = adr
        out[adr] = p
    return out

def zs(x):
    return x / roll_sd_lag(x.dropna()).reindex(x.index)

def trades(panels, sig, k, hold, hedge, side, xover=None):
    """Return DataFrame of trades: date, pair, net (fraction). sig = column name; side = -1 fade, +1 continue.
    xover: optional dict pair -> replacement signal series (placebo)."""
    rows = []
    for pr, p in panels.items():
        x = p[sig] if xover is None else xover[pr]
        z = zs(x) if xover is None else xover[pr + "_z"]
        fire = z.abs() >= k
        r = p["r" + hold]; e = p["e" + hold]
        s = side * np.sign(x)
        if hedge == "hdg":
            b = p.bc
            g = s * (r - b * e); cost = COST_BP * (1 + b.abs()) / 1e4
        else:
            g = s * r; b = pd.Series(0.0, index=p.index); cost = pd.Series(COST_BP / 1e4, index=p.index)
        nights = HOLDS[hold]
        # short leg notional: ADR if s<0, else hedge leg |b|
        short_not = np.where(s < 0, 1.0, b.abs())
        borrow = BORROW_YR * nights / 252 * short_not
        net = g - cost - borrow
        ok = fire & net.notna()
        rows.append(pd.DataFrame({"date": p.index[ok], "pair": pr, "net": net[ok].values}))
    return pd.concat(rows, ignore_index=True) if rows else pd.DataFrame(columns=["date", "pair", "net"])

def nw_t(series, lag):
    x = np.asarray(series, float); n = len(x)
    if n < 20: return np.nan
    m = x.mean(); u = x - m
    v = (u @ u) / n
    for L in range(1, lag + 1):
        w = 1 - L / (lag + 1); v += 2 * w * (u[L:] @ u[:-L]) / n
    return m / np.sqrt(v / n) if v > 0 else np.nan

def cell_t(tr, lag):
    if len(tr) < 20: return np.nan
    d = tr.groupby("date").net.mean().sort_index()
    return nw_t(d.values, lag)

CAL = None  # set to the US trading-day index by build()
def block_ci(tr, block=30, B=2000, seed=0):
    if len(tr) < 5: return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    pos = pd.Series(np.arange(len(CAL)), index=CAL)
    tr = tr.assign(b=pos.reindex(tr.date).values // block)
    g = tr.groupby("b").net.agg(["sum", "count"])
    s, c = g["sum"].values, g["count"].values; nb = len(s)
    idx = rng.integers(0, nb, size=(B, nb))
    means = s[idx].sum(1) / c[idx].sum(1)
    return tuple(np.percentile(means, [2.5, 97.5]) * 1e4)

def summarize(tr, lag, years):
    n = len(tr)
    if n == 0: return dict(n=0)
    net = tr.net.mean() * 1e4
    lo, hi = block_ci(tr)
    pp = tr.groupby("pair").net.agg(["mean", "count"])
    elig = pp[pp["count"] >= 10]
    share_pos = (elig["mean"] > 0).mean() if len(elig) else np.nan
    tot = tr.net.sum()
    maxshare = (tr.groupby("pair").net.sum().max() / tot) if tot > 0 else np.nan
    d = tr.groupby("date").net.sum().sort_values()
    trim = (tr[~tr.date.isin(d.index[-5:])].net.mean() * 1e4) if len(d) > 5 else np.nan
    return dict(n=n, net=net, lo=lo, hi=hi, t=cell_t(tr, lag), share_pos=share_pos,
                per_yr=n / years, per_mo=n / years / 12, maxshare=maxshare, trim5=trim)
```

## scripts/f4_rev.py
```python
# F4 (C213 sign rule ported, frozen) + reverse report. Usage: python f4_rev.py DATADIR OUTDIR MODE (f4 | rev | hold)
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import engine as E

DATA, OUT, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
panels = E.build(DATA)
SL = {"disc": (2012, 2021), "mid": (2022, 2023), "new": (2024, 2025), "hold": (2026, 2026)}
YEARS = {"disc": 10.0, "mid": 2.0, "new": 2.0, "hold": 9.7 / 12}
ALLOW_HOLD = MODE == "hold"

def f4_trades(hold):
    rows, betas = [], {}
    for pr, p in panels.items():
        w = p.Ao - p.Ac.shift(1); e = p.Eo - p.Ec.shift(1)
        ok = w.notna() & e.notna() & (w.abs() <= 0.15)   # A1-10: bad-print filter; F4 needs no home bar
        first = ok[ok].index[:30]
        ok = ok & (p.index > first[-1])                   # A1-10: beta-fit nights not traded
        b = np.polyfit(e[first].values, w[first].values, 1)[0]; betas[pr] = b
        d = w - b * e
        s = -np.sign(d)
        g = s * (p["r" + hold] - b * p["e" + hold])
        nights = E.HOLDS[hold]
        short_not = np.where(s < 0, 1.0, abs(b))
        net = g - E.COST_BP * (1 + abs(b)) / 1e4 - E.BORROW_YR * nights / 252 * short_not
        fire = (d.abs() >= 0.005) & net.notna() & ok
        rows.append(pd.DataFrame({"date": p.index[fire], "pair": pr, "net": net[fire].values,
                                  "gross": g[fire].values, "side": s[fire].values}))
    return pd.concat(rows, ignore_index=True), betas

def sl(tr, k):
    a, b = SL[k]; y = tr.date.dt.year
    return tr[(y >= a) & (y <= b)]

if MODE in ("f4", "hold"):
    res = {}
    for hold in E.HOLDS:
        tr, betas = f4_trades(hold)
        res[hold] = {}
        slices = ["disc", "mid", "new"] + (["hold"] if ALLOW_HOLD else [])
        for k in slices:
            s = E.summarize(sl(tr, k), E.HOLDS[hold], YEARS[k]); res[hold][k] = s
            print(hold, k, {kk: round(float(v), 2) for kk, v in s.items()})
        trn = sl(tr, "new")
        # random-sign placebo on newest
        rng = np.random.default_rng(1)
        obs = trn.net.mean(); cst = (trn.gross - trn.net).values
        flips = np.array([(trn.gross.values * rng.choice([-1, 1], len(trn)) - cst).mean() for _ in range(1000)])
        res[hold]["randsign_share_ge_obs"] = float((flips >= obs).mean())
        print(hold, "random-sign share >= obs", res[hold]["randsign_share_ge_obs"])
        yrs = tr[tr.date.dt.year <= (2026 if ALLOW_HOLD else 2025)].groupby(tr.date.dt.year).net.agg(["count", "mean"])
        yrs["mean"] *= 1e4; print(yrs.round(1).T.to_string())
        pp = trn.groupby("pair").net.agg(["count", "mean"]); pp["mean"] *= 1e4
        print("newest per pair", pp.round(1).T.to_string())
        sd = trn.groupby("side").net.agg(["count", "mean"]); sd["mean"] *= 1e4; print("newest by side", sd.round(1).to_dict())
        res[hold]["betas"] = betas
    json.dump(res, open(os.path.join(OUT, "F4_v2%s.json" % ("_holdout" if ALLOW_HOLD else "")), "w"), default=float, indent=1)

if MODE == "rev":
    rows = []
    allx = []
    for pr, p in panels.items():
        q = p[p.index.year <= 2025][["r_rev", "g_next", "oc_next"]].dropna()
        q = q[(q.g_next.abs() < 0.2) & (q.oc_next.abs() < 0.2)]
        allx.append(q.assign(pair=pr))
        for ycol in ("g_next", "oc_next"):
            x, y = q.r_rev.values, q[ycol].values
            b = np.polyfit(x, y, 1)[0]; u = y - y.mean() - b * (x - x.mean())
            xu = (x - x.mean()) * u
            S = xu @ xu + 2 * 0.5 * (xu[1:] @ xu[:-1])     # NW lag 1 (A1-11)
            se = np.sqrt(S) / ((x - x.mean()) @ (x - x.mean()))
            r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
            rows.append(dict(pair=pr, y=ycol, n=len(x), slope=b, t=b / se, r2=r2))
    df = pd.DataFrame(rows)
    A = pd.concat(allx)
    for ycol in ("g_next", "oc_next"):
        x, y = A.r_rev.values, A[ycol].values
        b = np.polyfit(x, y, 1)[0]
        # date-clustered t: aggregate per date
        u = y - y.mean() - b * (x - x.mean())
        g = pd.DataFrame({"d": A.index, "xu": (x - x.mean()) * u}).groupby("d").xu.sum().values
        S = g @ g + 2 * 0.5 * (g[1:] @ g[:-1])            # Driscoll-Kraay, NW lag 1 on per-date sums
        se = np.sqrt(S) / ((x - x.mean()) @ (x - x.mean()))
        r2 = 1 - (u @ u) / ((y - y.mean()) @ (y - y.mean()))
        print("POOLED", ycol, "n", len(x), "slope %.3f t(date-clustered) %.1f R2 %.3f" % (b, b / se, r2))
    print(df.round(3).to_string())
    df.to_csv(os.path.join(OUT, "REVERSE_v2.csv"), index=False)
```

## scripts/grid.py
```python
# grid + placebo (numpy fast path). Usage: python grid.py DATADIR OUTDIR MODE   (MODE = check | placebo | score)
import sys, os, json, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import engine as E

DATA, OUT, MODE = sys.argv[1], sys.argv[2], sys.argv[3]
panels = E.build(DATA)
pairs = list(panels)
idx = panels[pairs[0]].index
for p in panels.values(): assert p.index.equals(idx)
T, P = len(idx), len(pairs)
yr = idx.year.values
SL = {"disc": (yr >= 2012) & (yr <= 2021), "mid": (yr >= 2022) & (yr <= 2023),
      "new": (yr >= 2024) & (yr <= 2025), "hold": (yr == 2026)}
YEARS = {"disc": 10.0, "mid": 2.0, "new": 2.0, "hold": 9.7 / 12}

def M(col): return np.column_stack([panels[p][col].values for p in pairs])  # T x P

SIGS = {"F1": "x1", "F2SPY": "x2SPY", "F2ETF": "x2ETF", "F3": "x3"}
X = {k: M(v) for k, v in SIGS.items()}
R = {h: M("r" + h) for h in E.HOLDS}; Ee = {h: M("e" + h) for h in E.HOLDS}
BC = M("bc")

def zmat(x):
    z = np.full_like(x, np.nan)
    for j in range(x.shape[1]):
        s = pd.Series(x[:, j]); v = s.dropna()
        z[v.index, j] = (v / v.rolling(250, min_periods=60).std().shift(1)).values
    return z

def cells():
    out = []
    for fam, sides in (("F1", [-1]), ("F2SPY", [-1, 1]), ("F2ETF", [-1, 1]), ("F3", [1])):
        for side in sides:
            for k in E.KS:
                for h in E.HOLDS:
                    for hed in ("raw", "hdg"):
                        out.append((fam, side, k, h, hed))
    return out
CELLS = cells(); assert len(CELLS) == 144

# precompute per (hold, hedge): gross for side=+1, cost, borrow for long / short
PRE = {}
for h, nights in E.HOLDS.items():
    for hed in ("raw", "hdg"):
        if hed == "hdg":
            G = R[h] - BC * Ee[h]; cost = E.COST_BP * (1 + np.abs(BC)) / 1e4; bl = np.abs(BC); bs = np.ones_like(BC)
        else:
            G = R[h]; cost = np.full_like(G, E.COST_BP / 1e4); bl = np.zeros_like(G); bs = np.ones_like(G)
        f = E.BORROW_YR * nights / 252
        PRE[(h, hed)] = (G, cost, bl * f, bs * f)

def cell_trades(x, z, fam, side, k, h, hed, mask):
    G, cost, bl, bs = PRE[(h, hed)]
    s = side * np.sign(x)
    net = s * G - cost - np.where(s > 0, bl, bs)
    fire = (np.abs(z) >= k) & np.isfinite(net) & mask[:, None]
    return fire, net

def fast_t(fire, net, lag):
    cnt = fire.sum(1); tot = np.where(fire, net, 0).sum(1)
    d = tot[cnt > 0] / cnt[cnt > 0]
    return E.nw_t(d, lag), int(fire.sum())

def to_df(fire, net):
    ti, pj = np.nonzero(fire)
    return pd.DataFrame({"date": idx[ti], "pair": np.array(pairs)[pj], "net": net[ti, pj]})

Z = {k: zmat(v) for k, v in X.items()}

if MODE == "check":
    # data sanity only: no returns of any cell printed
    for p in pairs:
        q = panels[p]
        v = q.prem.notna()
        print(p, "valid prem days", int(v.sum()), "first", q.index[v][0].date(), "prem sd bp %.0f" % (q.prem.std() * 1e4),
              "ref jumps>5%", int((q.ref.diff().abs() > 0.05).sum()), "fx NaN", int(q.H.isna().sum()))
    sys.exit()

if MODE == "placebo":
    rng = np.random.default_rng(12345)
    NR = int(sys.argv[4]) if len(sys.argv) > 4 else 200
    KIND = sys.argv[5] if len(sys.argv) > 5 else "indep"
    disc = SL["disc"]; res = []
    dpos = np.where(disc)[0]
    for run in range(NR):
        Xs, Zs = {}, {}
        perm = dpos[rng.permutation(len(dpos))]  # shared date permutation (A1-7)
        for fam, x in X.items():
            xs = x.copy()
            if KIND == "shared":
                xs[dpos, :] = x[perm, :]
            else:
                for j in range(P):
                    ok = np.where(disc & np.isfinite(x[:, j]))[0]
                    xs[ok, j] = x[rng.permutation(ok), j]
            Xs[fam] = xs; Zs[fam] = zmat(xs)
        best = -np.inf
        for (fam, side, k, h, hed) in CELLS:
            fire, net = cell_trades(Xs[fam], Zs[fam], fam, side, k, h, hed, disc)
            t, n = fast_t(fire, net, E.HOLDS[h])
            if np.isfinite(t): best = max(best, t)
        res.append(best)
        if run % 20 == 0: print(run, best, flush=True)
    res = np.array(res)
    json.dump({"maxt": res.tolist(), "bar95": float(np.percentile(res, 95))}, open(os.path.join(OUT, "placebo_v2_%s.json" % KIND), "w"))
    print("BAR95", np.percentile(res, 95)); sys.exit()

if MODE == "controls":
    disc = SL["disc"]
    # look-ahead: F1 using Close(D) premium, traded open->close (must be huge)
    xl = M("r_rev"); zl = zmat(xl)
    fire, net = cell_trades(xl, zl, "LA", 1, 1.0, "H0", "raw", disc)
    print("lookahead t (continue close-based premium, H0):", fast_t(fire, net, 0))
    rng = np.random.default_rng(7)
    ts = []
    for r in range(20):
        xr = rng.standard_normal(X["F1"].shape) * np.where(np.isfinite(X["F1"]), 1, np.nan)
        zr = zmat(xr)
        fire, net = cell_trades(xr, zr, "RND", -1, 1.0, "H0", "raw", disc)
        ts.append(fast_t(fire, net, 0)[0])
    print("random-signal |t| max over 20:", np.nanmax(np.abs(ts)), "mean", np.nanmean(ts))
    sys.exit()

if MODE == "score":
    bars = [json.load(open(os.path.join(OUT, "placebo_v2_%s.json" % kd)))["bar95"] for kd in ("indep", "shared")]
    bar = max(bars); print("bars indep/shared", bars)
    STALE = M("Ao_stale").astype(bool) | M("Eo_stale").astype(bool)
    rows = []
    for c in CELLS:
        fam, side, k, h, hed = c
        row = dict(fam=fam, side=side, k=k, hold=h, hedge=hed)
        for sl in ("disc", "mid", "new"):
            fire, net = cell_trades(X[fam], Z[fam], fam, side, k, h, hed, SL[sl])
            s = E.summarize(to_df(fire, net), E.HOLDS[h], YEARS[sl])
            for kk, vv in s.items(): row[f"{sl}_{kk}"] = vv
        rows.append(row)
    df = pd.DataFrame(rows)
    df["surv"] = (df.disc_t >= bar) & (df.disc_net > 0) & (df.disc_share_pos >= 0.6) & (df.disc_per_yr >= 50)
    df["F"] = df.fam.str[:2]
    def verdict(r):
        if not r.new_n or r.new_n == 0 or not np.isfinite(r.new_net): return "NO-TRADES"
        if r.new_net <= 0: return "KILL"
        if r.new_lo <= 0: return "NOT-EST"
        nb = df[(df.fam == r.fam) & (df.side == r.side) & (df.hold == r.hold) & (df.hedge == r.hedge) & ((df.k - r.k).abs() == 0.5)]
        ok = (r.new_trim5 > 0) and (r.new_maxshare <= 0.5) and (nb.new_net > 0).any()
        return "SUPPORT" if ok else "NOT-EST(checks)"
    df["new_verdict"] = df.apply(verdict, axis=1)
    df.to_csv(os.path.join(OUT, "GRID_v2.csv"), index=False)
    print("bar", bar, "survivors", int(df.surv.sum()))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    cols = ["fam", "side", "k", "hold", "hedge", "disc_n", "disc_net", "disc_t", "disc_share_pos", "disc_per_yr",
            "mid_net", "new_n", "new_net", "new_lo", "new_hi", "new_t", "surv"]
    print(df.sort_values("disc_t", ascending=False)[cols].head(25).round(2).to_string())
    best = {}
    for F in ("F1", "F2", "F3"):
        b = df[df.F == F].sort_values("disc_t", ascending=False).iloc[0]; best[F] = b
        print("BEST", F, b[cols + ["new_trim5", "new_maxshare", "new_share_pos", "new_per_mo", "new_verdict"]].to_dict())
    for i, r in df[df.surv].iterrows(): best["S%d" % i] = r
    det = {}
    for nm, b in best.items():
        fam, side, k, h, hed = b.fam, int(b.side), b.k, b.hold, b.hedge
        d = {}
        for lab, extra in (("all", None), ("ex_stale_open", ~STALE)):
            for sl in ("disc", "mid", "new"):
                m = SL[sl]
                fire, net = cell_trades(X[fam], Z[fam], fam, side, k, h, hed, m)
                if extra is not None: fire = fire & extra
                tr = to_df(fire, net)
                s = E.summarize(tr, E.HOLDS[h], YEARS[sl])
                s["t_lag2h"] = E.cell_t(tr, 2 * E.HOLDS[h]) if len(tr) else np.nan
                d[lab + "_" + sl] = {kk: round(float(v), 2) for kk, v in s.items()}
        fire, net = cell_trades(X[fam], Z[fam], fam, side, k, h, hed, (yr >= 2012) & (yr <= 2025))
        tr = to_df(fire, net); yy = tr.groupby(tr.date.dt.year).net.agg(["count", "mean"]); yy["mean"] *= 1e4
        d["yearly"] = yy.round(1).to_dict()
        det[nm] = dict(cell=[fam, side, k, h, hed], **d)
        print(nm, json.dumps(det[nm]))
    json.dump(det, open(os.path.join(OUT, "BEST_v2.json"), "w"), indent=1, default=float)
    sys.exit()

if MODE == "holdout":
    df = pd.read_csv(os.path.join(OUT, "GRID_v2.csv"))
    rows = []
    for i, r in df[df.surv].iterrows():
        fire, net = cell_trades(X[r.fam], Z[r.fam], r.fam, int(r.side), r.k, r.hold, r.hedge, SL["hold"])
        tr = to_df(fire, net)
        s = E.summarize(tr, E.HOLDS[r.hold], YEARS["hold"])
        rows.append(dict(i=i, fam=r.fam, side=r.side, k=r.k, hold=r.hold, hedge=r.hedge, new_net=r.new_net,
                         new_verdict=r.new_verdict, **{"hold_" + kk: vv for kk, vv in s.items()}))
    h = pd.DataFrame(rows); h.to_csv(os.path.join(OUT, "HOLDOUT_v1.csv"), index=False)
    pd.set_option("display.width", 250)
    print(h[["i","fam","side","k","hold","hedge","new_net","new_verdict","hold_n","hold_net","hold_lo","hold_hi","hold_share_pos","hold_per_mo"]].round(2).to_string())
    print("holdout net>0:", (h.hold_net > 0).sum(), "of", len(h), "| SUPPORT cells net>0:", (h[h.new_verdict == "SUPPORT"].hold_net > 0).sum(), "of", (h.new_verdict == "SUPPORT").sum())
```

## scripts/intraday.py
```python
import yfinance as yf, pandas as pd, sys, os, time
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
T = ["TSM","BABA","JD","BIDU","NTES","SONY","TM","HMC","MUFG","SMFG","INFY","HDB","IBN","KB","SHG","PKX","SPY"]
for iv, per in (("1h", "730d"), ("5m", "60d")):
    for t in T:
        fn = os.path.join(OUT, f"{t}_{iv}.csv")
        if os.path.exists(fn): continue
        for k in range(4):
            try:
                df = yf.Ticker(t).history(period=per, interval=iv, auto_adjust=False, prepost=False)
                if len(df): break
            except Exception as e: print(t, e)
            time.sleep(3 * (k + 1))
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        df.to_csv(fn); print(t, iv, len(df), df.index.min(), df.index.max()); time.sleep(1)
```

## scripts/intraday_pm.py
```python
import yfinance as yf, pandas as pd, sys, os, time
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
T = ["TSM","BABA","JD","BIDU","NTES","SONY","TM","HMC","MUFG","SMFG","INFY","HDB","IBN","KB","SHG","PKX","SPY"]
for iv, per in (("1h", "730d"), ("5m", "60d")):
    for t in T:
        fn = os.path.join(OUT, f"{t}_{iv}_pm.csv")
        if os.path.exists(fn): continue
        for k in range(4):
            try:
                df = yf.Ticker(t).history(period=per, interval=iv, auto_adjust=False, prepost=True)
                if len(df): break
            except Exception as e: print(t, e)
            time.sleep(3 * (k + 1))
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        df.to_csv(fn); print(t, iv, len(df), df.index.min(), df.index.max()); time.sleep(1)
```

## scripts/pm.py
```python
# C2170 pre-market signal + MOO entry per AMENDMENT_A3. Usage: python pm.py DATADIR OUTDIR
import sys, os, numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(__file__))
import engine as E
DATA, OUT = sys.argv[1], sys.argv[2]
panels = E.build(DATA)

def pm_price(t, iv):
    b = pd.read_csv(os.path.join(DATA, "intraday", f"{t}_{iv}_pm.csv"), index_col=0, parse_dates=True)
    tm = b.index.hour * 60 + b.index.minute
    last_start = 9 * 60 + (25 if iv == "5m" else 0)
    b = b[(tm >= 8 * 60) & (tm <= last_start) & (b.High > b.Low)]
    return b.groupby(b.index.normalize()).Close.last()

def tr_factor(t):
    d = pd.read_csv(os.path.join(DATA, t + ".csv"), index_col=0, parse_dates=True)
    return d["Adj Close"] / d["Close"], d
fS, _ = tr_factor("SPY")
res, alltr = [], []
CELLS = [("A_F1_k1.5", "x1", 1.5), ("B_F2SPY_k1.0", "x2SPY", 1.0)] if len(sys.argv) < 4 else [("F1_k1.0", "x1", 1.0), ("F1_k2.0", "x1", 2.0), ("F1_k2.5", "x1", 2.5), ("F1_k1.5_hdg", "x1", 1.5)]
TAG = "v1" if len(sys.argv) < 4 else "A4"
for iv in (("1h", "5m") if TAG == "v1" else ("1h",)):
    spm = pm_price("SPY", iv)
    for cn, sig, k in CELLS:
        rows = []
        for pr, p in panels.items():
            f, raw = tr_factor(pr)
            ppm = np.log(pm_price(pr, iv) * f.reindex(pm_price(pr, iv).index))
            ppm = ppm.reindex(p.index)
            prem_pm = (ppm - p.H - p.ref).where(p.prem.notna())
            if sig == "x2SPY":
                a2, b2 = E.roll_beta_lag(p.prem, p.mSPY, 250, 60)
                m_pm = np.log((spm * fS.reindex(spm.index)).reindex(p.index)) - p.Sc.shift(1)
                x = prem_pm - (a2 + b2 * m_pm)
            else:
                x = prem_pm
            xd = p[sig]; sd = E.roll_sd_lag(xd.dropna()).reindex(p.index)
            z = x / sd
            fire = (z.abs() >= k) & x.notna() & p.rH0.notna()
            d = fire[fire].index
            s = -np.sign(x[d])
            if cn.endswith("_hdg"):
                net = (s * (p.rH0[d] - p.bc[d] * p.eH0[d])).values - 5e-4 * (1 + p.bc[d].abs().values)
            else:
                net = (s * p.rH0[d]).values - 5e-4
            rows.append(pd.DataFrame({"date": d, "pair": pr, "net": net,
                                      "pm_vs_open": (s * (p.Ao[d] - ppm[d])).values}))
        tr = pd.concat(rows); tr["iv"] = iv; tr["cell"] = cn; alltr.append(tr)
        for lab, m in (("2024-10-24..2025", (tr.date >= "2024-10-24") & (tr.date <= "2025-12-31")),
                       ("2026", tr.date.dt.year == 2026), ("all", tr.date >= "2024-10-24")):
            t2 = tr[m]
            if len(t2) < 5: continue
            lo, hi = E.block_ci(t2)
            res.append(dict(iv=iv, cell=cn, window=lab, n=len(t2), net=t2.net.mean() * 1e4, lo=lo, hi=hi,
                            pairs_pos=(t2.groupby("pair").net.mean() > 0).mean(), per_mo=len(t2) / (t2.date.dt.to_period("M").nunique()),
                            open_moved_toward_signal_bp=t2.pm_vs_open.mean() * 1e4))
df = pd.DataFrame(res); pd.set_option("display.width", 220); print(df.round(2).to_string())
df.to_csv(os.path.join(OUT, "PM_%s.csv" % TAG), index=False); pd.concat(alltr).to_csv(os.path.join(OUT, "PM_trades_%s.csv" % TAG), index=False)
```
