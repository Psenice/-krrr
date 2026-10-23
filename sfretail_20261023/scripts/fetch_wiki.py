import json, os, sys, urllib.parse, pandas as pd
sys.path.insert(0,'scripts'); from wget import get
# candidate titles per ticker: current article title first, then former titles of the SAME article (page moves)
C={"TSLA":["Tesla, Inc.","Tesla Motors"],"NVDA":["Nvidia"],"AMD":["AMD","Advanced Micro Devices"],"PLTR":["Palantir Technologies"],"GME":["GameStop"],"AMC":["AMC Theatres"],"SOFI":["SoFi","Social Finance"],"RIVN":["Rivian","Rivian Automotive"],"LCID":["Lucid Motors","Lucid Group","Atieva"],"NIO":["Nio Inc.","NIO (car company)","NextEV","Nio (car company)"],"MSTR":["MicroStrategy","Strategy (company)","Strategy Inc","Strategy Inc."],"COIN":["Coinbase"],"HOOD":["Robinhood Markets","Robinhood (company)"],"SMCI":["Supermicro","Super Micro Computer"],"ARM":["Arm Holdings","ARM Holdings","Arm Ltd"],"AAPL":["Apple Inc."],"AMZN":["Amazon (company)","Amazon.com"],"META":["Meta Platforms","Facebook, Inc."],"NFLX":["Netflix"],"BABA":["Alibaba Group","Alibaba Group Holding"],"SNAP":["Snap Inc."],"UBER":["Uber","Uber (company)"],"SHOP":["Shopify"],"RBLX":["Roblox Corporation"],"DKNG":["DraftKings"],"PLUG":["Plug Power"],"MARA":["MARA Holdings","Marathon Digital Holdings","Marathon Patent Group"],"RIOT":["Riot Platforms","Riot Blockchain"],"BB":["BlackBerry Limited","BlackBerry Ltd"],"CVNA":["Carvana"],"UPST":["Upstart (company)","Upstart Holdings","Upstart Network"],"AFRM":["Affirm (company)","Affirm Holdings"],"AI":["C3.ai","C3 IoT","C3.ai (company)"],"IONQ":["IonQ"],"RKLB":["Rocket Lab","Rocket Lab USA"],"SOUN":["SoundHound","SoundHound AI"],"CHWY":["Chewy (company)","Chewy, Inc.","Chewy.com"],"PTON":["Peloton Interactive","Peloton (company)"],"ZM":["Zoom Communications","Zoom Video Communications"],"DJT":["Trump Media & Technology Group"]}
if __name__=="__main__":
    os.makedirs("data/wiki_raw",exist_ok=True)
    B="https://wikimedia.org/api/rest_v1/metrics/pageviews/per-article/en.wikipedia/all-access/user/{}/daily/20150701/20261022"
    for t,titles in C.items():
        for ti in titles:
            fn=f"data/wiki_raw/{t}__{ti.replace('/','_').replace(' ','_')}.json"
            if os.path.exists(fn): continue
            r=get(B.format(urllib.parse.quote(ti.replace(' ','_'),safe='')))
            if r.status_code==404: print(t,ti,"404",flush=True); json.dump({"items":[]},open(fn,"w")); continue
            it=r.json()["items"]; json.dump(r.json(),open(fn,"w"))
            s=pd.Series({x["timestamp"][:8]:x["views"] for x in it})
            print(t,ti,len(it),s.index.min() if len(s) else None,int(s.median()) if len(s) else None,flush=True)
