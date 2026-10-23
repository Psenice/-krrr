"""Step 3 (C2211-C2214): pooled supply cell = HL (published N168) + Aster (K9 N168) + NEW events with N168 (one venue each)."""
import os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as Sc

ROOT, OUT, H, DAY = Sc.ROOT, Sc.OUT, Sc.H, Sc.DAY
T0, T1, Y26 = 1735689600000, 1792108799000, 1767225600000  # 2025-01-01, 2026-10-15 23:59:59, 2026-01-01
NIGHTA = {1000: 0.94, 5000: 0.97, 25000: 0.56}


def load_pool():
    hl = pd.read_csv(os.path.join(ROOT, 'data', 'e4x_hl_events.csv'))
    hl = hl[(hl['T'] >= T0) & (hl['T'] <= T1)]
    hl = pd.DataFrame(dict(layer='HL', coin=hl.coin, T=hl['T'], N168=hl.N168, entry=(-(-(hl['T'] + H) // H)) * H, cap=np.nan))
    a = pd.read_csv(os.path.join(ROOT, 'data', 'k9_aster_scored.csv'))
    a = a[a['drop'].isna() & (a['T'] <= T1)]
    a = pd.DataFrame(dict(layer='Aster', coin=a.coin, T=a['T'], N168=a.N168, entry=a.entry, cap=np.nan))
    U = pd.read_csv(os.path.join(OUT, 'new_union.csv'))
    U = U[U.N168.notna() & (U['T'] >= T0) & (U['T'] <= T1)]
    n = pd.DataFrame(dict(layer='NEW_' + U.venue, coin=U.coin, T=U['T'], N168=U.N168, entry=U.entry, cap=np.nan))
    return pd.concat([hl, a, n], ignore_index=True).sort_values('entry').reset_index(drop=True)


def book(P, equity=100.0, cap_new=None, factor=1.0):
    """shared cap 3 open, slot = equity/3, 1x, booked at exit, N168 floored at -10,000 (slot lost)."""
    slot = equity / 3
    open_until, rows = [], []
    for r in P.itertuples():
        e = int(r.entry); x = e + 168 * H
        open_until = [t for t in open_until if t > e]
        if len(open_until) >= 3:
            continue
        open_until.append(x)
        notional = slot * (factor if not r.layer.startswith('NEW') else 1.0)
        if r.layer.startswith('NEW') and cap_new is not None:
            notional = min(slot, cap_new)
        rows.append(dict(exit=x, layer=r.layer, pnl=notional * max(r.N168, -10000) / 1e4))
    B = pd.DataFrame(rows)
    return B


def money(B, months):
    if B.empty:
        return 0.0, 0.0
    d = B.groupby(pd.to_datetime(B.exit, unit='ms').dt.floor('D')).pnl.sum().sort_index()
    eq = d.cumsum(); dd = (eq - np.maximum.accumulate(np.maximum(eq, 0))).min()
    return B.pnl.sum() / months, float(-dd)


def main():
    L = []
    say = lambda s: (print(s), L.append(s))
    P = load_pool()
    U = pd.read_csv(os.path.join(OUT, 'new_union.csv'))
    y26 = P['T'] >= Y26
    m, lo, hi = Sc.boot(P.loc[y26, 'T'], P.loc[y26, 'N168'])
    nw = P.layer.str.startswith('NEW')
    mn, ln, hn = Sc.boot(P.loc[y26 & nw, 'T'], P.loc[y26 & nw, 'N168'])
    ex_all = U['excess'].mean()
    c1 = m > 0 and lo > 0; c2 = mn > 0; c3 = ex_all > 0
    v = 'PASS' if c1 and c2 and c3 else ('NO-SUPPLY-GAIN' if c1 else 'FAIL')
    say(f"C2211 pooled 2026 N168: n {int(y26.sum())} mean {m:+.0f} [{lo:+.0f}, {hi:+.0f}] (cond1 {c1}); NEW-layer 2026 N168 n {int((y26 & nw).sum())} {mn:+.0f} [{ln:+.0f}, {hn:+.0f}] (cond2 {c2}); NEW excess all years {ex_all:+.0f} (cond3 {c3}) -> {v}")
    for lab, msk in (('all 2025-01..2026-10-15', np.ones(len(P), bool)), ('2025', ~y26), ('2026', y26)):
        g = P[msk]; mm, ll, hh = Sc.boot(g['T'], g['N168'])
        say(f"   pooled {lab}: n {len(g)} {mm:+.0f} [{ll:+.0f}, {hh:+.0f}]; by layer " + str(g.groupby('layer').N168.agg(['size', 'mean']).round(0).to_dict('index')))
    base = P[~nw]
    mb, lb, hb = Sc.boot(base.loc[base['T'] >= Y26, 'T'], base.loc[base['T'] >= Y26, 'N168'])
    say(f"   reference HL+Aster only 2026: n {int((base['T'] >= Y26).sum())} {mb:+.0f} [{lb:+.0f}, {hb:+.0f}]")
    mo25, mo26 = 12.0, (T1 + 1 - Y26) / DAY / 30.44
    Ux = U[(U['T'] >= T0) & (U['T'] <= T1)]
    for lab, s, e, mo in (('2025', T0, Y26, mo25), ('2026', Y26, T1 + 1, mo26)):
        a = ((Ux['T'] >= s) & (Ux['T'] < e))
        say(f"C2212 {lab}: NEW with N168 {((P['T'] >= s) & (P['T'] < e) & nw).sum() / mo:.2f}/month; NEW union (any scored) {a.sum() / mo:.2f}/month; HL+Aster {((P['T'] >= s) & (P['T'] < e) & ~nw).sum() / mo:.2f}/month; pooled {((P['T'] >= s) & (P['T'] < e)).sum() / mo:.2f}/month")
    dep = os.path.join(OUT, 'depth_books.csv')
    capm = None
    if os.path.exists(dep):
        D = pd.read_csv(dep); D = D[D.err.isna() | (D.err == '')]
        capm = float(D.cap29_usd.median())
        say(f"C2213 NEW-event $ fillable at <=29 bp one-way (today's books, last 10 coins per venue): median {capm:,.0f} (by venue {D.groupby('venue').cap29_usd.median().round(0).to_dict()}); HL/Aster use NightA factors")
    if v == 'PASS':
        P26 = P[y26]; Pb = P26[~P26.layer.str.startswith('NEW')]
        for lab, Q in (('pooled', P26), ('HL+Aster only', Pb)):
            B = book(Q); mpm, dd = money(B, mo26); k = 25 / dd if dd > 0 else np.nan
            say(f"C2214 {lab} 2026 book at 1x per $100: ${mpm:.2f}/month, worst DD ${dd:.1f}; at $25 DD: ${mpm * k:.2f}/month (k {k:.2f}); taken {len(B)} of {len(Q)}")
        for eq in (1000, 5000, 25000):
            B = book(P26, equity=eq, cap_new=capm, factor=NIGHTA[eq]); mpm, dd = money(B, mo26)
            Bb = book(Pb, equity=eq, factor=NIGHTA[eq]); mb_, ddb = money(Bb, mo26)
            say(f"C2214 ${eq:,}: pooled ${mpm:,.0f}/month (DD ${dd:,.0f}) vs HL+Aster ${mb_:,.0f}/month; after live third pooled ${mpm * 2 / 3:,.0f}")
    else:
        say("C2214 money: not computed (verdict is not PASS)")
    open(os.path.join(OUT, 'report_step3.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
