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
