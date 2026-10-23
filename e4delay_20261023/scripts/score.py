"""Score PREREG (sha256 6748e406...) + AMENDMENTS (636436a6...). Writes out/events.csv, out/results.json."""
import json, numpy as np, pandas as pd
W = '/home/user/-krrr/e4delay_20261023'; R = f'{W}/raw'; OUT = f'{W}/out'
H = 3600000; DAY = 24 * H; COST = 20.0
DATA_END = 1792191600000  # 2026-10-22 23:00 UTC, last 1h bar on disk
GENERIC = {'THE', 'RED', 'OPEN', 'HOME', 'LA', 'SUN', 'BOB', 'AVA', 'SHELL', 'B3', 'XAN'}
FUND_END = None

_k, _f = {}, {}
def bars(c):
    if c not in _k:
        try: _k[c] = pd.read_csv(f'{R}/k/{c}.csv').drop_duplicates('t').set_index('t').sort_index()
        except FileNotFoundError: _k[c] = None
    return _k[c]
def fund(c):
    if c not in _f:
        try: _f[c] = pd.read_csv(f'{R}/f/{c}.csv')
        except FileNotFoundError: _f[c] = None
    return _f[c]

def leg(C, F, et):
    """short at open of bar et, 168 bars, exit close of bar et+167h. None if any bar missing."""
    idx = np.arange(et, et + 168 * H, H)
    if not np.isin(idx, C.index).all(): return None
    X = C.loc[idx]; ep, xp = X.o.iloc[0], X.c.iloc[-1]; xt = et + 168 * H
    fz = 0
    if F is None or len(F) == 0 or F.time.max() < xt - 8 * H: fz = 1
    fu = 0.0 if F is None else F[(F.time > et) & (F.time <= xt)].rate.sum() * 1e4
    gross = -(xp / ep - 1) * 1e4; net = gross + fu - COST; mae = (X.h.max() / ep - 1) * 1e4
    return dict(entry=et, gross=gross, fund=fu, net=net, mae=mae, liq1=int(mae >= 9000), liq2=int(mae >= 4500),
                floored=-10000.0 if mae >= 9000 else net, fund_zero=fz)

def placebo(C, et, ev_times):
    s = C.index[(C.index >= et - 90 * DAY) & (C.index <= et + 90 * DAY)]; s = s[s % (4 * H) == 0]
    ev = np.asarray(ev_times)
    v = [-(C.at[t + 167 * H, 'c'] / C.at[t, 'o'] - 1) * 1e4 for t in s
         if np.all(np.abs(t - ev) > 10 * DAY) and t + 167 * H in C.index]
    return float(np.mean(v)) if len(v) >= 20 else np.nan

def btc_move(et):
    B = bars('BTC')
    if B is None or et not in B.index or et + 167 * H not in B.index: return np.nan
    return (B.at[et + 167 * H, 'c'] / B.at[et, 'o'] - 1) * 1e4

def boot(x, t, n=2000, seed=2220):
    x = np.asarray(x, float); wk = pd.to_datetime(np.asarray(t), unit='ms', utc=True).strftime('%G-%V')
    g = pd.Series(x).groupby(wk.values); keys = list(g.groups); sums = g.sum().values; cnt = g.count().values
    rng = np.random.default_rng(seed); m = []
    for _ in range(n):
        i = rng.integers(0, len(keys), len(keys)); m.append(sums[i].sum() / cnt[i].sum())
    return float(np.percentile(m, 2.5)), float(np.percentile(m, 97.5))

def stat(x, t):
    x = np.asarray(x, float); t = np.asarray(t)
    if len(x) == 0: return dict(n=0)
    d = dict(n=int(len(x)), mean=float(x.mean()), median=float(np.median(x)), worst=float(x.min()), best=float(x.max()))
    if len(x) >= 3: d['lo'], d['hi'] = boot(x, t)
    if len(x) > 1: d['ex_best'] = float(np.sort(x)[:-1].mean())
    if len(x) > 6: d['trim5'] = float(np.sort(x)[:-5].mean())
    return d

