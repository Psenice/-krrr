"""Runner (frozen in AMENDMENT_A1). Modes:
  python3 scripts/run.py placebo   -> out/placebo_v1.csv (dev only, 100 circular shifts per family)
  python3 scripts/run.py dev       -> out/dev_v1.csv + out/dev_years_v1.csv (needs placebo_v1.csv)
  python3 scripts/run.py holdout   -> out/holdout_v1.csv (once; refuses if out/HOLDOUT_OPENED exists)
"""
import sys, os, math, json
sys.path.insert(0, "scripts")
from cells import *

K = 100
FAM = {"F1": lambda c: c.startswith("F1_"), "F2": lambda c: c.startswith("F2_"),
       "F3": lambda c: c.startswith("F3_"), "F4": lambda c: c in ("F4_top", "F4_bottom")}
CONTROLS = {"F4_all"}   # reported, not in a placebo bar, not eligible to survive


def hold_of(c):
    return int(c.split("_h")[-1]) if "_h" in c else 1


def nw_t(tr, h, col="net_bp"):
    """A1: Newey-West t on weekly means of net bp by entry week, lag ceil(h/5)."""
    if len(tr) < 5: return np.nan
    w = tr.groupby(tr["entry"].dt.to_period("W"))[col].mean().values
    n = len(w)
    if n < 10: return np.nan
    L = max(1, math.ceil(h / 5)); m = w.mean(); e = w - m
    v = (e @ e) / n
    for l in range(1, L + 1):
        v += 2 * (1 - l / (L + 1)) * (e[l:] @ e[:-l]) / n
    return m / math.sqrt(v / n) if v > 0 else np.nan


def roll_dev(df, rng, cutoff=DEV_END, minshift=90):
    """A1 placebo: circularly shift each column's dev-period values (dates <= cutoff) by a random offset >= minshift."""
    out = df.copy()
    dev = df.index <= cutoff
    for c in df.columns:
        a = df[c].values.copy(); seg = a[dev]
        ok = np.where(np.isfinite(seg))[0]
        if len(ok) < 2 * minshift + 1: continue
        lo, hi = ok[0], ok[-1] + 1
        s = seg[lo:hi]; k = rng.integers(minshift, len(s) - minshift)
        seg = seg.copy(); seg[lo:hi] = np.roll(s, k); a[dev] = seg; out[c] = a
    return out


def all_cells(P, V=None, Z=None, OS=None):
    o = {}
    if Z is None and V is not None: Z = zscore(V)
    if Z is not None:
        o.update(f1f2(P, Z)); o.update(f4(P, Z))
    if OS is not None:
        o.update(f3(P, OS))
    return o


def max_dd(tr, col="net_bp"):
    s = tr.sort_values("exit").groupby("exit")[col].sum().cumsum()
    dd = s - s.cummax()
    under = (dd < 0)
    longest = 0; cur = 0; prev = None
    for d, u in under.items():
        cur = cur + 1 if u else 0; longest = max(longest, cur)
    return float(dd.min()), int(longest)


