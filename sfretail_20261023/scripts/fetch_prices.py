import yfinance as yf, pandas as pd, sys
T="TSLA NVDA AMD PLTR GME AMC SOFI RIVN LCID NIO MSTR COIN HOOD SMCI ARM AAPL AMZN META NFLX BABA SNAP UBER SHOP RBLX DKNG PLUG MARA RIOT BB CVNA UPST AFRM AI IONQ RKLB SOUN CHWY PTON ZM DJT SPY".split()
for t in T:
    d=yf.download(t,start="2015-01-01",end="2026-10-23",auto_adjust=False,progress=False,actions=True)
    if isinstance(d.columns,pd.MultiIndex): d.columns=d.columns.get_level_values(0)
    d.to_csv(f"data/px_{t}.csv"); print(t,len(d),d.index.min().date() if len(d) else None,d.index.max().date() if len(d) else None,flush=True)
