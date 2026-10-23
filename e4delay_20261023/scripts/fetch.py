"""Binance USDT-M 1h klines + funding from data.binance.vision for each event coin, window [T-100d, T+100d]
(placebo needs +-90 d). Monthly files where published, else daily klines. Writes raw/k/<SYM>.csv, raw/f/<SYM>.csv.
Prints only coverage, never returns."""
import io, os, sys, zipfile, datetime as dt, requests, pandas as pd
from concurrent.futures import ThreadPoolExecutor
W = '/home/user/-krrr/e4delay_20261023'; R = f'{W}/raw'; B = 'https://data.binance.vision/data/futures/um'
os.makedirs(f'{R}/k', exist_ok=True); os.makedirs(f'{R}/f', exist_ok=True)
DAY = 86400000
S = requests.Session()

def get(u):
    for _ in range(4):
        try:
            r = S.get(u, timeout=60)
            if r.status_code == 404: return None
            if r.status_code == 200:
                z = zipfile.ZipFile(io.BytesIO(r.content)); return pd.read_csv(z.open(z.namelist()[0]), header=None)
        except Exception: pass
    return 'ERR'

def months(a, b):
    y, m = a.year, a.month; r = []
    while (y, m) <= (b.year, b.month):
        r.append(f'{y}-{m:02d}'); m += 1
        if m == 13: y, m = y + 1, 1
    return r

def sym_for(coin):
    c = coin[1:] if coin[:1] == 'k' and coin[1:2].isupper() else coin
    return [c + 'USDT', '1000' + c + 'USDT', '1M' + c + 'USDT']

def fetch(sym, t0, t1):
    a = dt.datetime.utcfromtimestamp(t0 / 1000); b = min(dt.datetime.utcfromtimestamp(t1 / 1000), dt.datetime(2026, 10, 22))
    K, F, missing = [], [], []
    for m in months(a, b):
        k = get(f'{B}/monthly/klines/{sym}/1h/{sym}-1h-{m}.zip')
        if isinstance(k, pd.DataFrame): K.append(k)
        else: missing.append(m)
        f = get(f'{B}/monthly/fundingRate/{sym}/{sym}-fundingRate-{m}.zip')
        if isinstance(f, pd.DataFrame): F.append(f)
    # daily fallback for missing months (unpublished or not listed yet)
    days = []
    for m in missing:
        y, mo = map(int, m.split('-')); d = dt.date(y, mo, 1)
        while d.month == mo and d <= b.date():
            if d >= a.date(): days.append(d)
            d += dt.timedelta(days=1)
    if days:
        with ThreadPoolExecutor(16) as P:
            for k in P.map(lambda d: get(f'{B}/daily/klines/{sym}/1h/{sym}-1h-{d}.zip'), days):
                if isinstance(k, pd.DataFrame): K.append(k)
    return K, F

def norm_k(K):
    k = pd.concat(K); k = k[k[0].astype(str).str.isdigit()].iloc[:, :6].astype(float); k.columns = ['t', 'o', 'h', 'l', 'c', 'v']
    k['t'] = k.t.astype('int64'); k.loc[k.t > 1e15, 't'] //= 1000
    return k.drop_duplicates('t').sort_values('t')

def norm_f(F):
    f = pd.concat(F); f = f[f[0].astype(str).str.isdigit()].iloc[:, [0, 2]]; f.columns = ['time', 'rate']; f = f.astype(float)
    f['time'] = f.time.astype('int64'); f.loc[f.time > 1e15, 'time'] //= 1000
    return f.drop_duplicates('time').sort_values('time')

def main():
    A = pd.read_csv(f'{W}/data/a_hl_pre2025.csv'); Bv = pd.read_csv(f'{W}/data/b_bnonly_2025_26.csv')
    E = pd.concat([A[['coin', 'T']], Bv[['coin', 'T']]])
    win = E.groupby('coin').T.agg(['min', 'max'])
    log = []
    def job(row):
        coin, (tmin, tmax) = row
        for sym in sym_for(coin):
            K, F = fetch(sym, tmin - 100 * DAY, tmax + 100 * DAY)
            if K:
                norm_k(K).to_csv(f'{R}/k/{coin}.csv', index=False)
                if F: norm_f(F).to_csv(f'{R}/f/{coin}.csv', index=False)
                return (coin, sym, len(K), len(F))
        return (coin, None, 0, 0)
    with ThreadPoolExecutor(6) as P:
        for r in P.map(job, list(win.iterrows()) and [(c, (r['min'], r['max'])) for c, r in win.iterrows()]):
            log.append(r); print(*r, flush=True)
    pd.DataFrame(log, columns=['coin', 'sym', 'kfiles', 'ffiles']).to_csv(f'{R}/fetch_log.csv', index=False)
    # BTC not needed (unhedged, as E4)

if __name__ == '__main__':
    main()
