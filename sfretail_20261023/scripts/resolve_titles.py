import requests, json, re, time, sys
sys.path.insert(0,'scripts'); from wget import get
UA={"User-Agent":"sfretail-research/1.0 (github.com/psenice; backtest research)"}
G={"TSLA":"Tesla, Inc.","NVDA":"Nvidia","AMD":"AMD","PLTR":"Palantir Technologies","GME":"GameStop","AMC":"AMC Theatres","SOFI":"SoFi","RIVN":"Rivian","LCID":"Lucid Motors","NIO":"Nio Inc.","MSTR":"MicroStrategy","COIN":"Coinbase","HOOD":"Robinhood Markets","SMCI":"Supermicro","ARM":"Arm Holdings","AAPL":"Apple Inc.","AMZN":"Amazon (company)","META":"Meta Platforms","NFLX":"Netflix","BABA":"Alibaba Group","SNAP":"Snap Inc.","UBER":"Uber","SHOP":"Shopify","RBLX":"Roblox Corporation","DKNG":"DraftKings","PLUG":"Plug Power","MARA":"MARA Holdings","RIOT":"Riot Platforms","BB":"BlackBerry Limited","CVNA":"Carvana","UPST":"Upstart Holdings","AFRM":"Affirm Holdings","AI":"C3.ai","IONQ":"IonQ","RKLB":"Rocket Lab","SOUN":"SoundHound","CHWY":"Chewy, Inc.","PTON":"Peloton Interactive","ZM":"Zoom Communications","DJT":"Trump Media & Technology Group"}
API="https://en.wikipedia.org/w/api.php"
out={}
for t,g in G.items():
    r=get(API,{"action":"query","titles":g,"redirects":1,"format":"json","prop":"info"}).json()
    pages=r["query"]["pages"]; p=list(pages.values())[0]
    cur=p.get("title"); missing="missing" in p
    # move history from revision comments
    olds=set(); cont={}
    while not missing:
        q={"action":"query","prop":"revisions","titles":cur,"rvprop":"comment|timestamp","rvlimit":500,"rvstart":"2015-01-01T00:00:00Z","rvdir":"newer","format":"json"}; q.update(cont)
        rr=get(API,q).json()
        for pg in rr["query"]["pages"].values():
            for rv in pg.get("revisions",[]):
                c=rv.get("comment","")
                m=re.search(r"moved page \[\[([^\]]+)\]\] to \[\[([^\]]+)\]\]",c)
                if m: olds.add((m.group(1),m.group(2),rv["timestamp"][:10]))
        if "continue" in rr: cont=rr["continue"]
        else: break
    out[t]={"guess":g,"title":cur,"missing":missing,"moves":sorted(olds,key=lambda x:x[2])}
    print(t,cur,missing,out[t]["moves"],flush=True)
json.dump(out,open("data/titles.json","w"),indent=1)
