"""sfretail engine (ccsp3). Daily data only. All returns are backtest.
Conventions (frozen in PREREG.md):
  ov_t = (Open_t + Div_t)/Close_{t-1} - 1      (dividend added on the ex-date open)
  id_t = Close_t/Open_t - 1
  open-to-open index I_t = prod (1+id_{t-1})(1+ov_t)
  pageview day D (UTC) is complete at 20:00 ET on D -> first usable entry = open of the first trading day with date > D
"""
import json, glob, os, numpy as np, pandas as pd
from fetch_wiki import C as TITLES

NAMES = list(TITLES.keys())
DEV_END = pd.Timestamp("2025-12-31")
HOLD_START = pd.Timestamp("2026-01-01")
COST_STOCK = 5.0     # bp per side, stock leg
COST_SPY = 1.0       # bp per side, SPY hedge leg (times |beta|)
BORROW = {}          # annual borrow rate for shorts (fraction); tiers [verify]
for n in "AAPL AMZN META NFLX NVDA AMD TSLA UBER SHOP BABA ARM COIN SNAP RBLX DKNG ZM PLTR HOOD SOFI CHWY".split(): BORROW[n] = 0.005
for n in "SMCI MSTR RIVN LCID NIO MARA RIOT BB CVNA AFRM IONQ RKLB SOUN PTON PLUG".split(): BORROW[n] = 0.05
for n in "GME AMC UPST AI DJT".split(): BORROW[n] = 0.20
SPY_BORROW = 0.003
MIN_PRICE = 3.0      # unadjusted prior close, dollars


def load_prices(d="data"):
    O, Cl, Dv, Sp = {}, {}, {}, {}
    for t in NAMES + ["SPY"]:
        x = pd.read_csv(f"{d}/px_{t}.csv", index_col=0, parse_dates=True)
        x = x[(x["Open"] > 0) & (x["Close"] > 0)]
        O[t], Cl[t] = x["Open"], x["Close"]
        Dv[t] = x.get("Dividends", pd.Series(0.0, index=x.index)).fillna(0.0)
        Sp[t] = x.get("Stock Splits", pd.Series(0.0, index=x.index)).fillna(0.0)
    O, Cl, Dv, Sp = (pd.DataFrame(z).sort_index() for z in (O, Cl, Dv, Sp))
    idx = O["SPY"].dropna().index
    O, Cl, Dv, Sp = (z.reindex(idx) for z in (O, Cl, Dv, Sp))
    Dv = Dv.fillna(0.0); Sp = Sp.fillna(0.0).replace(0.0, 1.0)
    ov = (O + Dv) / Cl.shift(1) - 1
    idr = Cl / O - 1
    oo = (1 + idr.shift(1)) * (1 + ov)
    I = oo.fillna(1.0).cumprod().where(O.notna())
    cc = (1 + ov) * (1 + idr) - 1
    # unadjusted close: adjusted close times product of split ratios dated after t
    fut = Sp[::-1].cumprod()[::-1].shift(-1).fillna(1.0)
    Craw = Cl * fut
    # beta vs SPY, trailing 252 days of close-close, min 120 obs, known at close t (use shift(1) for entry at open t+1... see beta_at)
    b = {}
    for t in NAMES:
        cv = cc[t].rolling(252, min_periods=120).cov(cc["SPY"])
        b[t] = (cv / cc["SPY"].rolling(252, min_periods=120).var()).clip(0, 3)
    beta = pd.DataFrame(b)
    return dict(O=O, C=Cl, ov=ov, id=idr, I=I, cc=cc, beta=beta, Craw=Craw, idx=idx)


def load_views(d="data/wiki_raw"):
    S = {}
    for t, titles in TITLES.items():
        tot = None
        for ti in titles:
            fn = f"{d}/{t}__{ti.replace('/', '_').replace(' ', '_')}.json"
            if not os.path.exists(fn): continue
            it = json.load(open(fn)).get("items", [])
            if not it: continue
            s = pd.Series({pd.Timestamp(x["timestamp"][:8]): x["views"] for x in it}, dtype=float)
            tot = s if tot is None else tot.add(s, fill_value=0)
        if tot is None: continue
        full = pd.date_range("2015-07-01", "2026-10-22")
        tot = tot.reindex(full)
        first = tot[tot > 0].index.min()
        tot[tot.index < first] = np.nan
        S[t] = tot
    return pd.DataFrame(S)


