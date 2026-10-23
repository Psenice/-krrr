# data gate: coverage and step checks (no outcomes)
import sys; sys.path.insert(0,'scripts')
from sflib import *
P=load_prices(); V=load_views()
rows=[]
for t in NAMES:
    px=P["O"][t].dropna()
    if t not in V: rows.append((t,0,None,None,np.nan,"NO PAGEVIEWS",len(px),str(px.index.min().date()))); continue
    s=V[t].dropna(); med=s.rolling(60,min_periods=30).median()
    r=(med/med.shift(60)).replace([np.inf,-np.inf],np.nan)
    stepmax=np.nanmax(np.maximum(r.values,1/r.values)) if r.notna().any() else np.nan
    when=r.index[np.nanargmax(np.maximum(r.values,1/r.values))].date() if r.notna().any() else None
    zero=(s==0).mean()
    rows.append((t,len(s),str(s.index.min().date()),int(s.median()),round(stepmax,1),str(when),len(px),str(px.index.min().date()),round(zero,3)))
df=pd.DataFrame(rows,columns=["name","pv_days","pv_first","pv_median","max_60d_median_step","step_at","px_days","px_first","zero_share"][:len(rows[0])])
print(df.to_string()); df.to_csv("out/data_gate_v1.csv",index=False)
