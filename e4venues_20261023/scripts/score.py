"""Step 2 (C2203-C2209): frozen E4 rule (K9 section 1) on NEW events per venue + overlap price agreement.
Usage: python3 -I scripts/score.py [fetch|score]   (fetch = data only, no numbers printed; score = numbers)"""
import json, os, sys
import numpy as np, pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venues as V

ROOT, H, DAY = V.ROOT, V.H, V.DAY
OUT = os.path.join(ROOT, 'out')
DATA_END = 1792742400000
COST = {'okx': 31.0, 'bitget': 33.0, 'gate': 31.0, 'bybit': 32.0}
PRIORITY = ['gate', 'bitget', 'okx', 'bybit']
VEN = ['okx', 'bitget', 'gate', 'bybit']  # bybit last: its rows depend on the others


def frame(rows):
    if not rows:
        return pd.DataFrame(columns=['op', 'hi', 'lo', 'cl', 'qv']).rename_axis('o')
    df = pd.DataFrame(rows, columns=['o', 'op', 'hi', 'lo', 'cl', 'qv']).drop_duplicates('o').set_index('o').sort_index()
    return df


def entry_bar(k1, T):
    tgt = T + H
    first_hour = -(-tgt // H) * H
    cand = k1.index[k1.index >= tgt]
    if len(cand) == 0:
        return None
    e = int(cand[0])
    return None if e > first_hour + H else e


def exit_close(k1, e, hold=168):
    for off in (hold - 1, hold - 2):
        t = e + off * H
        if t in k1.index:
            return float(k1.at[t, 'cl'])
    return None


def fund_sum(fu, e, hold=168):
    lo, hi = e + H // 2, e + hold * H + H // 2
    sel = [r[1] for r in fu if lo < r[0] <= hi]
    return sum(sel), len(sel)


def placebo(k1, e, notices):
    b = (e // (4 * H)) * (4 * H)
    nt = np.array(notices, dtype='int64')
    idx = k1.index
    starts = idx[(idx >= b - 90 * DAY) & (idx <= b + 90 * DAY) & (idx % (4 * H) == 0)]
    vals = []
    for s in starts:
        s = int(s)
        if len(nt) and np.any(np.abs(nt - s) <= 10 * DAY):
            continue
        last = s + 167 * H
        if last not in idx:
            continue
        vals.append(-(k1.at[last, 'cl'] / k1.at[s, 'op'] - 1) * 1e4)
    return (float(np.mean(vals)) if len(vals) >= 20 else np.nan), len(vals)


def boot(times, x, n=2000, seed=7):
    x = np.asarray(x, float); times = np.asarray(times)
    m = ~np.isnan(x); x, times = x[m], times[m]
    if len(x) == 0:
        return np.nan, np.nan, np.nan
    wk = pd.to_datetime(times, unit='ms').isocalendar()
    key = (wk.year.astype(str) + '-' + wk.week.astype(str)).values
    groups = [x[key == k] for k in pd.unique(key)]
    rng = np.random.default_rng(seed); G = len(groups); res = np.empty(n)
    for i in range(n):
        pick = rng.integers(0, G, G)
        res[i] = np.concatenate([groups[j] for j in pick]).mean()
    return x.mean(), np.percentile(res, 2.5), np.percentile(res, 97.5)


def bars(venue, sym, a, b):
    b = min(b, DATA_END)  # fixed data end: last complete 1h bar opens 2026-10-23 08:00 UTC
    f = {'okx': V.okx_1h, 'bitget': V.bitget_1h, 'gate': V.gate_1h, 'bybit': V.bybit_1h}[venue]
    return frame(f(sym, a, b))


def funding(venue, sym, e):
    a, b = e, e + 170 * H
    if venue == 'okx':
        return V.okx_funding(sym, a, b)
    if venue == 'bitget':
        return [r for r in V.bitget_funding(sym) if a <= r[0] < b]
    if venue == 'gate':
        return V.gate_funding(sym, (a // DAY) * DAY, (b // DAY + 1) * DAY)
    return []  # bybit: funding API blocked


def load():
    G = pd.read_csv(os.path.join(OUT, 'gate_events.csv'))
    cen = pd.read_csv(os.path.join(ROOT, 'data', 'census_slim.csv'))
    hl = pd.read_csv(os.path.join(ROOT, 'data', 'e4x_hl_events.csv'))
    ast = pd.read_csv(os.path.join(ROOT, 'data', 'k9_aster_scored.csv'))
    hl['coin_b'] = hl.coin.str.replace(r'^k(?=[A-Z])', '', regex=True)
    # notice lists for the placebo exclusion: every census notice + HL + Aster event of the coin
    G_c = G[G.src == 'census'][['coin', 'T']]
    notes = pd.concat([G_c, hl[['coin_b', 'T']].rename(columns={'coin_b': 'coin'}), ast[['coin', 'T']]]).drop_duplicates()
    NT = {c: g['T'].astype('int64').tolist() for c, g in notes.groupby('coin')}
    # NEW events: census, not on HL/Aster at T, no HL/Aster event of the coin within +-24h
    ref = pd.concat([hl[(hl['T'] >= 1735689600000)][['coin_b', 'T']].rename(columns={'coin_b': 'coin'}), ast[['coin', 'T']]])
    c = G[(G.src == 'census') & (G.f_HL.fillna('') != 'S') & (G.f_Aster.fillna('') != 'S')].copy()
    def dup(r):
        x = ref[ref.coin == r.coin]
        return bool(len(x) and np.any(np.abs(x['T'].values - r['T']) <= DAY))
    c['dup_ref'] = c.apply(dup, axis=1)
    new = c[(c.status == 'S') & ~c.dup_ref].copy()
    ov = G[G.src.isin(['HL', 'Aster']) & (G.status == 'S') & (G['T'] <= 1792108799000)].copy()
    return G, new, ov, NT


def score_new(new, NT, do_print):
    rows = []
    for venue in VEN:
        sub = new[new.venue == venue]
        if venue == 'bybit':  # A1: scored elsewhere (excess present) -> counts only; else scored on Bybit (price only)
            done = {(r['coin'], r['T']) for r in rows if r.get('drop') == '' and not pd.isna(r.get('excess', np.nan))}
            key = sub[['coin', 'T']].apply(lambda x: (x['coin'], int(x['T'])), axis=1)
            for r in sub[key.isin(done)].itertuples():
                rows.append(dict(venue=venue, coin=r.coin, T=int(r.T), sym=r.sym, drop='bybit_counts_only'))
            sub = sub[~key.isin(done)]
        grp = sub.groupby(['coin', 'T']) if venue == 'bybit' else sub.groupby('coin')  # Bybit: per-event windows (trade dumps)
        for key, g in grp:
            coin = key[0] if isinstance(key, tuple) else key
            sym = g.sym.iloc[0]
            a = int(g['T'].min()) - 91 * DAY; b = int(g['T'].max()) + 99 * DAY
            if venue == 'bybit':
                a = int(g['T'].min()) - DAY; b = int(g['T'].max()) + 9 * DAY
            try:
                k1 = bars(venue, sym, a, b)
            except Exception as ex:
                for r in g.itertuples(): rows.append(dict(venue=venue, coin=coin, T=int(r.T), sym=sym, drop='fetch_error'))
                continue
            for r in g.itertuples():
                T = int(r.T)
                out = dict(venue=venue, coin=coin, T=T, sym=sym, cost=COST[venue], drop='')
                e = entry_bar(k1, T)
                if e is None:
                    out['drop'] = 'no_entry'; rows.append(out); continue
                c168 = exit_close(k1, e)
                if c168 is None:
                    out['drop'] = 'no_exit'; rows.append(out); continue
                p0 = float(k1.at[e, 'op'])
                out.update(entry=e, entry_px=p0, ret168=(c168 / p0 - 1) * 1e4)
                win = k1.loc[e:e + 167 * H]
                out['mae'] = (win['hi'].max() / p0 - 1) * 1e4
                out['qv_day'] = win['qv'].sum(min_count=1) / (len(win) / 24) if len(win) else np.nan
                try:
                    fu = funding(venue, sym, e)
                    fs, fn = fund_sum(fu, e)
                except Exception:
                    fs, fn = np.nan, 0; out['note'] = 'fund_fetch_error'
                out['nfund'] = fn
                out['fund168'] = fs * 1e4 if fn >= 10 else np.nan
                out['N168'] = -out['ret168'] + out['fund168'] - COST[venue] if fn >= 10 else np.nan
                out['net_nofund'] = -out['ret168'] - COST[venue]  # Bybit-only rows (A1): no funding, no placebo
                if venue != 'bybit':
                    pm, pn = placebo(k1, e, NT.get(coin, [T]))
                    out['plac'], out['nplac'] = pm, pn
                    out['excess'] = -out['ret168'] - pm if pn >= 20 else np.nan
                rows.append(out)
    S = pd.DataFrame(rows)
    # symbol check: entry open vs another venue at the same entry hour
    S['sym_flag'] = ''
    ok = S[S['drop'] == ''] if 'drop' in S else S
    ok = ok.copy()
    mult = lambda r: 1000.0 if str(r.sym).startswith('1000') and not str(r.coin).startswith('1000') else 1.0
    ok['px_unit'] = [r.entry_px / mult(r) for r in ok.itertuples()]  # A1 (review must-fix 2)
    for i, r in ok.iterrows():
        oth = ok[(ok.coin == r.coin) & (ok['T'] == r['T']) & (ok.venue != r.venue) & (ok.entry == r.entry)]
        if len(oth) == 0:
            S.at[i, 'sym_flag'] = 'no_second_price'
        elif np.any(np.abs(oth.px_unit.values / r.px_unit - 1) > 0.10):
            S.at[i, 'sym_flag'] = 'mismatch'
    S.loc[S.sym_flag == 'mismatch', 'drop'] = 'symbol_mismatch'
    S.to_csv(os.path.join(OUT, 'new_scored.csv'), index=False)
    return S


def pick_union(S):
    """one row per NEW event: first venue in PRIORITY where it scored with funding; else first where excess exists."""
    ok = S[S['drop'] == ''].copy()
    ok['pr'] = ok.venue.map({v: i for i, v in enumerate(PRIORITY)})
    rows = []
    for (c, T), g in ok.groupby(['coin', 'T']):  # A1 (review must-fix 1): both > N168 > excess > priority
        g = g.assign(rk=-(2 * g.N168.notna().astype(int) * g.excess.notna().astype(int) + g.N168.notna().astype(int) + g.excess.notna().astype(int)))
        rows.append(g.sort_values(['rk', 'pr']).iloc[0])
    return pd.DataFrame(rows)


def say_cells(S, U, L):
    say = lambda s: (print(s), L.append(s))
    ok = S[S['drop'] == '']
    say(f"drops by venue: {S[S['drop']!=''].groupby(['venue','drop']).size().to_dict()}")
    for cid, venue in (('C2203', 'okx'), ('C2204', 'bitget'), ('C2205', 'gate'), ('C2206', 'bybit')):
        g = ok[ok.venue == venue]
        if not len(g):
            say(f"{cid} {venue}: scored 0"); continue
        yr = pd.to_datetime(g['T'], unit='ms').dt.year
        parts = [f"{cid} {venue}: scored {len(g)}"]
        for col in ('excess', 'N168', 'fund168'):
            if col in g and g[col].notna().any():
                m, lo, hi = boot(g['T'], g[col]); parts.append(f"{col} n {g[col].notna().sum()} {m:+.0f} [{lo:+.0f}, {hi:+.0f}]")
        for y in (2025, 2026):
            gy = g[yr == y]
            for col in ('excess', 'N168'):
                if col in gy and gy[col].notna().any():
                    m, lo, hi = boot(gy['T'], gy[col]); parts.append(f"{y} {col} n {gy[col].notna().sum()} {m:+.0f} [{lo:+.0f}, {hi:+.0f}]")
        say(' | '.join(parts))
    yr = pd.to_datetime(U['T'], unit='ms').dt.year
    m, lo, hi = boot(U['T'], U['excess']); n = U['excess'].notna().sum()
    v = 'NO DATA' if np.isnan(m) else ('KILL' if m <= 0 else ('SUPPORT' if lo > 0 and n >= 20 else 'NOT-ESTABLISHED'))
    say(f"C2207 NEW-layer excess (union, one venue each): n {n} mean {m:+.0f} [{lo:+.0f}, {hi:+.0f}] median {U['excess'].median():+.0f} -> {v}; venues {U.venue.value_counts().to_dict()}")
    for y in (2025, 2026):
        gy = U[yr == y]; m2, l2, h2 = boot(gy['T'], gy['excess']); say(f"   {y} excess n {gy['excess'].notna().sum()} {m2:+.0f} [{l2:+.0f}, {h2:+.0f}]")
    m, lo, hi = boot(U['T'], U['N168'])
    mc, lc, hc = boot(U['T'], U['N168'].clip(lower=-10000))
    x = U['excess'].dropna().sort_values()
    say(f"C2208 NEW-layer N168: n {U['N168'].notna().sum()} {m:+.0f} [{lo:+.0f}, {hi:+.0f}]; capped {mc:+.0f} [{lc:+.0f}, {hc:+.0f}]; funding mean {U['fund168'].mean():+.0f}; worst N168 {U['N168'].min():+.0f}; trim-5 excess {x.iloc[:-5].mean():+.0f}; top-5 share excess {x.iloc[-5:].sum()/x.sum():.2f}; placebo mean {U['plac'].mean():+.0f}")
    for y in (2025, 2026):
        gy = U[yr == y]; m2, l2, h2 = boot(gy['T'], gy['N168']); say(f"   {y} N168 n {gy['N168'].notna().sum()} {m2:+.0f} [{l2:+.0f}, {h2:+.0f}]")
    say(f"   symbol flags: {S.sym_flag.value_counts().to_dict()}")


# ---------------- overlap agreement ----------------
def ref_bars(src, coin, T):
    import requests
    a, b = T - DAY, T + 9 * DAY
    if src == 'Aster':
        sym = '1000NEXUSDT' if coin == 'NEX' else f'{coin}USDT'
        def f():
            r = V.get('https://fapi.asterdex.com/fapi/v1/klines', dict(symbol=sym, interval='1h', startTime=a, endTime=b, limit=1500))
            if r.status_code != 200: raise V.FetchError(sym)
            return [[int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[7])] for x in r.json()]
        return frame(V.cache(f'ref/aster_{sym}_{T}.json', f)), H
    hc = 'k' + coin if coin in ('PEPE', 'BONK', 'NEIRO', 'DOGS') else coin
    def f():
        r = V.S.post('https://api.hyperliquid.xyz/info', json={'type': 'candleSnapshot', 'req': {'coin': hc, 'interval': '4h', 'startTime': a, 'endTime': b}}, timeout=40)
        if r.status_code != 200: raise V.FetchError(hc)
        return [[int(x['t']), float(x['o']), float(x['h']), float(x['l']), float(x['c']), float(x['v'])] for x in r.json()]
    return frame(V.cache(f'ref/hl4h_{hc}_{T}.json', f)), 4 * H


def overlap(ov, do_print, L):
    say = (lambda s: (print(s), L.append(s))) if do_print else (lambda s: None)
    ast = pd.read_csv(os.path.join(ROOT, 'data', 'k9_aster_scored.csv'))
    rows = []
    for r in ov[ov.venue != 'bybit'].itertuples():  # A1: Bybit overlap needs GB of trade dumps for HL-size coins -> skipped
        T = int(r.T)
        try:
            vb = bars(r.venue, r.sym, T - DAY, T + 9 * DAY)
            rb, step = ref_bars(r.src, r.coin, T)
        except Exception as ex:
            rows.append(dict(venue=r.venue, src=r.src, coin=r.coin, T=T, err=str(ex)[:80])); continue
        if r.venue != 'bybit' or True:
            g = vb[vb.index % step == 0] if step == 4 * H else vb
            if step == 4 * H:  # aggregate venue 1h to 4h closes: close of the 4h bar = close of its last 1h bar
                c4 = vb['cl'].groupby((vb.index // (4 * H)) * (4 * H)).last()
                vc = c4
            else:
                vc = vb['cl']
            rc = rb['cl']
            j = pd.concat([vc.rename('v'), rc.rename('r')], axis=1).dropna()
            e = entry_bar(vb, T)
            jj = j[(j.index >= (e or T)) & (j.index <= (e or T) + 168 * H)] if e else j.iloc[0:0]
            if len(jj) < 10:
                rows.append(dict(venue=r.venue, src=r.src, coin=r.coin, T=T, err='short_overlap')); continue
            corr = np.corrcoef(np.diff(np.log(jj.v.values)), np.diff(np.log(jj.r.values)))[0, 1]
            gap = float(np.mean(jj.v / jj.r - 1) * 1e4)
            c168 = exit_close(vb, e)
            vret = (c168 / vb.at[e, 'op'] - 1) * 1e4 if c168 else np.nan
            if r.src == 'Aster':
                ra = ast[(ast.coin == r.coin) & (ast['T'] == T)]
                rret = float(ra.ret168.iloc[0]) if len(ra) and ra.ret168.notna().any() else np.nan
            else:
                rret = np.nan
            rows.append(dict(venue=r.venue, src=r.src, coin=r.coin, T=T, n=len(jj), corr=corr, gap_bp=gap, vret168=vret, rret168=rret, err=''))
    O = pd.DataFrame(rows); O.to_csv(os.path.join(OUT, 'overlap_agreement.csv'), index=False)
    ok = O[O.err == ''] if 'err' in O else O
    for (venue, src), g in ok.groupby(['venue', 'src']):
        d = (g.vret168 - g.rret168).dropna()
        say(f"C2209 overlap {venue} vs {src}: n {len(g)} corr median {g['corr'].median():.3f} p10 {g['corr'].quantile(.1):.3f}; mean gap {g.gap_bp.mean():+.1f} bp (median |gap| {g.gap_bp.abs().median():.1f}); ret168 diff vs Aster n {len(d)} mean {d.mean() if len(d) else float('nan'):+.0f} median |diff| {d.abs().median() if len(d) else float('nan'):.0f}")
    say(f"   overlap errors: {O[O.err!=''].groupby(['venue','err']).size().to_dict() if 'err' in O else {}}")


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else 'score'
    G, new, ov, NT = load()
    S = score_new(new, NT, mode == 'score')
    if mode == 'fetch':
        print('fetched NEW', len(S));
        overlap(ov, False, [])
        print('fetched overlap', flush=True)
        return
    L = []
    U = pick_union(S); U.to_csv(os.path.join(OUT, 'new_union.csv'), index=False)
    say_cells(S, U, L)
    overlap(ov, True, L)
    open(os.path.join(OUT, 'report_step2.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
