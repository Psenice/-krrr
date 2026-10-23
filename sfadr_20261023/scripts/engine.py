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

def load(d, t):
    df = pd.read_csv(os.path.join(d, t.replace("=", "_") + ".csv"), index_col=0, parse_dates=True)
    df = df[~df.index.duplicated(keep="last")]
    return df[["Open", "High", "Low", "Close", "Volume"]].replace(0, np.nan)

def roll_sd_lag(x, n=250, mn=60):
    return x.rolling(n, min_periods=mn).std().shift(1)

def roll_beta_lag(y, x, n=250, mn=60):
    # OLS slope + intercept of y on x over previous n valid obs (both valid), lagged one row
    m = y.notna() & x.notna()
    yy, xx = y.where(m), x.where(m)
    mx = xx.rolling(n, min_periods=mn).mean(); my = yy.rolling(n, min_periods=mn).mean()
    cov = (xx * yy).rolling(n, min_periods=mn).mean() - mx * my
    var = (xx * xx).rolling(n, min_periods=mn).mean() - mx * mx
    b = cov / var; a = my - b * mx
    return a.shift(1), b.shift(1)

def clean_fx(fx):
    lf = np.log(fx)
    nb = pd.concat([lf.shift(k) for k in (-2, -1, 1, 2)], axis=1).median(axis=1)
    return fx.where((lf - nb).abs() <= 0.03)

def build(datadir):
    spy = load(datadir, "SPY")
    out = {}
    for adr, home, fxt, etf in PAIRS:
        A = load(datadir, adr); Hm = load(datadir, home); FX = load(datadir, fxt); E = load(datadir, etf)
        idx = spy.index
        A = A.reindex(idx)
        p = pd.DataFrame(index=idx)
        p["Ao"], p["Ac"] = np.log(A.Open), np.log(A.Close)
        p["Avol"] = A.Close * A.Volume
        fx = clean_fx(FX.Open).reindex(idx)
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
        _, p["bc"] = roll_beta_lag(p.Ac.diff(), p.Ec.diff(), 250, 60)
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
        p["r_rev"] = (p.Ac - p.H - p.ref).where(prem.notna())
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

def block_ci(tr, block=30, B=2000, seed=0):
    if len(tr) < 5: return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    tr = tr.sort_values("date")
    dates = np.array(sorted(tr.date.unique()))
    bid = {d: i // block for i, d in enumerate(dates)}
    tr = tr.assign(b=tr.date.map(bid))
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
