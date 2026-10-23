# debug run on SHUFFLED pageviews only (no real outcomes); prints shapes and counts, not P&L
import sys, time, numpy as np; sys.path.insert(0,'scripts')
from cells import *
t0=time.time(); P=load_prices(); V=load_views(); print("loaded",V.shape,round(time.time()-t0,1))
rng=np.random.default_rng(1); Vs=shuffle_views(V,rng); Z=zscore(Vs)
t0=time.time(); o=f1f2(P,Z); print("f1f2",round(time.time()-t0,1),{k:len(v) for k,v in o.items()})
t0=time.time(); o4=f4(P,Z); print("f4",round(time.time()-t0,1),{k:len(v) for k,v in o4.items()})
OS=os_signal(P); OSs=OS.copy()
for c in OSs: 
    a=OSs[c].values.copy(); ok=np.isfinite(a); v=a[ok]; rng.shuffle(v); a[ok]=v; OSs[c]=a
t0=time.time(); o3=f3(P,OSs); print("f3",round(time.time()-t0,1),{k:len(v) for k,v in o3.items()})
s=summarize(split(o["F1_fade_h5"],"dev")); print({k:s[k] for k in ["n","per_yr","names","first","last"]})
