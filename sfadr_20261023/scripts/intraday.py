import yfinance as yf, pandas as pd, sys, os, time
OUT = sys.argv[1]; os.makedirs(OUT, exist_ok=True)
T = ["TSM","BABA","JD","BIDU","NTES","SONY","TM","HMC","MUFG","SMFG","INFY","HDB","IBN","KB","SHG","PKX","SPY"]
for iv, per in (("1h", "730d"), ("5m", "60d")):
    for t in T:
        fn = os.path.join(OUT, f"{t}_{iv}.csv")
        if os.path.exists(fn): continue
        for k in range(4):
            try:
                df = yf.Ticker(t).history(period=per, interval=iv, auto_adjust=False, prepost=False)
                if len(df): break
            except Exception as e: print(t, e)
            time.sleep(3 * (k + 1))
        df.index = df.index.tz_convert("America/New_York").tz_localize(None)
        df.to_csv(fn); print(t, iv, len(df), df.index.min(), df.index.max()); time.sleep(1)
