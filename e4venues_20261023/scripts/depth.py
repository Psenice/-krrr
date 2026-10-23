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
