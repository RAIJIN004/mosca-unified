"""Sweep winrate VECTORIZADO: precompute paths en R, eval configs con numpy."""
import csv, os
import numpy as np
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
D=np.load(os.path.join(BASE,"data","klines_cache.npz"))
TO=32
N=len(M)
H=np.full((N,TO),np.nan)
L=np.full((N,TO),np.nan); C=np.full((N,TO),np.nan)
SGN=np.zeros(N); OK=np.zeros(N,bool); FB=np.zeros(N); FV=np.zeros(N)
for n,r in enumerate(M):
    A=D[r["symbol"]]; ts=A[:,0]
    j=np.searchsorted(ts,int(r["ts"]))
    if j>=len(A) or int(ts[j])!=int(r["ts"]) or j+TO>=len(A): continue
    px=A[j,4]; sgn=1 if r["side"]=="1" else -1
    rr=abs(px-(px-float(r["risk"])/100*px*sgn))/1  # = risk%*px/100
    rr=float(r["risk"])/100*px
    seg=A[j+1:j+1+TO]
    H[n]=sgn*(seg[:,2]-px)/rr; L[n]=sgn*(seg[:,3]-px)/rr; C[n]=sgn*(seg[:,4]-px)/rr
    SGN[n]=sgn; OK[n]=True
    o,c=A[j+1,1],A[j+1,4]
    FB[n]=(c-o)/o*100*sgn
    FV[n]=A[j+1,5]/(np.mean(A[max(0,j-19):j+1,5])+1e-9)
print(f"N={N} ok={OK.sum()} dias={(max(int(r['ts']) for r in M)-min(int(r['ts']) for r in M))/86400000:.0f}",flush=True)
H,L,C=H[OK],L[OK],C[OK]
MM=[r for o,r in zip(OK,M) if o]; FB=FB[OK]; FV=FV[OK]
EFF=np.array([float(r["eff"]) for r in MM]); AL=np.array([abs(float(r["alpha"])) for r in MM])
SIDE=np.array([r["side"] for r in MM])
DAYS=(max(int(r['ts']) for r in M)-min(int(r['ts']) for r in M))/86400000
def first_hit(A2M,th,ge=True):
    m=A2M>=th if ge else A2M<=th
    any_=m.any(1)
    j=np.where(any_,m.argmax(1),TO+1)
    return j,any_
def ev(mask,TP,BE=None):
    Hm,Lm,Cm=H[mask],L[mask],C[mask]
    jtp,_=first_hit(Hm,TP,True); jsl,_=first_hit(Lm,-1.0,False)
    if BE is None:
        win=jtp<jsl; win=win & (jtp<=TO)
        R=np.where(win,TP,np.where(jsl<=TO,-1.0,Cm[:,TO-1]))
        return win.mean()*100,R.mean(),R.sum(),len(R)
    jbe,_=first_hit(Hm,BE,True)
    # eventos antes de BE
    pre_tp=(jtp<jbe)&(jtp<jsl)&(jtp<=TO)
    pre_sl=(jsl<=jtp)&(jsl<jbe)&(jsl<=TO)
    # tras BE: stop=px(0): primer j>=jbe con l<=0 (stop) o h>=TP
    J=np.arange(1,TO+1)
    elig=J[None,:]>=np.minimum(jbe,TO+1)[:,None]
    hit_tp2=((Hm>=TP)&elig); hit_sl2=((Lm<=0)&elig)
    jtp2=np.where(hit_tp2.any(1),hit_tp2.argmax(1)+1,TO+1)
    jsl2=np.where(hit_sl2.any(1),hit_sl2.argmax(1)+1,TO+1)
    post=~(pre_tp|pre_sl)
    win_post=(jtp2<jsl2)&(jtp2<=TO)
    R=np.zeros(len(Hm)); W=np.zeros(len(Hm),bool)
    R[pre_tp]=TP; W[pre_tp]=True
    R[pre_sl]=-1.0
    R[post & win_post]=TP; W[post & win_post]=True
    sl_be=post & (~win_post) & (jsl2<=TO)
    R[sl_be]=-0.05
    rest=post & (~win_post) & (jsl2>TO)
    R[rest]=Cm[rest][:,TO-1] if rest.any() else []
    R=np.where(pre_tp|pre_sl,R,R)
    return W.mean()*100,R.mean(),R.sum(),len(R)
print("== SWEEP ==",flush=True)
for TP in [0.5,0.8,1.0,1.2,1.5,2.0]:
    for BE in [None,0.5]:
        w,a,t,n=ev(np.ones(len(H),bool),TP,BE)
        print(f" TP={TP} BE={BE}: win={w:.1f}% avgR={a:+.3f} total={t:+.0f} tr/dia={n/DAYS:.1f}",flush=True)
print("== FILTROS TP=1.0 BE=0.5 ==",flush=True)
def F(name,m):
    w,a,t,n=ev(m,1.0,0.5)
    print(f" {name}: n={n} tr/dia={n/DAYS:.1f} win={w:.1f}% avgR={a:+.3f} total={t:+.0f}",flush=True)
allm=np.ones(len(H),bool)
F("nada",allm)
F("LONG",SIDE=="1")
F("LONG+eff.45", (SIDE=="1")&(EFF>=0.45))
F("...+alpha1.5",(SIDE=="1")&(EFF>=0.45)&(AL>=1.5))
F("...+noPBvol",(SIDE=="1")&(EFF>=0.45)&(AL>=1.5)&(~((FB<-0.3)&(FV>=1.2))))
F("...+1rafav",(SIDE=="1")&(EFF>=0.45)&(AL>=1.5)&(FB>0.3))
print("== TP FINO mejor filtro ==",flush=True)
m=(SIDE=="1")&(EFF>=0.45)&(AL>=1.5)&(~((FB<-0.3)&(FV>=1.2)))
for TP in [0.4,0.5,0.6,0.7,0.8,1.0,1.2]:
    w,a,t,n=ev(m,TP,0.5)
    print(f" TP={TP}: tr/dia={n/DAYS:.1f} win={w:.1f}% avgR={a:+.3f} total={t:+.0f}",flush=True)
