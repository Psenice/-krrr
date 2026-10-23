"""Cell builders for F1-F4 (frozen with PREREG.md)."""
import numpy as np, pandas as pd
from sflib import *

HOLDS = [1, 5, 20]
ZTH = 3.0


def shock_signals(P, Z):
    idx = P["idx"]
    zz = Z.stack().rename("z").reset_index(); zz.columns = ["D", "name", "z"]
    zz = zz[zz["z"] >= ZTH]
    zz["entry_pos"] = next_trading(idx, zz["D"])
    zz = zz[zz["entry_pos"] < len(idx)]
    # same-day return only when D is a trading day
    pos = idx.get_indexer(zz["D"])
    cc = P["cc"]
    zz["is_td"] = pos >= 0
    zz["ret_D"] = [cc[n].values[p] if p >= 0 else np.nan for n, p in zip(zz["name"], pos)]
    zz = zz.sort_values("z", ascending=False).drop_duplicates(["name", "entry_pos"])
    return zz


def f1f2(P, Z):
    sig = shock_signals(P, Z)
    out = {}
    for h in HOLDS:
        out[f"F1_fade_h{h}"] = event_trades(P, sig, h, -1)
        out[f"F1_cont_h{h}"] = event_trades(P, sig, h, +1)
        up = sig[sig["is_td"] & (sig["ret_D"] > 0)]; dn = sig[sig["is_td"] & (sig["ret_D"] < 0)]
        out[f"F2_up_fade_h{h}"] = event_trades(P, up, h, -1)
        out[f"F2_up_cont_h{h}"] = event_trades(P, up, h, +1)
        out[f"F2_dn_fade_h{h}"] = event_trades(P, dn, h, +1)   # fade a down day = long
        out[f"F2_dn_cont_h{h}"] = event_trades(P, dn, h, -1)   # continue a down day = short
    return out


def os_signal(P):
    return (np.log1p(P["ov"]) - np.log1p(P["id"])).rolling(20, min_periods=20).sum()[NAMES]


def f3(P, OS, quant=5):
    idx = P["idx"]
    Ia = P["I"][NAMES].values; Is = P["I"]["SPY"].values; Ba = P["beta"][NAMES].values
    Ca = P["Craw"][NAMES].values; Sa = OS[NAMES].values
    bor = np.array([BORROW[n] for n in NAMES])
    out = {}
    for h in HOLDS:
        plan = []
        for t in range(1, len(idx) - h - 1, h):
            e = t + 1
            ok = np.isfinite(Sa[t]) & np.isfinite(Ba[t]) & (np.nan_to_num(Ca[t]) >= MIN_PRICE) & np.isfinite(Ia[e]) & np.isfinite(Ia[e + h])
            j = np.where(ok)[0]
            if len(j) < 10: plan.append(None); continue
            k = max(2, len(j) // quant)
            o = j[np.argsort(Sa[t, j], kind="stable")]
            plan.append((t, e, set(o[-k:]), set(o[:k])))
        for lab, sgn in (("hiLo", 1), ("loHi", -1)):
            rows = []; prevL, prevS = set(), set()
            for i, p in enumerate(plan):
                if p is None: prevL, prevS = set(), set(); continue
                t, e, hi, lo = p
                L, S = (hi, lo) if sgn > 0 else (lo, hi)
                nxt = plan[i + 1] if i + 1 < len(plan) else None
                nL, nS = ((nxt[2], nxt[3]) if sgn > 0 else (nxt[3], nxt[2])) if nxt else (set(), set())
                rm = Is[e + h] / Is[e] - 1
                for j, d, prev, nset in [(n, 1, prevL, nL) for n in L] + [(n, -1, prevS, nS) for n in S]:
                    bb = Ba[t, j]
                    g = d * ((Ia[e + h, j] / Ia[e, j] - 1) - bb * rm) * 1e4
                    c = (COST_STOCK if j not in prev else 0) + (COST_STOCK if j not in nset else 0)
                    c += 2 * COST_SPY * bb if (j not in prev or j not in nset) else 0
                    c += (bor[j] if d < 0 else SPY_BORROW * bb) * h / 252 * 1e4
                    rows.append((NAMES[j], idx[e], idx[e + h], g, g - c, d))
                prevL, prevS = L, S
            out[f"F3_{lab}_h{h}"] = pd.DataFrame(rows, columns=["name", "entry", "exit", "gross_bp", "net_bp", "dir"])
    return out


def f4(P, Z):
    idx = P["idx"]; ov = P["ov"]; beta = P["beta"]; Craw = P["Craw"]
    # score known at the close of trading day t = z of calendar day t-1 (UTC day complete before the US close)
    Zt = Z.reindex(idx - pd.Timedelta(days=1)); Zt.index = idx
    Zt = Zt.reindex(columns=NAMES)
    nxt_ov = ov[NAMES].shift(-1); nxt_spy = ov["SPY"].shift(-1)
    beta = beta.shift(1)   # A1: beta from the close before the entry close
    valid = Zt.notna() & beta[NAMES].notna() & (Craw[NAMES] >= MIN_PRICE) & nxt_ov.notna()
    r = Zt.where(valid).rank(axis=1, pct=True)
    cnt = valid.sum(axis=1)
    out = {}
    for lab, m in (("top", r > 2 / 3), ("bottom", r <= 1 / 3), ("all", valid)):
        m = m & (cnt >= 9).values[:, None]
        g = (nxt_ov - beta[NAMES].mul(nxt_spy, axis=0)) * 1e4
        c = 2 * COST_STOCK + 2 * COST_SPY * beta[NAMES] + SPY_BORROW * beta[NAMES] / 252 * 1e4
        st = pd.DataFrame({"gross_bp": g.where(m).stack(), "net_bp": (g - c).where(m).stack()}).dropna().reset_index()
        st.columns = ["entry", "name", "gross_bp", "net_bp"]
        pos = idx.get_indexer(st["entry"])
        st["exit"] = idx[np.minimum(pos + 1, len(idx) - 1)]
        out[f"F4_{lab}"] = st[["name", "entry", "exit", "gross_bp", "net_bp"]]
    return out


def split(tr, part):
    if part == "dev": return tr[tr["exit"] <= DEV_END]
    if part == "hold": return tr[tr["entry"] >= HOLD_START]
    raise ValueError(part)
