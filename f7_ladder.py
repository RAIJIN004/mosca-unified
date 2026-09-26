"""Valida ladder unified (v6>v12>v24, v6>=1.5) sobre campeon LONG frac=0.8 TP=1.0."""
import csv, os
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__)) if "__file__" in dir() else r"C:\Users\jhonv\Downloads\mosca-unified"
M = list(csv.DictReader(open(os.path.join(BASE, "manifests", "photos_full.csv"))))
D = np.load(os.path.join(BASE, "data", "klines_cache.npz"))
TO = 32
EFF = np.array([float(r["eff"]) for r in M]); ALP = np.array([float(r["alpha"]) for r in M])
SIDE = np.array([r["side"] for r in M]); SPLIT = np.array([r["split"] for r in M])
V6 = np.array([float(r["v6"]) for r in M]); V12 = np.array([float(r["v12"]) for r in M]); V24 = np.array([float(r["v24"]) for r in M])
LAD = np.array([int(r["ladder"]) for r in M])
FB = np.zeros(len(M)); FV = np.zeros(len(M)); II = np.zeros(len(M), int)
for n, r in enumerate(M):
    A = D[r["symbol"]]; ts = A[:, 0]; j = np.searchsorted(ts, int(r["ts"])); II[n] = j
    sgn = 1 if r["side"] == "1" else -1
    FB[n] = (A[j+1, 4] - A[j+1, 1]) / A[j+1, 1] * 100 * sgn
    FV[n] = A[j+1, 5] / (np.mean(A[max(0, j-19):j+1, 5]) + 1e-9)
base = (SIDE == "1") & (EFF >= 0.45) & (np.abs(ALP) >= 1.5) & (~((FB < -0.3) & (FV >= 1.2)))
def run(mask, tag):
    idx = np.where(mask)[0]; W = []; R = []; SP = []
    for n in idx:
        r = M[n]; A = D[r["symbol"]]; j = II[n]
        h4 = np.max(A[j-15:j+1, 2]); l4 = np.min(A[j-15:j+1, 3])
        lv = h4 - (h4 - l4) * 0.8; sl = A[j, 4] - float(r["risk"]) / 100 * A[j, 4]
        fill = None
        for k in range(1, 13):
            h, l = A[j+k, 2], A[j+k, 3]
            if l <= lv and l <= sl: break
            if l <= sl: break
            if l <= lv: fill = k; break
        if fill is None: continue
        rr2 = abs(lv - sl); tp = lv + rr2; w = 0; R_ = (A[j+TO, 4] - lv) / rr2
        for k in range(fill, TO+1):
            h, l = A[j+k, 2], A[j+k, 3]
            if l <= sl and h >= tp: R_ = -1.0; break
            if l <= sl: R_ = -1.0; break
            if h >= tp: w = 1; R_ = 1.0; break
        W.append(w); R.append(R_); SP.append(SPLIT[n])
    W = np.array(W); R = np.array(R); SP = np.array(SP)
    tot = f"win={W.mean()*100:.1f}% avg={R.mean():+.3f} tot={R.sum():+.0f} n={len(R)}"
    print(f"{tag}: {tot}", flush=True)
    for s in ["train", "val", "testA", "testB"]:
        o = SP == s
        if o.sum(): print(f"  {s}: n={o.sum()} win={W[o].mean()*100:.1f}% avg={R[o].mean():+.3f}", flush=True)
run(base, "base")
run(base & (LAD == 1), "base+ladder(v6>v12>v24)")
run(base & (LAD == 1) & (V6 >= 1.5), "base+ladder+v6>=1.5")
run(base & (LAD == 0), "base+SIN-ladder")
