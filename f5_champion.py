"""F5: campeon frac=0.8 TP=1.0 por split + arrastre fees (0.05%/lado)."""
import csv, os
import numpy as np
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
D=np.load(os.path.join(BASE,"data","klines_cache.npz"))
TO=32
EFF=np.array([float(r["eff"]) for r in M]); ALP=np.array([float(r["alpha"]) for r in M])
SIDE=np.array([r["side"] for r in M])
FB=np.zeros(len(M)); FV=np.zeros(len(M))
II=np.zeros(len(M),int)
for n,r in enumerate(M):
    A=D[r["symbol"]]; ts=A[:,0]; j=np.searchsorted(ts,int(r["ts"])); II[n]=j
    sgn=1 if r["side"]=="1" else -1
    FB[n]=(A[j+1,4]-A[j+1,1])/A[j+1,1]*100*sgn
    FV[n]=A[j+1,5]/(np.mean(A[max(0,j-19):j+1,5])+1e-9)
base=np.where((SIDE=="1")&(EFF>=0.45)&(np.abs(ALP)>=1.5)&(~((FB<-0.3)&(FV>=1.2))))[0]
SPLIT=np.array([r["split"] for r in M])
res={s:[] for s in ["train","val","testA","testB"]}
fees=[]
for n in base:
    r=M[n]; A=D[r["symbol"]]; j=II[n]
    h4=np.max(A[j-15:j+1,2]); l4=np.min(A[j-15:j+1,3])
    lv=h4-(h4-l4)*0.8
    sl=A[j,4]-float(r["risk"])/100*A[j,4]
    fill=None
    for k in range(1,13):
        h,l=A[j+k,2],A[j+k,3]
        if l<=lv and l<=sl: break
        if l<=sl: break
        if l<=lv: fill=k; break
    if fill is None: continue
    rr2=abs(lv-sl); tp=lv+rr2*1.0; w=0;R=(A[j+TO,4]-lv)/rr2
    for k in range(fill,TO+1):
        h,l=A[j+k,2],A[j+k,3]
        if l<=sl and h>=tp: R=-1.0; break
        if l<=sl: R=-1.0; break
        if h>=tp: w=1; R=1.0; break
    res[SPLIT[n]].append((w,R))
    fees.append(0.10/(rr2/A[j,4]*100))  # costo round-trip en R (0.05%x2)
print("CAMPEON frac=0.8 TP=1.0 + filtro base LONG",flush=True)
totW=totR=totN=0
for s in ["train","val","testA","testB"]:
    o=res[s]
    W=np.mean([x[0] for x in o])*100 if o else 0
    A_=np.mean([x[1] for x in o]) if o else 0
    T_=np.sum([x[1] for x in o]) if o else 0
    print(f" {s}: fills={len(o)} win={W:.1f}% avgR={A_:+.3f} total={T_:+.0f}",flush=True)
    totW+=sum(x[0] for x in o); totR+=T_; totN+=len(o)
DAYS=(max(int(r["ts"]) for r in M)-min(int(r["ts"]) for r in M))/86400000
print(f" GLOBAL: tr/dia={totN/DAYS:.1f} win={totW/totN*100:.1f}% avgR={totR/totN:+.3f}",flush=True)
fees=np.array(fees)
print(f" FEES: costo medio={fees.mean():.3f}R/trade med={np.median(fees):.3f} p90={np.quantile(fees,0.9):.3f}",flush=True)
print(f" avgR NETO aprox={totR/totN-fees.mean():+.3f} (win% no cambia: fees no convierten TP en SL salvo borde)",flush=True)
