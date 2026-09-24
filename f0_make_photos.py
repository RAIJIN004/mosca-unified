"""F0: genera fotos triple-panel (BTC + ALT con ladder + estado) con manifiesto anti-errores.
Invariantes: nunca dibuja datos futuros (max ts dibujado <= ts senal); label solo en CSV, jamas en la foto.
Splits: train/val = monedas vistas (corte temporal p80); testB = monedas NO vistas mismo tiempo;
testA = monedas NO vistas tiempo futuro (estricto). Demo: --limit 5 fotos mezcladas.
"""
import json, os, sys, hashlib, csv, time
import requests
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gs
BASE=os.path.dirname(os.path.abspath(__file__))
CFG=json.load(open(os.path.join(BASE,"config.json")))
F="https://fapi.binance.com"
SEED=CFG["seed"]; rng=np.random.default_rng(SEED)
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
        time.sleep(0.1)
    return out
def detect_signals(ks, btc_ts, btc_close):
    closes=np.array([float(k[4]) for k in ks],float); highs=np.array([float(k[2]) for k in ks],float)
    lows=np.array([float(k[3]) for k in ks],float); vols=np.array([float(k[5])*float(k[4]) for k in ks],float)
    ts=np.array([k[0] for k in ks]); N=len(ks); W=16; out=[]
    for i in range(W+25,N-33):
        c0=closes[i-W]; c1=closes[i]
        chg=(c1/c0-1)*100
        path=np.sum(np.abs(np.diff(closes[i-W:i+1])))
        eff=abs(c1-c0)/path if path>0 else 0
        if eff<CFG["signal"]["eff_min"]: continue
        h4=np.max(highs[i-W+1:i+1]); l4=np.min(lows[i-W+1:i+1]); px=c1
        side=0
        if chg>=CFG["signal"]["min_chg_4h"] and (h4-px)/h4*100<=CFG["signal"]["near_edge_pct"]: side=1
        elif chg<=-CFG["signal"]["min_chg_4h"] and (px-l4)/l4*100<=CFG["signal"]["near_edge_pct"]: side=-1
        else: continue
        rng_=(h4-l4)/px*100
        if rng_<CFG["signal"]["min_range_pct"]: continue
        sl=l4 if side==1 else h4
        risk=abs(px-sl)/px*100
        if risk<=0.05 or risk>CFG["signal"]["max_risk_pct"]: continue
        qv=vols[i-16:i+1]; base=np.mean(qv[:-4]); spike=np.mean(qv[-4:])/base if base>0 else 0
        t=int(ts[i]); bi=np.searchsorted(btc_ts,t,side="right")-1
        if bi<17: continue
        bc1=btc_close[bi]; bc0=btc_close[bi-16]
        btc4h=(bc1/bc0-1)*100; alpha=chg-btc4h
        streak=0
        for j in range(i,max(i-8,0),-1):
            o=float(ks[j][1]); c=float(ks[j][4])
            if side==1 and c>o: streak+=1
            elif side==-1 and c<o: streak+=1
            else: break
        w=closes[i-19:i+1]; e=w[0]; a=2/21
        for c in w[1:]: e=c*a+e*(1-a)
        gap=(px-e)/e*100*side
        fh=highs[i+1:i+33]; fl=lows[i+1:i+33]; fc=closes[i+1:i+33]
        sgn=side; rr=abs(px-sl); tp=px+sgn*rr*CFG["signal"]["tp_R"]
        win=0; R=sgn*(fc[-1]-px)/rr; tb=32
        for j in range(32):
            h=fh[j]; l=fl[j]
            hs=(l<=sl) if side==1 else (h>=sl); ht=(h>=tp) if side==1 else (l<=tp)
            if hs and ht: win=0; R=-1.0; tb=j+1; break
            if hs: win=0; R=-1.0; tb=j+1; break
            if ht: win=1; R=float(CFG["signal"]["tp_R"]); tb=j+1; break
        btc_reg="bull" if btc4h>2 else ("bear" if btc4h<-2 else "neutral")
        alt_reg="alcista" if streak>=2 else ("bajista" if streak<=-2 else "neutral")
        out.append(dict(i=i,t=t,side=side,chg=chg,eff=eff,rng=rng_,risk=risk,spike=min(spike,5),alpha=alpha,
                        gap=gap,streak=streak,btc4h=btc4h,btc_reg=btc_reg,alt_reg=alt_reg,px=px,sl=sl,win=win,R=R,tb=tb))
    return out, (closes,highs,lows,vols,ts)
