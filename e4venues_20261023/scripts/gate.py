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
