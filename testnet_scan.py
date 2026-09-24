"""Scan live testnet: busca setup campeon (LONG eff.45 alpha1.5 noPBvol) en vela cerrada i=-2."""
import requests
F="https://testnet.binancefuture.com"
COINS=["ASTERUSDT","XPLUSDT","PUMPUSDT","STBLUSDT","0GUSDT","WLDUSDT","ENAUSDT","ARBUSDT","OPUSDT","INJUSDT","SUIUSDT","TIAUSDT"]
def kl(symbol,n=100):
    r=requests.get(F+"/fapi/v1/klines",params={"symbol":symbol,"interval":"15m","limit":n},timeout=20)
    r.raise_for_status(); return r.json()
btc=kl("BTCUSDT"); bc=[float(k[4]) for k in btc]
btc4h=(bc[-1]/bc[-17]-1)*100
print(f"BTC testnet 4h: {btc4h:+.2f}%",flush=True)
import numpy as np
for sym in COINS:
    try:
        ks=kl(sym); closes=np.array([float(k[4]) for k in ks]); highs=np.array([float(k[2]) for k in ks]); lows=np.array([float(k[3]) for k in ks])
        vols=np.array([float(k[5])*float(k[4]) for k in ks])
        for i in [len(ks)-3,len(ks)-2]:
            c0=closes[i-16]; c1=closes[i]
            chg=(c1/c0-1)*100
            path=np.sum(np.abs(np.diff(closes[i-16:i+1]))); eff=abs(c1-c0)/path
            h4=np.max(highs[i-15:i+1]); l4=np.min(lows[i-15:i+1]); px=c1
            side=1 if (chg>=2.0 and (h4-px)/h4*100<=3.0) else (-1 if (chg<=-2.0 and (px-l4)/l4*100<=3.0) else 0)
            if side!=1 or eff<0.45: continue
            if (h4-l4)/px*100<1.5: continue
            sl=l4; risk=(px-sl)/px*100
            if risk<=0.05 or risk>8: continue
            alpha=chg-btc4h
            if abs(alpha)<1.5: continue
            o1,c1_=float(ks[i+1][1]),float(ks[i+1][4])
            fb=(c1_-o1)/o1*100; fv=vols[i+1]/(np.mean(vols[max(0,i-19):i+1])+1e-9)
            if fb<-0.3 and fv>=1.2: continue
            lv=h4-(h4-l4)*0.8; tp=lv+(lv-sl)*1.0
            print(f">>> {sym} i={i} px={px:.4g} lv80={lv:.4g} sl={sl:.4g} tp={tp:.4g} risk={risk:.2f}% eff={eff:.2f} alpha={alpha:+.1f} fb={fb:+.2f}%",flush=True)
    except Exception as e:
        print(sym,"ERR",e)
print("scan fin",flush=True)
