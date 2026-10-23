# download yfinance daily OHLC (unadjusted for splits only = yfinance auto_adjust=False) for all legs
import yfinance as yf, pandas as pd, time, sys, os
OUT = sys.argv[1]
PAIRS = [("TSM","2330.TW"),("BABA","9988.HK"),("JD","9618.HK"),("BIDU","9888.HK"),("NTES","9999.HK"),
 ("SONY","6758.T"),("TM","7203.T"),("HMC","7267.T"),("MUFG","8306.T"),("SMFG","8316.T"),
 ("INFY","INFY.NS"),("HDB","HDFCBANK.NS"),("IBN","ICICIBANK.NS"),("KB","105560.KS"),("SHG","055550.KS"),("PKX","005490.KS")]
EXTRA = ["TWD=X","HKD=X","JPY=X","INR=X","KRW=X","SPY","EWJ","EWY","FXI","EWT","INDA"]
tick = [a for a,_ in PAIRS]+[h for _,h in PAIRS]+EXTRA
for t in tick:
    fn = os.path.join(OUT, t.replace("=","_")+".csv")
    if os.path.exists(fn): continue
    for k in range(5):
        try:
            df = yf.Ticker(t).history(start="2011-06-01", end="2026-10-23", interval="1d", auto_adjust=False, actions=True)
            if len(df) > 100: break
        except Exception as e: print(t, e)
        time.sleep(3*(k+1))
    df.index = df.index.tz_localize(None).normalize()
    df.to_csv(fn); print(t, len(df), df.index.min().date(), df.index.max().date()); time.sleep(1)
