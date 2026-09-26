"""Deriva 24h (diaria) sobre campeon: banda leve a favor vs parabolico/contra."""
import csv, os
import requests
import numpy as np
BASE = r"C:\Users\jhonv\Downloads\mosca-unified"
M = list(csv.DictReader(open(os.path.join(BASE, "manifests", "photos_full.csv"))))
D = np.load(os.path.join(BASE, "data", "klines_cache.npz"))
F = "https://fapi.binance.com"
daily = {}
syms = sorted({r["symbol"] for r in M})
for s in syms:
    r = requests.get(F + "/fapi/v1/klines", params={"symbol": s, "interval": "1d", "limit": 400}, timeout=20)
    r.raise_for_status()
    k = r.json()
    daily[s] = (np.array([x[0] for x in k]), np.array([float(x[4]) for x in k]))
    print(s, len(k), flush=True)
TO = 32
EFF = np.array([float(r["eff"]) for r in M]); ALP = np.array([float(r["alpha"]) for r in M])
SIDE = np.array([r["side"] for r in M]); SPLIT = np.array([r["split"] for r in M])
FB = np.zeros(len(M)); FV = np.zeros(len(M)); II = np.zeros(len(M), int); DR = np.zeros(len(M))
for n, r in enumerate(M):
    A = D[r["symbol"]]; ts = A[:, 0]; j = np.searchsorted(ts, int(r["ts"])); II[n] = j
    sgn = 1 if r["side"] == "1" else -1
    FB[n] = (A[j+1, 4] - A[j+1, 1]) / A[j+1, 1] * 100 * sgn
    FV[n] = A[j+1, 5] / (np.mean(A[max(0, j-19):j+1, 5]) + 1e-9)
    dts, dc = daily[r["symbol"]]
    k = np.searchsorted(dts, int(r["ts"]), side="right") - 1
    DR[n] = (dc[k] / dc[k-1] - 1) * 100 if k >= 1 else 0
base = (SIDE == "1") & (EFF >= 0.45) & (np.abs(ALP) >= 1.5) & (~((FB < -0.3) & (FV >= 1.2)))
def run(mask, tag):
    idx = np.where(mask)[0]; W = []; R = []
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
        W.append(w); R.append(R_)
    W = np.array(W); R = np.array(R)
    print(f"{tag}: n={len(R)} win={W.mean()*100:.1f}% avg={R.mean():+.3f} tot={R.sum():+.0f}", flush=True)
run(base, "base")
run(base & (DR >= 0) & (DR <= 12), "deriva-leve-alcista[0,+12]")
run(base & (DR >= 0) & (DR <= 8), "deriva-leve[0,+8]")
run(base & (DR > 12), "parabolico>12")
run(base & (DR < 0), "contra-tendencia<0")
