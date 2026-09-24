"""F3: menu diario top-K por RF + V3-limit + frontera winrate con avgR>=0 y >=5 tr/dia."""
import csv, os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
D=np.load(os.path.join(BASE,"data","klines_cache.npz"))
TO=32; N=len(M)
H=np.full((N,TO),np.nan); L=np.full((N,TO),np.nan); C=np.full((N,TO),np.nan)
PX=np.zeros(N); RR=np.zeros(N); II=np.zeros(N,int)
for n,r in enumerate(M):
    A=D[r["symbol"]]; ts=A[:,0]
    j=np.searchsorted(ts,int(r["ts"]))
    assert j<len(A) and int(ts[j])==int(r["ts"]) and j+TO<len(A)
    II[n]=j; px=A[j,4]; sgn=1 if r["side"]=="1" else -1
    rr=float(r["risk"])/100*px; PX[n]=px; RR[n]=rr
    seg=A[j+1:j+1+TO]
    H[n]=sgn*(seg[:,2]-px)/rr; L[n]=sgn*(seg[:,3]-px)/rr; C[n]=sgn*(seg[:,4]-px)/rr
A1=np.array([float(r["achg"]) for r in M]); EFF=np.array([float(r["eff"]) for r in M])
RNG=np.array([float(r["rng"]) for r in M]); RSK=np.array([float(r["risk"]) for r in M])
SP=np.array([float(r["spike"]) for r in M]); ALP=np.array([float(r["alpha"]) for r in M])
GAP=np.array([float(r["gap"]) for r in M]); V6=np.array([float(r["v6"]) for r in M])
V12=np.array([float(r["v12"]) for r in M]); V24=np.array([float(r["v24"]) for r in M])
BTC=np.array([float(r["btc4h"]) for r in M]); SIDE=np.array([1 if r["side"]=="1" else 0 for r in M])
YW=np.array([int(r["win"]) for r in M]); TS=np.array([int(r["ts"]) for r in M])
DAY=(TS//86400000)
TOP9=np.stack([np.abs(ALP),SP,RSK,RNG,EFF,V6,V12,V24,BTC],1)
trm=np.array([r["split"]=="train" for r in M])
clf=RandomForestClassifier(n_estimators=300,min_samples_leaf=60,class_weight="balanced_subsample",random_state=7,n_jobs=-1)
clf.fit(TOP9[trm],YW[trm])
P=clf.predict_proba(TOP9)[:,1]
print(f"AUC train={roc_auc_score(YW[trm],P[trm]):.3f}",flush=True)
for s in ["val","testA","testB"]:
    m=np.array([r["split"]==s for r in M])
    print(f" AUC {s}={roc_auc_score(YW[m],P[m]):.3f} win={YW[m].mean()*100:.1f}%",flush=True)
# primera vela
FB=np.zeros(N); FV=np.zeros(N)
for n,r in enumerate(M):
    A=D[r["symbol"]]; j=II[n]; sgn=1 if r["side"]=="1" else -1
    FB[n]=(A[j+1,4]-A[j+1,1])/A[j+1,1]*100*sgn
    FV[n]=A[j+1,5]/(np.mean(A[max(0,j-19):j+1,5])+1e-9)
def first_hit(M2,th,ge):
    m=M2>=th if ge else M2<=th
    return np.where(m.any(1),m.argmax(1)+1,TO+1)
def ev_mask_TP(mask,TP):
    Hm,Lm,Cm=H[mask],L[mask],C[mask]
    jtp=first_hit(Hm,TP,True); jsl=first_hit(Lm,-1.0,False)
    win=(jtp<jsl)&(jtp<=TO)
    R=np.where(win,TP,np.where(jsl<=TO,-1.0,Cm[:,TO-1]))
    return win,R
def ev_v3(mask,frac=0.618,TP=2.0):
    """limit al retroceso frac del rango 4h: entry=extremo -/+ frac*rango; si SL toca antes o no llena en 12 velas -> no trade"""
    idx=np.where(mask)[0]; Rs=[];W=0;F=0
    for n in idx:
        r=M[n]; A=D[r["symbol"]]; j=II[n]; sgn=1 if r["side"]=="1" else -1
        h4=np.max(A[j-15:j+1,2]); l4=np.min(A[j-15:j+1,3])
        lv=h4-(h4-l4)*frac if sgn==1 else l4+(h4-l4)*frac
        sl=A[j,4]-sgn*RR[n]
        fill=None
        for k in range(1,13):
            h,l=A[j+k,2],A[j+k,3]
            touch=(l<=lv) if sgn==1 else (h>=lv)
            dead=(l<=sl) if sgn==1 else (h>=sl)
            if touch and dead: break  # misma vela: SL primero -> invalida
            if dead: break
            if touch: fill=k; break
        if fill is None: continue
        F+=1
        rr2=abs(lv-sl); tp=lv+sgn*rr2*TP
        w=0;R=sgn*(A[j+TO,4]-lv)/rr2
        for k in range(fill,TO+1):
            h,l=A[j+k,2],A[j+k,3]
            hs=(l<=sl) if sgn==1 else (h>=sl); ht=(h>=tp) if sgn==1 else (l<=tp)
            if hs and ht: R=-1.0; break
            if hs: R=-1.0; break
            if ht: w=1; R=TP; break
        Rs.append(R); W+=w
    return (W/max(1,F)*100, np.mean(Rs) if Rs else 0, np.sum(Rs) if Rs else 0, F)
DAYS=(TS.max()-TS.min())/86400000
base=(SIDE==1)&(EFF>=0.45)&(np.abs(ALP)>=1.5)&(~((FB<-0.3)&(FV>=1.2)))
print("\n== V3-limit en filtro base ==",flush=True)
for fr in [0.5,0.618,0.75]:
    w,a,t,f=ev_v3(base,fr,2.0)
    print(f" V3 frac={fr}: fills={f} tr/dia={f/DAYS:.1f} win={w:.1f}% avgR={a:+.3f} total={t:+.0f}",flush=True)
print("\n== MENU DIARIO top-K por RF (filtro base, TP=1.0 sin BE) ==",flush=True)
cands=np.where(base)[0]
byday={}
for n in cands: byday.setdefault(DAY[n],[]).append(n)
for K in [1,3,5]:
    Sall=[]
    for d,ns in byday.items():
        ns=sorted(ns,key=lambda n:-P[n])[:K]
        Sall.extend(ns)
    win,R=ev_mask_TP(np.array(sorted(Sall)),1.0)
    print(f" top{K}/dia: dias={len(byday)} tr/dia={len(Sall)/DAYS:.1f} win={win.mean()*100:.1f}% avgR={R.mean():+.3f} total={R.sum():+.0f}",flush=True)
print("\n== FRONTERA: max win con avgR>=0 y >=5tr/dia ==",flush=True)
cands=np.where(base)[0]
best=None
for TP in [0.5,0.6,0.7,0.8,1.0,1.2,1.5]:
    for K in [1,2,3,5,99]:
        Sall=[]
        for d,ns in byday.items():
            Sall.extend(sorted(ns,key=lambda n:-P[n])[:K])
        Sall=np.array(sorted(Sall))
        if len(Sall)/DAYS<5: continue
        win,R=ev_mask_TP(Sall,TP)
        w,a=win.mean()*100,R.mean()
        if a>=0 and (best is None or w>best[0]):
            best=(w,a,R.sum(),TP,K,len(Sall)/DAYS)
print(f" MEJOR: win={best[0]:.1f}% avgR={best[1]:+.3f} total={best[2]:+.0f} TP={best[3]} topK={best[4]} tr/dia={best[5]:.1f}",flush=True)
