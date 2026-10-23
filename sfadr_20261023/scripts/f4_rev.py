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
