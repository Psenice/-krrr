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