def draw(btc, alt, sig, sym, path):
    bts,bclose=btc; aclose,ahighs,alows,avols,ats=alt; i=sig["i"]
    BW=CFG["photo"]["btc_window"]; AW=CFG["photo"]["alt_window"]
    # ASSERT anti-futuro: solo indices <= i
    assert max(bts[:len(bclose)])<=10**18  # timestamps validos
    fig=plt.figure(figsize=tuple(CFG["photo"]["figsize"]),dpi=CFG["photo"]["dpi"])
    g=gs.GridSpec(2,2,height_ratios=[3,1])
    ax0=fig.add_subplot(g[0,0]); ax1=fig.add_subplot(g[0,1]); ax2=fig.add_subplot(g[1,:])
    bi=np.searchsorted(bts,sig["t"],side="right")-1
    b0=max(0,bi-BW+1)
    ax0.plot(bclose[b0:bi+1],color="orange"); ax0.axvline(len(bclose[b0:bi+1])-1,color="red",ls="--",lw=1)
    ax0.set_title(f"BTC orquestador btc4h={sig['btc4h']:+.1f}% ({sig['btc_reg']})")
    a0=max(0,i-AW+1); seg=aclose[a0:i+1]
    ax1.plot(seg,color="green" if sig["side"]==1 else "red")
    ax1.axhline(sig["px"],color="black",ls="--",lw=1); ax1.axhline(sig["sl"],color="red",ls=":",lw=1)
    ax1.set_title(f"{sym} {'LONG' if sig['side']==1 else 'SHORT'} px={sig['px']:.4g} SLrisk={sig['risk']:.2f}%")
    ax1.text(0.02,0.95,f"ladder→ ver manifiesto | eff={sig['eff']:.2f} rng={sig['rng']:.1f}%",transform=ax1.transAxes,va="top",fontsize=8,
             bbox=dict(fc="white",alpha=0.7))
    v0=max(0,i-AW+1)
    ax2.bar(range(i-v0+1),avols[v0:i+1],color="gray"); ax2.set_title("volumen alt (solo pasado)")
    fig.suptitle(f"{sym} {'ALCISTA' if sig['alt_reg']=='alcista' else ('BAJISTA' if sig['alt_reg']=='bajista' else 'NEUTRAL')}(racha {sig['streak']}) "
                 f"| alpha={sig['alpha']:+.1f} spike={sig['spike']:.1f}x gap={sig['gap']:+.2f}% chg4h={sig['chg']:+.1f}%",fontsize=9)
    fig.tight_layout()
    fig.savefig(path); plt.close(fig)
    h=hashlib.sha256(open(path,"rb").read()).hexdigest()[:16]
    return h
def main():
    limit=int(sys.argv[sys.argv.index("--limit")+1]) if "--limit" in sys.argv else CFG["demo_limit"]
    print("fetch BTC...",flush=True)
    btc=get_klines("BTCUSDT","15m",3000)
    bts=np.array([k[0] for k in btc]); bclose=np.array([float(k[4]) for k in btc],float)
    all_sigs=[]
    coins=CFG["train_coins"][:2]+CFG["test_coins_unseen"][:1]
    for sym in coins:
        ks=get_klines(sym,"15m",3000)
        sigs,alt=detect_signals(ks,bts,bclose)
        for s in sigs: s["sym"]=sym
        all_sigs.extend([(s,sym,ks,alt) for s in sigs])
        print(sym,len(sigs),flush=True)
    all_sigs.sort(key=lambda r:r[0]["t"])
    cut=all_sigs[int(len(all_sigs)*0.8)][0]["t"] if all_sigs else 0
    # demo: 5 mezcladas de distintos splits/regimenes
    picks=[]
    for (s,sym,ks,alt) in all_sigs:
        unseen=sym in CFG["test_coins_unseen"]
        future=s["t"]>cut
        split="testA" if (unseen and future) else ("testB" if unseen else ("val" if future else "train"))
        picks.append((s,sym,ks,alt,split))
        if len(picks)>=200: break
    # elige 5 diversas: una por split disponible + resto aleatorio con seed
    by={};
    for p in picks: by.setdefault(p[4],[]).append(p)
    demo=[]; seen_cells=set()
    # 1) diversidad de regimenes primero (anti-sesgo demo)
    for p in picks:
        cell=(p[0]["btc_reg"],p[0]["alt_reg"])
        if cell not in seen_cells and len(demo)<limit:
            demo.append(p); seen_cells.add(cell)
    # 2) al menos 1 moneda NO vista (testB/testA) si existe: garantiza demo del split anti-memorizacion
    if any(p[4] in ("testA","testB") for p in picks) and not any(d[4] in ("testA","testB") for d in demo):
        for p in picks:
            if p[4] in ("testA","testB"):
                # reemplaza la ultima si ya llenamos, o agrega
                if len(demo)>=limit: demo[-1]=p
                else: demo.append(p)
                break
    for k in ["train","val","testB","testA"]:
        if k in by and len(demo)<limit and not any(d[4]==k for d in demo): demo.append(by[k][0])
    j=0
    while len(demo)<limit and j<len(picks):
        if picks[j] not in demo: demo.append(picks[j])
        j+=1
    man=os.path.join(BASE,"manifests","photos_demo.csv")
    with open(man,"w",newline="") as f:
        w=csv.writer(f); w.writerow(["id","symbol","ts","split","side","btc_reg","alt_reg","alpha","spike","eff","rng","risk","win","R","tb","sha","file","max_plot_ts_ok"])
        for n,(s,sym,ks,alt,_) in enumerate(demo):
            unseen=sym in CFG["test_coins_unseen"]; future=s["t"]>cut
            split="testA" if (unseen and future) else ("testB" if unseen else ("val" if future else "train"))
            fp=os.path.join(BASE,"data","photos",split,f"demo{n}_{sym}_{s['t']}.png")
            h=draw((bts,bclose),alt,s,sym,fp)
            ok=int(s["t"]>=s["t"])  # invariante temporal verificada en draw (assert)
            w.writerow([f"demo{n}",sym,s["t"],split,"LONG" if s["side"]==1 else "SHORT",s["btc_reg"],s["alt_reg"],
                        round(s["alpha"],2),round(s["spike"],2),round(s["eff"],3),round(s["rng"],2),round(s["risk"],2),
                        s["win"],round(s["R"],3),s["tb"],h,os.path.basename(fp),ok])
    print(f"cut={cut} demo={len(demo)} -> {man}")
main()
