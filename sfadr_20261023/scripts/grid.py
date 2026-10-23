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
    disc = SL["disc"]; res = []
    for run in range(NR):
        Xs, Zs = {}, {}
        for fam, x in X.items():
            xs = x.copy()
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
    json.dump({"maxt": res.tolist(), "bar95": float(np.percentile(res, 95))}, open(os.path.join(OUT, "placebo_v1.json"), "w"))
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
    bar = json.load(open(os.path.join(OUT, "placebo_v1.json")))["bar95"]
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
    df.to_csv(os.path.join(OUT, "GRID_v1.csv"), index=False)
    print("bar", bar, "survivors", int(df.surv.sum()))
    pd.set_option("display.width", 250); pd.set_option("display.max_columns", 40)
    cols = ["fam", "side", "k", "hold", "hedge", "disc_n", "disc_net", "disc_t", "disc_share_pos", "disc_per_yr",
            "mid_net", "new_n", "new_net", "new_lo", "new_hi", "new_t", "surv"]
    print(df.sort_values("disc_t", ascending=False)[cols].head(25).round(2).to_string())
    for fam in SIGS:
        b = df[df.fam == fam].sort_values("disc_t", ascending=False).iloc[0]
        print("BEST", fam, b[cols].round(2).to_dict())
    sys.exit()