def main():
    A = pd.read_csv(f'{W}/data/a_hl_pre2025.csv'); A['sub'] = 'A'
    B = pd.read_csv(f'{W}/data/b_bnonly_2025_26.csv'); B['sub'] = 'B'
    E = pd.concat([A, B[['coin', 'T', 'sub']]]).sort_values('T').reset_index(drop=True)
    keep, last = [], {}
    for r in E.itertuples():
        if r.coin in last and r.T - last[r.coin] < 7 * DAY: keep.append(False); continue
        keep.append(True); last[r.coin] = r.T
    E = E[keep].reset_index(drop=True)
    rows = []
    for r in E.itertuples():
        T = int(r.T); rec = dict(coin=r.coin, T=T, sub=r.sub, generic=int(r.coin in GENERIC))
        C = bars(r.coin); F = fund(r.coin)
        if C is None or C.index[0] > T - DAY: rows.append({**rec, 'drop': 'no perp'}); continue
        b0 = T - T % H
        if b0 not in C.index: rows.append({**rec, 'drop': 'no notice bar'}); continue
        p0 = C.at[b0, 'o']; etE = T + H if T % H == 0 else b0 + 2 * H
        pre = C.loc[(C.index >= b0) & (C.index < etE)]
        Rg = pre.h.max() / p0 - 1; gated = bool(Rg >= 0.20)
        # ccB loop (also used for S1, any-time)
        P = C.at[b0, 'h']; trig = None
        for t in C.index[(C.index > b0) & (C.index + H <= T + 7 * DAY)]:
            P = max(P, C.at[t, 'h']); c = C.at[t, 'c']
            if P >= 1.2 * p0 and C.at[t, 'c'] <= P - (P - p0) / 3: trig = int(t); break
        peak = (C.loc[(C.index >= b0) & (C.index + H <= T + 7 * DAY)].h.max() / p0 - 1)
        rec.update(R_gate=Rg * 1e4, gated=int(gated), peak7d=peak * 1e4, trig=trig)
        if T + 15 * DAY > DATA_END: rows.append({**rec, 'drop': 'censored'}); continue
        e4 = leg(C, F, etE)
        if e4 is None: rows.append({**rec, 'drop': 'no exit E4'}); continue
        dl = leg(C, F, trig + H) if trig is not None else None
        if trig is not None and dl is None: rows.append({**rec, 'drop': 'no exit delayed'}); continue
        evt = E[E.coin == r.coin]['T'].values
        rec.update({f'e4_{k}': v for k, v in e4.items()})
        rec['e4_plac'] = placebo(C, etE, evt); rec['e4_btc'] = btc_move(etE)
        if dl is not None:
            rec.update({f'd_{k}': v for k, v in dl.items()}); rec['delay_h'] = (dl['entry'] - etE) / H
            rec['d_plac'] = placebo(C, dl['entry'], evt); rec['d_btc'] = btc_move(dl['entry'])
        rows.append(rec)
    D = pd.DataFrame(rows); D.to_csv(f'{OUT}/events.csv', index=False)
    ok = D[D['drop'].isna()].copy() if 'drop' in D else D.copy()
    ok['yr'] = pd.to_datetime(ok['T'], unit='ms').dt.year
    res = {'population_after_dedupe': int(len(E)), 'by_sub': E['sub'].value_counts().to_dict(),
           'drops': D['drop'].value_counts().to_dict(), 'scored': int(len(ok))}
    res['E4_all'] = stat(ok.e4_floored, ok['T'])
    # decider: gated events. Delayed policy: trade if triggered, else 0.
    G = ok[ok.gated == 1].copy()
    G['dpol'] = G.d_floored.fillna(0.0); G['delta'] = G.dpol - G.e4_floored
    G['delta_unf'] = G.d_net.fillna(0.0) - G.e4_net
    res['gated'] = dict(n=int(len(G)), triggered=int(G.trig.notna().sum()))
    res['C2221_delta'] = stat(G.delta, G['T'])
    res['C2221_e4_leg'] = stat(G.e4_floored, G['T']); res['C2221_delayed_leg'] = stat(G.dpol, G['T'])
    tr = G[G.trig.notna()]; un = G[G.trig.isna()]
    res['delta_triggered'] = stat(tr.delta, tr['T']); res['delta_untriggered'] = stat(un.delta, un['T'])
    noliq = G[(G.e4_liq1 == 0) & (G.d_liq1.fillna(0) == 0)]; res['delta_ex_liq'] = stat(noliq.delta, noliq['T'])
    ng = G[G.generic == 0]; res['delta_ex_generic'] = stat(ng.delta, ng['T'])
    res['delta_unfloored'] = stat(G.delta_unf, G['T'])
    res['by_year'] = {int(y): stat(g.delta, g['T']) for y, g in G.groupby('yr')}
    res['by_sub'] = {s: stat(g.delta, g['T']) for s, g in G.groupby('sub')}
    res['policy_level_mean_all_scored'] = float(G.delta.sum() / len(ok)) if len(ok) else None
    span_m = (ok['T'].max() - ok['T'].min()) / (30.4375 * DAY)
    res['fires_per_month_gated'] = len(G) / span_m; res['span_months'] = span_m
    res['liq'] = dict(e4_1x=int(G.e4_liq1.sum()), e4_2x=int(G.e4_liq2.sum()),
                      d_1x=int(G.d_liq1.fillna(0).sum()), d_2x=int(G.d_liq2.fillna(0).sum()))
    res['fund_zero_flags'] = int(G.e4_fund_zero.sum() + G.d_fund_zero.fillna(0).sum())
    # S3 placebo excess
    res['S3_excess_e4'] = stat((G.e4_gross - G.e4_plac).dropna(), G.loc[(G.e4_gross - G.e4_plac).notna(), 'T'])
    xd = (tr.d_gross - tr.d_plac).dropna(); res['S3_excess_delayed_trig'] = stat(xd, tr.loc[xd.index, 'T'])
    res['btc_move_mean'] = dict(e4=float(G.e4_btc.mean()), delayed_trig=float(tr.d_btc.mean()) if len(tr) else None)
    # S2 random-delay placebo on triggered gated events
    if len(tr) >= 3:
        rng = np.random.default_rng(2223); dl = tr.delay_h.values; sims = []
        for _ in range(1000):
            v = []
            for i, r in enumerate(tr.itertuples()):
                d = rng.choice(np.delete(dl, i)); C = bars(r.coin)
                x = leg(C, fund(r.coin), int(r.e4_entry + round(d) * H))
                v.append((x['floored'] if x else np.nan) - r.e4_floored)
            sims.append(np.nanmean(v))
        res['S2_random_delay'] = dict(real=float(tr.delta.mean()), p50=float(np.median(sims)), p90=float(np.percentile(sims, 90)),
                                      pct_of_real=float((np.array(sims) < tr.delta.mean()).mean() * 100))
    # S1 ccB-style any-time (biased): all scored events whose trigger fired
    S1 = ok[ok.trig.notna() & ok.d_floored.notna()]
    res['S1_anytime_delayed'] = stat(S1.d_floored, S1['T']); res['S1_anytime_e4'] = stat(S1.e4_floored, S1['T'])
    res['S1_anytime_delta'] = stat(S1.d_floored - S1.e4_floored, S1['T'])
    # verdict
    d = res['C2221_delta']; n = d['n']
    if n >= 20 and d['mean'] <= 0: v = 'KILL'
    elif (n >= 20 and d['mean'] > 0 and d.get('lo', -1) > 0 and d.get('ex_best', -1) > 0 and d.get('trim5', -1) > 0
          and res['delta_ex_liq'].get('mean', -1) > 0):
        v = 'PASS'
        y = res['by_year'].get(2026, {'n': 0})
        if y['n'] >= 5 and y['mean'] <= 0: v = 'NOT-ESTABLISHED (2026 downgrade)'
    else: v = 'NOT-ESTABLISHED'
    res['verdict'] = v
    json.dump(res, open(f'{OUT}/results.json', 'w'), indent=1, default=float)
    print(json.dumps(res, indent=1, default=float))

if __name__ == '__main__':
    main()
