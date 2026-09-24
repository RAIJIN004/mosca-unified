"""F4 remate: V3-deep x TP x menu top-K. Objetivo win max con avgR>0 y >=3 tr/dia."""
import csv, os
import numpy as np
from sklearn.ensemble import RandomForestClassifier
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
D=np.load(os.path.join(BASE,"data","klines_cache.npz"))
TO=32; N=len(M)
II=np.zeros(N,int)
for n,r in enumerate(M):
    ts=D[r["symbol"]][:,0]; j=np.searchsorted(ts,int(r["ts"])); II[n]=j
EFF=np.array([float(r["eff"]) for r in M]); ALP=np.array([float(r["alpha"]) for r in M])
SIDE=np.array([1 if r["side"]=="1" else 0 for r in M]); TS=np.array([int(r["ts"]) for r in M])
DAY=TS//86400000; DAYS=(TS.max()-TS.min())/86400000
TOP9=np.stack([np.abs(ALP),np.array([float(r["spike"]) for r in M]),np.array([float(r["risk"]) for r in M]),
               np.array([float(r["rng"]) for r in M]),EFF,np.array([float(r["v6"]) for r in M]),
               np.array([float(r["v12"]) for r in M]),np.array([float(r["v24"]) for r in M]),
               np.array([float(r["btc4h"]) for r in M])],1)
YW=np.array([int(r["win"]) for r in M])
trm=np.array([r["split"]=="train" for r in M])
clf=RandomForestClassifier(n_estimators=300,min_samples_leaf=60,class_weight="balanced_subsample",random_state=7,n_jobs=-1)
clf.fit(TOP9[trm],YW[trm]); P=clf.predict_proba(TOP9)[:,1]
FB=np.zeros(N); FV=np.zeros(N)
for n,r in enumerate(M):
    A=D[r["symbol"]]; j=II[n]; sgn=1 if r["side"]=="1" else -1
    FB[n]=(A[j+1,4]-A[j+1,1])/A[j+1,1]*100*sgn
    FV[n]=A[j+1,5]/(np.mean(A[max(0,j-19):j+1,5])+1e-9)
base=np.where((SIDE==1)&(EFF>=0.45)&(np.abs(ALP)>=1.5)&(~((FB<-0.3)&(FV>=1.2))))[0]
def v3_batch(idxs,frac,TP):
    out=[]
    for n in idxs:
        r=M[n]; A=D[r["symbol"]]; j=II[n]; sgn=1 if r["side"]=="1" else -1
        h4=np.max(A[j-15:j+1,2]); l4=np.min(A[j-15:j+1,3])
        lv=h4-(h4-l4)*frac if sgn==1 else l4+(h4-l4)*frac
        sl=PX_(n,A,j,sgn)
        fill=None
        for k in range(1,13):
            h,l=A[j+k,2],A[j+k,3]
            touch=(l<=lv) if sgn==1 else (h>=lv); dead=(l<=sl) if sgn==1 else (h>=sl)
            if touch and dead: break
            if dead: break
            if touch: fill=k; break
        if fill is None: continue
        rr2=abs(lv-sl); tp=lv+sgn*rr2*TP; w=0;R=sgn*(A[j+TO,4]-lv)/rr2
        for k in range(fill,TO+1):
            h,l=A[j+k,2],A[j+k,3]
            hs=(l<=sl) if sgn==1 else (h>=sl); ht=(h>=tp) if sgn==1 else (l<=tp)
            if hs and ht: R=-1.0; break
            if hs: R=-1.0; break
            if ht: w=1; R=TP; break
        out.append((n,w,R))
    return out
def PX_(n,A,j,sgn):
    return A[j,4]-sgn*float(M[n]["risk"])/100*A[j,4]
print("== V3 x TP (filtro base) ==",flush=True)
res={}
for fr in [0.618,0.7,0.75,0.8]:
    for TP in [1.0,1.5,2.0]:
        o=v3_batch(base,fr,TP)
        if o:
            W=np.mean([x[1] for x in o])*100; A_=np.mean([x[2] for x in o]); T_=np.sum([x[2] for x in o])
            print(f" frac={fr} TP={TP}: fills={len(o)} tr/dia={len(o)/DAYS:.1f} win={W:.1f}% avgR={A_:+.3f} total={T_:+.0f}",flush=True)
            res[(fr,TP)]=o
print("\n== MENU top-K/dia sobre V3 fills (frac=0.75, TP=1.5) ==",flush=True)
o=res.get((0.75,1.5),v3_batch(base,0.75,1.5))
byday={}
for n,w,R in o: byday.setdefault(DAY[n],[]).append((n,w,R))
for K in [1,2,3,5,99]:
    S=[]
    for d,ns in byday.items(): S.extend(sorted(ns,key=lambda t:-P[t[0]])[:K])
    W=np.mean([x[1] for x in S])*100; A_=np.mean([x[2] for x in S]); T_=np.sum([x[2] for x in S])
    print(f" top{K}: tr/dia={len(S)/DAYS:.1f} win={W:.1f}% avgR={A_:+.3f} total={T_:+.0f}",flush=True)
