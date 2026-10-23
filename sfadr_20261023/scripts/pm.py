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