def zscore(V, win=60, minobs=50):
    L = np.log1p(V)
    m = L.shift(1).rolling(win, min_periods=minobs).mean()
    s = L.shift(1).rolling(win, min_periods=minobs).std()
    return (L - m) / s.where(s > 0)


def shuffle_views(V, rng):
    out = V.copy()
    for t in V.columns:
        s = V[t]; ok = s.notna().values
        vals = s.values[ok].copy(); rng.shuffle(vals)
        a = s.values.copy(); a[ok] = vals; out[t] = a
    return out


def next_trading(idx, dates):
    """position in idx of the first trading day strictly after each calendar date"""
    return np.searchsorted(idx.values, dates.values, side="right")


def event_trades(P, sig, h, direction):
    """sig: DataFrame rows (name, D, entry_pos). direction +1 long / -1 short. Non-overlapping per name.
    Return DataFrame of trades with net bp."""
    I, beta, idx, Craw = P["I"], P["beta"], P["idx"], P["Craw"]
    rows = []
    for name, g in sig.sort_values("entry_pos").groupby("name"):
        busy_until = -1
        Iv = I[name].values; Is = I["SPY"].values; bv = beta[name].values; cr = Craw[name].values
        for e in g["entry_pos"].values:
            if e <= busy_until or e + h >= len(idx) or e < 1: continue
            if not (np.isfinite(Iv[e]) and np.isfinite(Iv[e + h]) and np.isfinite(bv[e - 1])): continue
            if not (cr[e - 1] >= MIN_PRICE): continue
            busy_until = e + h - 1
            b = bv[e - 1]
            rs = Iv[e + h] / Iv[e] - 1; rm = Is[e + h] / Is[e] - 1
            gross = direction * (rs - b * rm) * 1e4
            cost = 2 * COST_STOCK + 2 * COST_SPY * b
            if direction < 0: cost += BORROW[name] * h / 252 * 1e4
            else: cost += SPY_BORROW * b * h / 252 * 1e4
            rows.append((name, idx[e], idx[e + h], gross, gross - cost))
    return pd.DataFrame(rows, columns=["name", "entry", "exit", "gross_bp", "net_bp"])


def week_t(tr, col="net_bp"):
    if len(tr) < 5: return np.nan
    w = tr.groupby(tr["entry"].dt.to_period("W"))[col].mean()
    if len(w) < 5 or w.std() == 0: return np.nan
    return w.mean() / w.std() * np.sqrt(len(w))


def block_ci(tr, col="net_bp", B=1000, block=30, seed=7):
    if len(tr) < 5: return (np.nan, np.nan)
    rng = np.random.default_rng(seed)
    d0 = tr["entry"].min()
    blk = ((tr["entry"] - d0).dt.days // block).values
    ub = np.unique(blk)
    sums = pd.Series(tr[col].values).groupby(blk).sum().reindex(ub).values
    cnts = pd.Series(np.ones(len(tr))).groupby(blk).sum().reindex(ub).values
    ms = []
    for _ in range(B):
        k = rng.integers(0, len(ub), len(ub))
        ms.append(sums[k].sum() / cnts[k].sum())
    return tuple(np.percentile(ms, [2.5, 97.5]))


def summarize(tr, col="net_bp"):
    if len(tr) == 0:
        return dict(n=0)
    yrs = (tr["entry"].max() - tr["entry"].min()).days / 365.25
    yrs = max(yrs, 0.25)
    pn = tr.groupby("name")[col].agg(["sum", "count"])
    pn = pn[pn["count"] >= 3]
    top5 = tr[col].nlargest(5).sum()
    tot = tr[col].sum()
    lo, hi = block_ci(tr, col)
    return dict(n=len(tr), mean=tr[col].mean(), gross=tr["gross_bp"].mean(), lo=lo, hi=hi, t=week_t(tr, col),
                per_yr=len(tr) / yrs, per_month=len(tr) / yrs / 12, names=tr["name"].nunique(),
                frac_names_pos=(pn["sum"] > 0).mean() if len(pn) else np.nan,
                trim5=tr[col].drop(tr[col].nlargest(5).index).mean(),
                top5_share=top5 / tot if tot > 0 else np.nan,
                first=str(tr["entry"].min().date()), last=str(tr["exit"].max().date()))
