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
