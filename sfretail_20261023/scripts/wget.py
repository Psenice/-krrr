import requests, time
UA={"User-Agent":"sfretail-research/1.0 (github.com/psenice; academic backtest)"}
def get(url,params=None,tries=12):
    for i in range(tries):
        r=requests.get(url,params=params,headers=UA,timeout=60)
        if r.status_code==200: time.sleep(1.0); return r
        if r.status_code==404: return r
        w=float(r.headers.get("retry-after",3)); time.sleep(min(max(w,2),30))
    raise RuntimeError(f"failed {url} {params} {r.status_code}")
