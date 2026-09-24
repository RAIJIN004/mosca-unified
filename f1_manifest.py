"""F1: manifiesto full 120 dias x 25 monedas + features + splits + cuota foto estratificada."""
import json, os, csv, time
import requests
import numpy as np
BASE=os.path.dirname(os.path.abspath(__file__))
CFG=json.load(open(os.path.join(BASE,"config.json")))
F="https://fapi.binance.com"
N15=11520; N1H=2880
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
print("BTC...",flush=True)
btc15=get_klines("BTCUSDT","15m",N15)
btc_ts=np.array([k[0] for k in btc15]); btc_c=np.array([float(k[4]) for k in btc15],float)
coins=CFG["train_coins"]+CFG["test_coins_unseen"]
all_ts=[]
rows=[]
for sym in coins:
    ks=get_klines(sym,"15m",N15); kh=get_klines(sym,"1h",N1H)
    closes=np.array([float(k[4]) for k in ks],float); highs=np.array([float(k[2]) for k in ks],float)
    lows=np.array([float(k[3]) for k in ks],float); vols=np.array([float(k[5])*float(k[4]) for k in ks],float)
    ts=np.array([k[0] for k in ks])
    hvol=np.array([float(k[5])*float(k[4]) for k in kh],float); hts=np.array([k[0] for k in kh])
    N=len(ks); W=16; n0=len(rows)
    for i in range(W+25,N-33):
        c0=closes[i-W]; c1=closes[i]
        chg=(c1/c0-1)*100
        path=np.sum(np.abs(np.diff(closes[i-W:i+1])))
        eff=abs(c1-c0)/path if path>0 else 0
        if eff<0.35: continue
        h4=np.max(highs[i-W+1:i+1]); l4=np.min(lows[i-W+1:i+1]); px=c1
        side=0
        if chg>=2.0 and (h4-px)/h4*100<=3.0: side=1
        elif chg<=-2.0 and (px-l4)/l4*100<=3.0: side=-1
        else: continue
        rng_=(h4-l4)/px*100
        if rng_<1.5: continue
        sl=l4 if side==1 else h4
        risk=abs(px-sl)/px*100
        if risk<=0.05 or risk>8: continue
        qv=vols[i-16:i+1]; base=np.mean(qv[:-4]); spike=np.mean(qv[-4:])/base if base>0 else 0
        t=int(ts[i]); bi=np.searchsorted(btc_ts,t,side="right")-1
        if bi<17: continue
        btc4h=(btc_c[bi]/btc_c[bi-16]-1)*100; alpha=chg-btc4h
        streak=0
        for j in range(i,max(i-8,0),-1):
            o=float(ks[j][1]); c=float(ks[j][4])
            if side==1 and c>o: streak+=1
            elif side==-1 and c<o: streak+=1
            else: break
        w=closes[i-19:i+1]; e=w[0]; a=2/21
        for c in w[1:]: e=c*a+e*(1-a)
        gap=(px-e)/e*100*side
        hi=np.searchsorted(hts,t,side="right")-1
        if hi>=274:
            def mult(h):
                wv=hvol[hi-h+1:hi+1]; bv=hvol[hi-h-200:hi-h]
                return float(np.mean(wv)/np.mean(bv)) if np.mean(bv)>0 else 0
            v24,v12,v6=mult(24),mult(12),mult(6)
        else: v24=v12=v6=0
        ladder=int(v6>v12>v24)
        fh=highs[i+1:i+33]; fl=lows[i+1:i+33]; fc=closes[i+1:i+33]
        sgn=side; rr=abs(px-sl); tp=px+sgn*rr*2
        win=0; R=sgn*(fc[-1]-px)/rr; tb=32
        for j in range(32):
            h=fh[j]; l=fl[j]
            hs=(l<=sl) if side==1 else (h>=sl); ht=(h>=tp) if side==1 else (l<=tp)
            if hs and ht: win=0; R=-1.0; tb=j+1; break
            if hs: win=0; R=-1.0; tb=j+1; break
            if ht: win=1; R=2.0; tb=j+1; break
        btc_reg="bull" if btc4h>2 else ("bear" if btc4h<-2 else "neutral")
        alt_reg=("alcista" if side==1 else "bajista") if streak>=2 else "neutral"
        rows.append([sym,t,side,round(float(chg),2),round(float(eff),3),round(float(rng_),2),round(float(risk),2),
                     round(min(float(spike),5),2),round(float(alpha),2),round(float(gap),2),round(float(v6),2),
                     round(float(v12),2),round(float(v24),2),ladder,round(float(btc4h),2),btc_reg,alt_reg,win,round(float(R),3),tb,i,streak])
    print(f"{sym}: +{len(rows)-n0} total={len(rows)}",flush=True)
rows.sort(key=lambda r:r[1])
cut=rows[int(len(rows)*0.8)][1]
print(f"N={len(rows)} cut={cut}")
# split + cuota foto estratificada (train 120/celda, val 30, testA 40, testB 40)
QUOTA={"train":120,"val":30,"testA":40,"testB":40}
cnt={}; photo_flags=[]
for r in rows:
    sym,t=r[0],r[1]
    unseen=sym in CFG["test_coins_unseen"]; future=t>cut
    split="testA" if (unseen and future) else ("testB" if unseen else ("val" if future else "train"))
    key=(split,r[15],r[16])
    take=cnt.get(key,0)<QUOTA[split]
    cnt[key]=cnt.get(key,0)+1
    photo_flags.append(split if take else "")
with open(os.path.join(BASE,"manifests","photos_full.csv"),"w",newline="") as f:
    w=csv.writer(f)
    w.writerow(["id","symbol","ts","split","side","achg","eff","rng","risk","spike","alpha","gap","v6","v12","v24","ladder","btc4h","btc_reg","alt_reg","win","R","tb","idx","streak","photo_split"])
    for n,r in enumerate(rows):
        sym,t=r[0],r[1]
        unseen=sym in CFG["test_coins_unseen"]; future=t>cut
        split="testA" if (unseen and future) else ("testB" if unseen else ("val" if future else "train"))
        w.writerow([f"s{n}",sym,t,split]+r[2:]+[photo_flags[n]])
print("celdas:",{k:v for k,v in sorted(cnt.items())})
print("fotos cuota:",sum(1 for p in photo_flags if p))
