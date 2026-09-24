"""F1 render: fotos triple-panel con cuota, cache klines, resume, localizacion por timestamp (anti-shift)."""
import json, os, csv, time, hashlib
import requests
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
from concurrent.futures import ThreadPoolExecutor
BASE=os.path.dirname(os.path.abspath(__file__))
CFG=json.load(open(os.path.join(BASE,"config.json")))
F="https://fapi.binance.com"
CACHE=os.path.join(BASE,"data","klines_cache.npz")
def get_klines(symbol, interval, total):
    out=[]; end=None
    while len(out)<total:
        p={"symbol":symbol,"interval":interval,"limit":min(1500,total-len(out))}
        if end: p["endTime"]=end
        r=requests.get(F+"/fapi/v1/klines",params=p,timeout=25); r.raise_for_status()
        ks=r.json()
        if not ks: break
        out=ks+out; end=ks[0][0]-1
        if len(ks)<2: break
        time.sleep(0.08)
    return out
def load_cache():
    if os.path.exists(CACHE):
        d=np.load(CACHE,allow_pickle=True)
        return dict(d)
    data={}
    print("fetch+cache BTC...",flush=True)
    btc=get_klines("BTCUSDT","15m",11520)
    data["BTC"]=np.array([[k[0],float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5])*float(k[4])] for k in btc],float)
    for sym in CFG["train_coins"]+CFG["test_coins_unseen"]:
        ks=get_klines(sym,"15m",11520)
        data[sym]=np.array([[k[0],float(k[1]),float(k[2]),float(k[3]),float(k[4]),float(k[5])*float(k[4])] for k in ks],float)
        print(sym,len(ks),flush=True)
    np.savez_compressed(CACHE,**data)
    return data
DATA=load_cache()
BT=DATA["BTC"]; BTS=BT[:,0]; BCLOSE=BT[:,4]
MAN=[r for r in csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))) if r["photo_split"]]
print(f"a renderizar: {len(MAN)}",flush=True)
LOG=os.path.join(BASE,"manifests","photos_rendered.csv")
done={r["id"]:r for r in (csv.DictReader(open(LOG)) if os.path.exists(LOG) else [])}
import threading
lock=threading.Lock()
def render(r):
    if r["id"] in done and os.path.exists(os.path.join(BASE,"data","photos",r["photo_split"],done[r["id"]]["file"])):
        return ("skip",r["id"])
    A=DATA[r["symbol"]]; ts=A[:,0]
    j=np.searchsorted(ts,int(r["ts"]))
    if j>=len(ts) or int(ts[j])!=int(r["ts"]): return ("MISSING-TS",r["id"])
    i=j; px=A[i,4]
    bi=np.searchsorted(BTS,int(r["ts"]),side="right")-1
    fig=plt.figure(figsize=(8,5),dpi=70)
    g=gs.GridSpec(2,2,height_ratios=[3,1])
    ax0=fig.add_subplot(g[0,0]); ax1=fig.add_subplot(g[0,1]); ax2=fig.add_subplot(g[1,:])
    b0=max(0,bi-63)
    ax0.plot(BCLOSE[b0:bi+1],color="orange"); ax0.axvline(bi-b0,color="red",ls="--",lw=1)
    ax0.set_title(f"BTC btc4h={float(r['btc4h']):+.1f}% ({r['btc_reg']})",fontsize=9)
    a0=max(0,i-47)
    ax1.plot(A[a0:i+1,4],color="green" if r["side"]=="1" else "red")
    sl_off=float(r["risk"])/100*px
    sl=px-sl_off if r["side"]=="1" else px+sl_off
    ax1.axhline(px,color="black",ls="--",lw=1); ax1.axhline(sl,color="red",ls=":",lw=1)
    ax1.set_title(f"{r['symbol']} {'LONG' if r['side']=='1' else 'SHORT'} risk={r['risk']}%",fontsize=9)
    ax1.text(0.02,0.92,f"eff={r['eff']} rng={r['rng']}%",transform=ax1.transAxes,va="top",fontsize=7,
             bbox=dict(fc="white",alpha=0.7))
    ax2.bar(range(i-a0+1),A[a0:i+1,5],color="gray"); ax2.set_title("volumen alt (solo pasado)",fontsize=9)
    fig.suptitle(f"{r['symbol']} {r['alt_reg']} | alpha={r['alpha']} spike={r['spike']}x gap={r['gap']}% chg={r['achg']}%",fontsize=8)
    fig.tight_layout()
    fn=f"{r['id']}_{r['symbol']}_{r['ts']}.png"
    fp=os.path.join(BASE,"data","photos",r["photo_split"],fn)
    fig.savefig(fp); plt.close(fig)
    h=hashlib.sha256(open(fp,"rb").read()).hexdigest()[:16]
    with lock:
        with open(LOG,"a",newline="") as f: csv.writer(f).writerow([r["id"],r["photo_split"],fn,h])
    return ("ok",r["id"])
if not os.path.exists(LOG):
    with open(LOG,"w",newline="") as f: csv.writer(f).writerow(["id","split","file","sha"])
from collections import Counter
res=Counter(); n=0
with ThreadPoolExecutor(max_workers=4) as ex:
    for st,rid in ex.map(render,MAN):
        res[st]+=1; n+=1
        if n%200==0: print(n,dict(res),flush=True)
print("DONE",dict(res))
