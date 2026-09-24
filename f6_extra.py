"""F6 extra: SHORT espejo + sensibilidad frac. Reusa cache+manifest."""
import csv, os
import numpy as np
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
D=np.load(os.path.join(BASE,"data","klines_cache.npz"))
TO=32
EFF=np.array([float(r["eff"]) for r in M]); ALP=np.array([float(r["alpha"]) for r in M])
SIDE=np.array([r["side"] for r in M]); SPLIT=np.array([r["split"] for r in M])
II=np.zeros(len(M),int); FB=np.zeros(len(M)); FV=np.zeros(len(M))
for n,r in enumerate(M):
    A=D[r["symbol"]]; ts=A[:,0]; j=np.searchsorted(ts,int(r["ts"])); II[n]=j
    sgn=1 if r["side"]=="1" else -1
    FB[n]=(A[j+1,4]-A[j+1,1])/A[j+1,1]*100*sgn
    FV[n]=A[j+1,5]/(np.mean(A[max(0,j-19):j+1,5])+1e-9)
filtL=(SIDE=="1")&(EFF>=0.45)&(np.abs(ALP)>=1.5)&(~((FB<-0.3)&(FV>=1.2)))
filtS=(SIDE=="-1")&(EFF>=0.45)&(np.abs(ALP)>=1.5)&(~((FB<-0.3)&(FV>=1.2)))
def run(mask,frac,TP,sgn):
    per={s:[] for s in ["train","val","testA","testB"]}
    for n in np.where(mask)[0]:
        r=M[n]; A=D[r["symbol"]]; j=II[n]
        h4=np.max(A[j-15:j+1,2]); l4=np.min(A[j-15:j+1,3])
        lv=h4-(h4-l4)*frac if sgn==1 else l4+(h4-l4)*frac
        px=A[j,4]; sl=px-sgn*float(r["risk"])/100*px
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
        per[SPLIT[n]].append((w,R))
    return per
def show(name,per):
    tW=tR=tN=0
    line=f"{name}: "
    for s in ["train","val","testA","testB"]:
        o=per[s]
        W=np.mean([x[0] for x in o])*100 if o else 0; A_=np.mean([x[1] for x in o]) if o else 0
        line+=f"{s}:{len(o)}/{W:.0f}%/{A_:+.2f} "
        tW+=sum(x[0] for x in o); tR+=sum(x[1] for x in o); tN+=len(o)
    print(line+f"| TOT:{tN} win={tW/max(1,tN)*100:.1f}% avg={tR/max(1,tN):+.3f}",flush=True)
print("== SHORT espejo frac=0.8 TP=1.0 ==",flush=True)
show("SHORT",run(filtS,0.8,1.0,-1))
print("== Sensibilidad LONG TP=1.0 ==",flush=True)
for fr in [0.75,0.85]:
    show(f"LONG fr={fr}",run(filtL,fr,1.0,1))
