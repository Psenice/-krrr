"""Parallel cache warm-up: runs score.score_new on one venue's NEW events (no numbers printed, output discarded)."""
import os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import score as Sc
import pandas as pd
v = sys.argv[1]
G, new, ov, NT = Sc.load()
Sc.VEN = [v]
pd.DataFrame.to_csv = lambda *a, **k: None
Sc.score_new(new[new.venue == v], NT, False)
print('prefetched', v, flush=True)