def main(mode):
    os.makedirs("out", exist_ok=True)
    P = load_prices(); V = load_views()
    Vg = V.drop(columns=[c for c in DROP if c in V.columns])
    if mode == "placebo":
        rng = np.random.default_rng(20261023)
        OS = os_signal(P)
        rows = []
        for k in range(K):
            Vs = roll_dev(Vg, rng)
            OSs = roll_dev(OS, rng)
            o = all_cells(P, V=Vs, OS=OSs)
            for c, tr in o.items():
                d = split(tr, "dev")
                rows.append((k, c, len(d), d["net_bp"].mean() if len(d) else np.nan, nw_t(d, hold_of(c))))
            if k % 10 == 0: print("placebo", k, flush=True)
        pl = pd.DataFrame(rows, columns=["k", "cell", "n", "mean", "t"])
        pl.to_csv("out/placebo_v1.csv", index=False)
        bars = {}
        for f, sel in FAM.items():
            mx = pl[pl["cell"].map(sel)].groupby("k")["t"].max()
            bars[f] = float(np.nanpercentile(mx, 95))
        json.dump(bars, open("out/placebo_bars_v1.json", "w"), indent=1); print(bars)
        return
    if mode == "dev":
        bars = json.load(open("out/placebo_bars_v1.json"))
        pl = pd.read_csv("out/placebo_v1.csv")
        o = all_cells(P, V=Vg, OS=os_signal(P))
        res, yrs = [], []
        for c, tr in o.items():
            d = split(tr, "dev"); s = summarize(d); h = hold_of(c)
            s["t"] = nw_t(d, h)
            fam = c[:2]; s["cell"] = c; s["family"] = fam
            s["bar"] = bars.get(fam, np.nan) if c not in CONTROLS else np.nan
            p = pl[pl["cell"] == c]
            s["placebo_mean"] = p["mean"].mean(); s["placebo_n"] = p["n"].mean()
            s["excess_vs_placebo"] = s.get("mean", np.nan) - s["placebo_mean"]
            nw = d[(d["entry"] >= "2025-01-01")]
            s["newest_n"] = len(nw); s["newest_mean"] = nw["net_bp"].mean() if len(nw) else np.nan
            nlo, nhi = block_ci(nw) if len(nw) >= 5 else (np.nan, np.nan)
            s["newest_lo"], s["newest_hi"] = nlo, nhi
            gates = {
                "t>bar": bool(s["t"] > s["bar"]) if np.isfinite(s["bar"]) else False,
                "lo>0": bool(s.get("lo", np.nan) > 0),
                "names60": bool(s.get("frac_names_pos", 0) >= 0.6),
                "50/yr": bool(s.get("per_yr", 0) >= 50),
                "trim5>0": bool(s.get("trim5", np.nan) > 0),
                "newest>0": bool(s["newest_mean"] > 0),
            }
            s["failed"] = ",".join(g for g, ok in gates.items() if not ok)
            if c in CONTROLS: s["verdict_dev"] = "CONTROL"
            elif not s["failed"]: s["verdict_dev"] = "SURVIVOR"
            elif not (s.get("mean", -1) > 0) or s.get("hi", -1) < 0: s["verdict_dev"] = "KILL"
            else: s["verdict_dev"] = "NOT-ESTABLISHED"
            if s["verdict_dev"] == "SURVIVOR": s["maxdd_bp"], s["underwater_days"] = max_dd(d)
            res.append(s)
            for y, g in d.groupby(d["entry"].dt.year):
                yrs.append((c, y, len(g), g["net_bp"].mean(), g["gross_bp"].mean()))
        pd.DataFrame(res).to_csv("out/dev_v1.csv", index=False)
        pd.DataFrame(yrs, columns=["cell", "year", "n", "net", "gross"]).to_csv("out/dev_years_v1.csv", index=False)
        print(pd.DataFrame(res)[["cell", "n", "mean", "gross", "lo", "hi", "t", "bar", "frac_names_pos", "per_month", "newest_n", "newest_mean", "verdict_dev", "failed"]].round(2).to_string())
        return
    if mode == "holdout":
        if os.path.exists("out/HOLDOUT_OPENED"): sys.exit("holdout already opened")
        open("out/HOLDOUT_OPENED", "w").write(pd.Timestamp.now(tz="UTC").isoformat())
        o = all_cells(P, V=Vg, OS=os_signal(P))
        res = []
        for c, tr in o.items():
            d = split(tr, "hold"); d = d[d["exit"] <= pd.Timestamp("2026-10-22")]
            s = summarize(d); s["cell"] = c; s["t"] = nw_t(d, hold_of(c)) if len(d) else np.nan
            res.append(s)
        pd.DataFrame(res).to_csv("out/holdout_v1.csv", index=False)
        print(pd.DataFrame(res)[["cell", "n", "mean", "gross", "lo", "hi", "per_month", "frac_names_pos"]].round(2).to_string())


DROP = ["RIOT", "AI"]   # A1 data gate: no usable article (RIOT) / two uncovered moves (AI)
if __name__ == "__main__":
    main(sys.argv[1])
