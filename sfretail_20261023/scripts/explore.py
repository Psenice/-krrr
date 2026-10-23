"""Exploratory checks (A1 items 8, 9 + plateau). Labelled exploratory; never change a verdict.
usage: python3 scripts/explore.py CELL [CELL ...]  -> out/explore_v1.csv (appends)"""
import sys, os
sys.path.insert(0, "scripts")
import cells
from cells import *
from run import DROP, hold_of, nw_t

MEME = {"GME", "AMC", "BB"}


def build(P, Z, cell, lag=0):
    sig = shock_signals(P, Z); sig["entry_pos"] = sig["entry_pos"] + lag
    sig = sig[sig["entry_pos"] < len(P["idx"])]
    parts = cell.split("_"); h = int(parts[-1][1:])
    if cell.startswith("F1_"):
        d = -1 if parts[1] == "fade" else 1; s = sig
    else:
        side, kind = parts[1], parts[2]
        s = sig[sig["is_td"] & ((sig["ret_D"] > 0) if side == "up" else (sig["ret_D"] < 0))]
        d = {("up", "fade"): -1, ("up", "cont"): 1, ("dn", "fade"): 1, ("dn", "cont"): -1}[(side, kind)]
    return event_trades(P, s, h, d), d, h


def row(label, cell, d):
    s = summarize(d) if len(d) else {"n": 0}
    return dict(cell=cell, variant=label, n=s.get("n"), mean=s.get("mean"), lo=s.get("lo"), hi=s.get("hi"),
                t=nw_t(d, hold_of(cell)) if len(d) else None, per_month=s.get("per_month"))


if __name__ == "__main__":
    P = load_prices(); V = load_views(); V = V.drop(columns=[c for c in DROP if c in V.columns])
    out = []
    for cell in sys.argv[1:]:
        if not (cell.startswith("F1_") or cell.startswith("F2_")): continue
        Z = zscore(V)
        tr, d, h = build(P, Z, cell, lag=1); out.append(row("entry_E+1", cell, split(tr, "dev")))
        tr, d, h = build(P, Z, cell)
        dv = split(tr, "dev")
        if d < 0:
            x = dv[~(dv["name"].isin(MEME) & (dv["entry"] >= "2021-01-01") & (dv["entry"] <= "2021-03-31"))]
            out.append(row("no_meme_2021Q1", cell, x))
            y = dv.copy(); hi_tier = y["name"].map(lambda n: BORROW[n] >= 0.2)
            y.loc[hi_tier, "net_bp"] -= 2 * 0.20 * h / 252 * 1e4
            out.append(row("borrow_x3_top_tier", cell, y))
        for zt in (2.5, 3.5):
            cells.ZTH = zt
            tr, d, h = build(P, Z, cell); out.append(row(f"plateau_z{zt}", cell, split(tr, "dev")))
        cells.ZTH = 3.0
    df = pd.DataFrame(out)
    fn = "out/explore_v1.csv"
    df.to_csv(fn, mode="a", header=not os.path.exists(fn), index=False)
    print(df.round(2).to_string())
