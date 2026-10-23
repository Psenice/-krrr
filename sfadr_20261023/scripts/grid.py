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
