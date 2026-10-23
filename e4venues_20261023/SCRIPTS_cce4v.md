## scripts/depth.py
```python
"""C2210: today's order books for the last 10 NEW-event coins per venue (OKX, Bitget, Gate; Bybit REST blocked).
Sell side walk: $ notional fillable with average one-way slippage vs mid <= 29 bp; slippage at $100/$500/$5k."""
import os, sys, json, time
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venues as V
import score as Sc

OUT = Sc.OUT


def book(venue, sym):
    if venue == 'okx':
        ins = V.get('https://www.okx.com/api/v5/public/instruments', dict(instType='SWAP', instId=sym)).json()['data'][0]
        ct = float(ins['ctVal'])
        d = V.get('https://www.okx.com/api/v5/market/books', dict(instId=sym, sz=400)).json()['data'][0]
        bids = [(float(p), float(q) * ct) for p, q, *_ in d['bids']]; asks = [(float(p), float(q) * ct) for p, q, *_ in d['asks']]
    elif venue == 'bitget':
        d = V.get('https://api.bitget.com/api/v2/mix/market/merge-depth', dict(symbol=sym, productType='USDT-FUTURES', limit='max')).json()['data']
        bids = [(float(p), float(q)) for p, q in d['bids']]; asks = [(float(p), float(q)) for p, q in d['asks']]
    else:
        c = V.get(f'https://api.gateio.ws/api/v4/futures/usdt/contracts/{sym}').json()
        m = float(c['quanto_multiplier'])
        d = V.get('https://api.gateio.ws/api/v4/futures/usdt/order_book', dict(contract=sym, limit=300)).json()
        bids = [(float(x['p']), float(x['s']) * m) for x in d['bids']]; asks = [(float(x['p']), float(x['s']) * m) for x in d['asks']]
    return sorted(bids, reverse=True), sorted(asks)


def walk(bids, mid, usd):
    left, qty, cost = usd, 0.0, 0.0
    for p, q in bids:
        take = min(q, left / p)
        qty += take; cost += take * p; left -= take * p
        if left <= 1e-9: break
    if left > 1e-6: return np.nan
    return (1 - (cost / qty) / mid) * 1e4


def cap29(bids, mid):
    qty, cost, best = 0.0, 0.0, 0.0
    for p, q in bids:
        # largest fill within this level keeping avg slippage <= 29 bp
        lim = mid * (1 - 29e-4)
        if (cost + q * p) / (qty + q) >= lim:
            qty += q; cost += q * p; best = cost
        else:
            # partial: solve (cost + x p)/(qty + x) = lim
            x = (lim * qty - cost) / (p - lim) if p < lim else q
            x = max(0.0, min(q, x)); best = cost + x * p
            break
    return best


def main():
    G = pd.read_csv(os.path.join(OUT, 'gate_events.csv'))
    _, new, _, _ = Sc.load()
    rows = []
    for venue in ['okx', 'bitget', 'gate']:
        sub = new[new.venue == venue].sort_values('T', ascending=False).drop_duplicates('coin').head(10)
        for r in sub.itertuples():
            try:
                bids, asks = book(venue, r.sym)
                mid = (bids[0][0] + asks[0][0]) / 2
                rows.append(dict(venue=venue, coin=r.coin, T=int(r.T), spread_bp=(asks[0][0] / bids[0][0] - 1) * 1e4,
                                 s100=walk(bids, mid, 100), s500=walk(bids, mid, 500), s5k=walk(bids, mid, 5000), cap29_usd=cap29(bids, mid), err=''))
            except Exception as e:
                rows.append(dict(venue=venue, coin=r.coin, T=int(r.T), err=str(e)[:80]))
            time.sleep(0.2)
    D = pd.DataFrame(rows); D.to_csv(os.path.join(OUT, 'depth_books.csv'), index=False)
    L = []
    for v, g in D[D.err == ''].groupby('venue'):
        s = (f"C2210 {v}: n {len(g)} spread median {g.spread_bp.median():.1f} bp; one-way slip $100 median {g.s100.median():.1f}, $500 {g.s500.median():.1f}, $5k {g.s5k.median():.1f} bp; "
             f"$ fillable at <=29 bp: median {g.cap29_usd.median():,.0f}, min {g.cap29_usd.min():,.0f}; coins >29bp at $500: {list(g[g.s500 > 29].coin)}")
        print(s); L.append(s)
    open(os.path.join(OUT, 'report_depth.txt'), 'w').write('\n'.join(L) + '\n')


if __name__ == '__main__':
    main()
```
## scripts/gate.py
```python
"""Step 1 (C2200-C2202): venue gate. For every coin in the census + HL/Aster event lists, find the first kline of its USDT
perp on OKX, Bitget, Gate (daily candles from the public API; a listing day that straddles T-24h is refined with 1h
candles) and Bybit (first daily trade dump; refined with the first trade timestamp). Writes out/listings.csv and
out/gate_events.csv (one row per notice x venue)."""
import os, re, sys, json, time
from concurrent.futures import ThreadPoolExecutor
import pandas as pd
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import venues as V

ROOT = V.ROOT
OUT = os.path.join(ROOT, 'out'); os.makedirs(OUT, exist_ok=True)
D = os.path.join(ROOT, 'data')


def base(t):
    t = str(t)
    if re.fullmatch(r'[A-Z]{2,}2', t) and t not in ('2Z',):  # Upbit duplicate-ticker suffix (GAME2, MET2, UP2, META2)
        return t[:-1]
    if t.startswith('k') and t[1:2].isupper():  # HL kPEPE -> 1000PEPE handled by variants
        return t[1:]
    return t


def first_daily(venue, coin):
    """(symbol, first bar open ms, last bar open ms) over coin variants; (None, None, None) if absent."""
    for c in V.variants(coin):
        if venue == 'okx':
            s = V.okx_inst(c); d = V.okx_daily(s)
        elif venue == 'bitget':
            s = V.bitget_sym(c); d = V.bitget_daily(s)
        elif venue == 'gate':
            s = V.gate_sym(c); d = V.gate_daily(s)
        else:
            s = V.bybit_sym(c); days = V.bybit_days(s)
            if days:
                f = int(pd.Timestamp(days[0], tz='UTC').value // 10**6); l = int(pd.Timestamp(days[-1], tz='UTC').value // 10**6)
                return s, f, l
            continue
        if d:
            return s, d[0][0], d[-1][0]
    return None, None, None


def refine(venue, sym, day0):
    """exact first 1h bar (or first trade) on the listing day."""
    if venue == 'bybit':
        return V.bybit_first_trade(sym, pd.Timestamp(day0, unit='ms').strftime('%Y-%m-%d'))
    f = {'okx': V.okx_1h, 'bitget': V.bitget_1h, 'gate': V.gate_1h}[venue]
    rows = f(sym, day0, day0 + V.DAY + V.H)
    return rows[0][0] if rows else day0 + V.DAY


def main():
    cen = pd.read_csv(os.path.join(D, 'census_slim.csv'), dtype={'T': 'int64'}).fillna('')
    hl = pd.read_csv(os.path.join(D, 'e4x_hl_events.csv'))
    g1 = pd.read_csv(os.path.join(D, 'g1_aster_events.csv'))
    cen['coin'] = cen.ticker.map(base)
    hl['coin_b'] = hl.coin.map(base)
    coins = sorted(set(cen.coin) | set(hl.loc[hl['T'] >= 1735689600000, 'coin_b']) | set(g1.coin))
    print('coins', len(coins), flush=True)
    res = {}

    def run(venue):
        rows = []
        for c in coins:
            try:
                s, f, l = first_daily(venue, c)
                rows.append(dict(venue=venue, coin=c, sym=s, first_day=f, last_day=l, err=''))
            except Exception as e:
                rows.append(dict(venue=venue, coin=c, sym=None, first_day=None, last_day=None, err=str(e)[:120]))
        return rows

    with ThreadPoolExecutor(4) as P:
        for rows in P.map(run, ['okx', 'bitget', 'gate', 'bybit']):
            for r in rows: res[(r['venue'], r['coin'])] = r
    L = pd.DataFrame(res.values())

    # events: census notices + HL (>=2025) + Aster class
    ev = pd.concat([
        cen.assign(src='census', ev_coin=cen.coin)[['src', 'v', 'T', 'ticker', 'ev_coin', 'f_HL', 'f_Aster', 'f_BinanceFut']],
        hl[hl['T'] >= 1735689600000].assign(src='HL', v='', ticker=hl.coin, ev_coin=hl.coin_b, f_HL='S', f_Aster='', f_BinanceFut='')[['src', 'v', 'T', 'ticker', 'ev_coin', 'f_HL', 'f_Aster', 'f_BinanceFut']],
        g1.assign(src='Aster', v=g1.venue.str[0], ticker=g1.coin, ev_coin=g1.coin, f_HL='', f_Aster='S', f_BinanceFut='')[['src', 'v', 'T', 'ticker', 'ev_coin', 'f_HL', 'f_Aster', 'f_BinanceFut']],
    ], ignore_index=True)
    out = []
    for e in ev.itertuples():
        for venue in ['okx', 'bitget', 'gate', 'bybit']:
            r = res[(venue, e.ev_coin)]
            st, first = 'N', None
            if r['err']:
                st = 'ERR'
            elif r['first_day'] is not None:
                f0 = int(r['first_day']); cut = int(e.T) - V.DAY
                if f0 + V.DAY <= cut:
                    first = f0
                elif f0 > int(e.T) + V.H:
                    first = f0
                else:
                    try:
                        first = refine(venue, r['sym'], f0)
                    except Exception as ex:
                        st = 'ERR'; first = None
                if first is not None:
                    if first <= cut: st = 'S'
                    elif first <= int(e.T) + V.H: st = 'D'
                    else: st = 'L'
                    # delisted before the 7-day hold ends?
                    if st == 'S' and r['last_day'] is not None and int(r['last_day']) < int(e.T) + 9 * V.DAY:
                        st = 'S_delisted'
            out.append(dict(src=e.src, kv=e.v, T=int(e.T), ticker=e.ticker, coin=e.ev_coin, f_HL=e.f_HL, f_Aster=e.f_Aster,
                            f_BinanceFut=e.f_BinanceFut, venue=venue, sym=r['sym'], first=first, status=st))
    G = pd.DataFrame(out)
    L.to_csv(os.path.join(OUT, 'listings.csv'), index=False)
    G.to_csv(os.path.join(OUT, 'gate_events.csv'), index=False)
    print(L.groupby('venue').apply(lambda g: pd.Series(dict(found=g.sym.notna().sum(), err=(g.err != '').sum()))))


if __name__ == '__main__':
    main()
```
## scripts/gate_counts.py
```python
"""C2200-C2202 counts from out/gate_events.csv (no returns)."""
import os, sys
import pandas as pd, numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as Sc
G, new, ov, NT = Sc.load()
L = []
say = lambda s: (print(s), L.append(s))
cen = G[G.src == 'census']
pool = cen[(cen.f_HL.fillna('') != 'S') & (cen.f_Aster.fillna('') != 'S')]
say(f"census notices {cen[['coin','T']].drop_duplicates().shape[0]}; not on HL/Aster at T: {pool[['coin','T']].drop_duplicates().shape[0]}")
say("status of those notices per venue: " + str(pool.groupby(['venue', 'status']).size().unstack(fill_value=0).to_dict('index')))
yr = lambda d: pd.to_datetime(d['T'], unit='ms').dt.year
for v in Sc.VEN:
    n = new[new.venue == v]; o = ov[ov.venue == v]
    say(f"C2200 {v}: NEW {len(n)} (2025 {(yr(n)==2025).sum()}, 2026 {(yr(n)==2026).sum()}) | OVERLAP {len(o)} (HL {(o.src=='HL').sum()}/126, Aster {(o.src=='Aster').sum()}/66)")
u = new[['coin', 'T']].drop_duplicates()
say(f"C2201 NEW union (any venue): {len(u)} events, {u.coin.nunique()} coins (2025 {(yr(u)==2025).sum()}, 2026 {(yr(u)==2026).sum()}); dup-with-HL/Aster removed: {int(G[(G.src=='census')].shape[0] and 0)}")
k = new.groupby(['coin', 'T']).venue.apply(lambda s: '+'.join(sorted(s)))
say("NEW venue combos: " + str(k.value_counts().to_dict()))
only = k[k == 'bybit']
say(f"Bybit-only NEW events: {len(only)} {list(only.index)}")
ex = pool[(pool.status == 'S')]
say(f"S but within 24h of an HL/Aster event (excluded): {ex[['coin','T']].drop_duplicates().shape[0] - len(u)}")
nn = pool.groupby(['coin', 'T']).status.apply(lambda s: ''.join(sorted(set(s))))
say(f"notices not on HL/Aster with no S venue: {(~nn.str.contains('S')).sum()} (of which any D: {nn.str.contains('D').sum()})")
open(os.path.join(Sc.OUT, 'report_step1.txt'), 'w').write('\n'.join(L) + '\n')
```
## scripts/pooled.py
```python
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
```
## scripts/prefetch.py
```python
"""Parallel cache warm-up: runs score.score_new on one venue's NEW events (no numbers printed, output discarded)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as Sc
import pandas as pd
v = sys.argv[1]
G, new, ov, NT = Sc.load()
Sc.VEN = [v]
pd.DataFrame.to_csv = lambda *a, **k: None
Sc.score_new(new[new.venue == v], NT, False)
print('prefetched', v, flush=True)
```
## scripts/score.py
```python
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
```
## scripts/venues.py
```python
"""cce4v venue helpers: first-kline (listing) discovery, 1h/4h klines and funding for OKX, Bitget, Gate, Bybit.
All fetches cache raw JSON under raw/<venue>/; an HTTP/network error is never cached as 'no data'.
Bybit's REST API is geo-blocked from this container (CloudFront 403), so Bybit uses public.bybit.com/trading daily
trade dumps (listing = first file date; bars built from trades). Gate 1h history beyond 10,000 points and Gate funding
come from download.gatedata.org monthly dumps."""
import gzip, io, json, os, re, time, zipfile
import requests

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
RAW = os.path.join(ROOT, 'raw')
H = 3600_000
DAY = 24 * H
S = requests.Session()
S.headers['User-Agent'] = 'cce4v-research'


class FetchError(Exception):
    pass


def get(url, params=None, tries=6, ok404=False):
    for k in range(tries):
        try:
            r = S.get(url, params=params, timeout=40)
            if r.status_code == 200:
                return r
            if r.status_code in (404,) and ok404:
                return None
            if r.status_code == 429 or r.status_code >= 500:
                time.sleep(1.5 * 2 ** k); continue
            if r.status_code in (400, 403, 404):
                return r  # caller inspects body
        except requests.RequestException:
            pass
        time.sleep(1.5 * 2 ** k)
    raise FetchError(url)


def cache(path, fn):
    p = os.path.join(RAW, path)
    if os.path.exists(p):
        return json.load(open(p))
    os.makedirs(os.path.dirname(p), exist_ok=True)
    x = fn()  # raises on error -> nothing cached
    json.dump(x, open(p, 'w'))
    return x


# ---------------- symbols ----------------
def okx_inst(coin): return f'{coin}-USDT-SWAP'
def bitget_sym(coin): return f'{coin}USDT'
def gate_sym(coin): return f'{coin}_USDT'
def bybit_sym(coin): return f'{coin}USDT'


def variants(coin):
    """coin as on the venue: plain, then 1000x (memes)."""
    return [coin, f'1000{coin}']


# ---------------- daily bars (listing discovery) ----------------
def okx_daily(inst):
    def f():
        out, after = [], None
        while True:
            p = dict(instId=inst, bar='1Dutc', limit=100)
            if after: p['after'] = after
            j = get('https://www.okx.com/api/v5/market/history-candles', p).json()
            if j.get('code') == '51001': return []
            if j.get('code') != '0': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            out += [[int(r[0]), float(r[1]), float(r[4]), float(r[7])] for r in d]
            nxt = d[-1][0]
            if after == nxt or len(d) < 100: break
            after = nxt; time.sleep(0.12)
        return sorted(out)
    return cache(f'okx/d1_{inst}.json', f)


def bitget_daily(sym):
    def f():
        out, end = [], int(time.time() * 1000)
        while True:
            r = get('https://api.bitget.com/api/v2/mix/market/history-candles',
                    dict(symbol=sym, productType='USDT-FUTURES', granularity='1Dutc', limit=200, endTime=end))
            j = r.json()
            if j.get('code') in ('40034', '40309') or (j.get('code') != '00000' and 'not exist' in str(j.get('msg', '')).lower()): return []
            if j.get('code') != '00000': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            rows = [[int(x[0]), float(x[1]), float(x[4]), float(x[6])] for x in d]
            new = [x for x in rows if not out or x[0] < out[0][0]]
            if not new: break
            out = sorted(new) + out
            end = min(x[0] for x in rows) - 1; time.sleep(0.12)
        return out
    return cache(f'bitget/d1_{sym}.json', f)


def gate_daily(sym):
    def f():
        r = get('https://api.gateio.ws/api/v4/futures/usdt/candlesticks',
                dict(contract=sym, interval='1d', **{'from': 1672531200, 'to': int(time.time())}))
        j = r.json()
        if isinstance(j, dict):
            if 'not found' in str(j).lower() or j.get('label') in ('CONTRACT_NOT_FOUND', 'INVALID_CONTRACT'): return []
            raise FetchError(str(j)[:200])
        return sorted([[int(x['t']) * 1000, float(x['o']), float(x['c']), float(x.get('sum') or 0)] for x in j])
    return cache(f'gate/d1_{sym}.json', f)


def bybit_days(sym):
    """sorted list of 'YYYY-MM-DD' with a trade dump; [] if the symbol has no directory."""
    def f():
        r = get(f'https://public.bybit.com/trading/{sym}/', ok404=True)
        if r is None or r.status_code == 404: return []
        if r.status_code != 200: raise FetchError(sym)
        return sorted(re.findall(rf'{sym}(\d{{4}}-\d{{2}}-\d{{2}})\.csv\.gz', r.text))
    return cache(f'bybit/days_{sym}.json', f)


# ---------------- 1h bars ----------------
def okx_1h(inst, a, b):
    """1h bars with open in [a, b); OKX history-candles pages backwards from 'after'."""
    def f():
        out, after = [], b
        while after > a:
            j = get('https://www.okx.com/api/v5/market/history-candles', dict(instId=inst, bar='1H', limit=100, after=after)).json()
            if j.get('code') == '51001': return []
            if j.get('code') != '0': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            out += [[int(r[0]), float(r[1]), float(r[2]), float(r[3]), float(r[4]), float(r[7])] for r in d if r[8] == '1']
            nxt = int(d[-1][0])
            if nxt >= after: break
            after = nxt; time.sleep(0.11)
        return sorted({r[0]: r for r in out if a <= r[0] < b}.values())
    return cache(f'okx/h1_{inst}_{a}_{b}.json', f)


def bitget_1h(sym, a, b):
    def f():
        out, end = [], b
        while end > a:
            j = get('https://api.bitget.com/api/v2/mix/market/history-candles',
                    dict(symbol=sym, productType='USDT-FUTURES', granularity='1H', limit=200, endTime=end)).json()
            if j.get('code') != '00000': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            rows = [[int(x[0]), float(x[1]), float(x[2]), float(x[3]), float(x[4]), float(x[6])] for x in d]
            out += rows
            mn = min(r[0] for r in rows)
            if mn - 1 >= end: break
            end = mn - 1; time.sleep(0.11)
        return sorted({r[0]: r for r in out if a <= r[0] < b}.values())
    return cache(f'bitget/h1_{sym}_{a}_{b}.json', f)


def _gatedata(kind, sym, ym):
    r = get(f'https://download.gatedata.org/futures_usdt/{kind}/{ym}/{sym}-{ym}.csv.gz', ok404=True)
    if r is None or r.status_code == 404: return None
    if r.status_code != 200: raise FetchError(kind + sym + ym)
    return gzip.decompress(r.content).decode().strip().splitlines()


def months(a, b):
    import datetime as dt
    d = dt.datetime.utcfromtimestamp(a / 1000).replace(day=1)
    e = dt.datetime.utcfromtimestamp(b / 1000)
    out = []
    while d <= e:
        out.append(d.strftime('%Y%m'))
        d = (d.replace(day=28) + dt.timedelta(days=4)).replace(day=1)
    return out


def gate_1h(sym, a, b):
    """API for the last ~10,000 hours, gatedata monthly dumps before that. rows [t,o,h,l,c,quote_vol]."""
    def f():
        out = []
        lim = int(time.time() * 1000) - 9900 * H
        if a < lim:
            for ym in months(a, min(b, lim + 40 * DAY)):
                L = _gatedata('candlesticks_1h', sym, ym)
                for ln in (L or []):
                    x = ln.split(',')
                    try: t = int(float(x[0])) * 1000
                    except ValueError: continue
                    # gatedata columns: timestamp, volume, close, high, low, open, (amount)
                    out.append([t, float(x[5]), float(x[3]), float(x[4]), float(x[2]), float(x[6]) if len(x) > 6 else float('nan')])
        s = -(-max(a, lim) // H) * H  # A1 (review must-fix 4): align to the hour so page joins lose no bar
        while s < b:
            e = min(b, s + 1900 * H)
            j = get('https://api.gateio.ws/api/v4/futures/usdt/candlesticks',
                    dict(contract=sym, interval='1h', **{'from': s // 1000, 'to': e // 1000})).json()
            if isinstance(j, dict): raise FetchError(str(j)[:200])
            out += [[int(x['t']) * 1000, float(x['o']), float(x['h']), float(x['l']), float(x['c']), float(x.get('sum') or 0)] for x in j]
            s = e + H; time.sleep(0.11)
        return sorted({r[0]: r for r in out if a <= r[0] < b}.values())
    return cache(f'gate/h1_{sym}_{a}_{b}.json', f)


def bybit_1h(sym, a, b):
    """1h OHLC + quote volume from daily trade dumps (timestamp s, price, size)."""
    import datetime as dt
    def f():
        bars = {}
        d = dt.datetime.utcfromtimestamp(a / 1000).date()
        e = dt.datetime.utcfromtimestamp((b - 1) / 1000).date()
        while d <= e:
            r = get(f'https://public.bybit.com/trading/{sym}/{sym}{d.isoformat()}.csv.gz', ok404=True)
            if r is not None and r.status_code == 200:
                L = gzip.decompress(r.content).decode().splitlines()
                hdr = L[0].split(',')
                it, ip, iz = hdr.index('timestamp'), hdr.index('price'), hdr.index('size')
                rows = []
                for ln in L[1:]:
                    x = ln.split(',')
                    ts = float(x[it]); ts = ts / 1000 if ts > 1e11 else ts
                    rows.append((ts, float(x[ip]), float(x[iz])))
                rows.sort()
                for ts, p, z in rows:
                    t = int(ts * 1000) // H * H
                    if not (a <= t < b): continue
                    if t not in bars: bars[t] = [t, p, p, p, p, 0.0]
                    br = bars[t]; br[2] = max(br[2], p); br[3] = min(br[3], p); br[4] = p; br[5] += p * z
            elif r is not None and r.status_code != 404:
                raise FetchError(sym + str(d))
            d += dt.timedelta(days=1)
        return [bars[t] for t in sorted(bars)]
    return cache(f'bybit/h1_{sym}_{a}_{b}.json', f)


def bybit_first_trade(sym, day):
    def f():
        r = get(f'https://public.bybit.com/trading/{sym}/{sym}{day}.csv.gz', ok404=True)
        if r is None or r.status_code != 200: raise FetchError(sym + day)
        L = gzip.decompress(r.content).decode().splitlines()
        it = L[0].split(',').index('timestamp')
        return min(int(float(ln.split(',')[it]) * 1000) for ln in L[1:])
    return cache(f'bybit/first_{sym}_{day}.json', f)


# ---------------- funding ----------------
def okx_funding(inst, a, b):
    """OKX REST serves ~3 months only; older returns []. rows [t, rate]."""
    def f():
        out, after = [], b
        while True:
            j = get('https://www.okx.com/api/v5/public/funding-rate-history', dict(instId=inst, limit=100, after=after)).json()
            if j.get('code') == '51001': return []
            if j.get('code') != '0': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            out += [[int(r['fundingTime']), float(r['realizedRate'] or r['fundingRate'])] for r in d]
            nxt = int(d[-1]['fundingTime'])
            if nxt <= a or nxt >= after: break
            after = nxt; time.sleep(0.11)
        return sorted({r[0]: r for r in out if a <= r[0] < b}.values())
    return cache(f'okx/fu_{inst}_{a}_{b}.json', f)


def bitget_funding(sym):
    """full history (pageNo <= 100, pageSize 100). rows [t, rate]."""
    def f():
        out = []
        for pg in range(1, 101):
            j = get('https://api.bitget.com/api/v2/mix/market/history-fund-rate',
                    dict(symbol=sym, productType='USDT-FUTURES', pageSize=100, pageNo=pg)).json()
            if j.get('code') != '00000': raise FetchError(str(j)[:200])
            d = j['data']
            if not d: break
            out += [[int(r['fundingTime']), float(r['fundingRate'])] for r in d]
            if len(d) < 100: break
            time.sleep(0.11)
        return sorted({r[0]: r for r in out}.values())
    return cache(f'bitget/fu_{sym}.json', f)


def gate_funding(sym, a, b):
    """gatedata funding_applies dumps (monthly) + REST for the recent part. rows [t, rate]."""
    def f():
        out = []
        for ym in months(a, b):
            L = _gatedata('funding_applies', sym, ym)
            for ln in (L or []):
                x = ln.split(',')
                try: out.append([int(float(x[0])) * 1000, float(x[1])])
                except (ValueError, IndexError): continue
        j = get('https://api.gateio.ws/api/v4/futures/usdt/funding_rate', dict(contract=sym, limit=1000)).json()
        if not isinstance(j, list):
            raise FetchError('gate funding ' + str(j)[:120])  # A1 (review must-fix 5)
        out += [[int(r['t']) * 1000, float(r['r'])] for r in j]
        return sorted({r[0]: r for r in out if a <= r[0] < b}.values())
    return cache(f'gate/fu_{sym}_{a}_{b}.json', f)
```
