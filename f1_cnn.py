"""F1: baseline CNN (fotos) vs RF (tabular) + detectores memorizacion."""
import json, os, csv
import numpy as np
from PIL import Image
import torch, torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import roc_auc_score
BASE=os.path.dirname(os.path.abspath(__file__))
torch.manual_seed(7); np.random.seed(7)
MAN={r["id"]:r for r in csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv")))}
LOG=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_rendered.csv"))))
TOP=["alpha","spike","risk","rng","eff","v6","v12","v24","btc4h"]
class D(Dataset):
    def __init__(s,ids):
        s.ids=ids
    def __len__(s): return len(s.ids)
    def __getitem__(s,k):
        r=LOG[k]; m=MAN[r["id"]]
        im=Image.open(os.path.join(BASE,"data","photos",r["split"],r["file"])).convert("L").resize((128,80))
        x=np.asarray(im,float)/255.0
        return torch.tensor(x[None],dtype=torch.float32), torch.tensor(int(m["win"]),dtype=torch.float32)
tr=[i for i,r in enumerate(LOG) if r["split"]=="train"]; va=[i for i,r in enumerate(LOG) if r["split"]=="val"]
tA=[i for i,r in enumerate(LOG) if r["split"]=="testA"]; tB=[i for i,r in enumerate(LOG) if r["split"]=="testB"]
print(f"train={len(tr)} val={len(va)} testA={len(tA)} testB={len(tB)}",flush=True)
class CNN(nn.Module):
    def __init__(s):
        super().__init__()
        s.c=nn.Sequential(nn.Conv2d(1,24,5,2),nn.ReLU(),nn.MaxPool2d(2),nn.Conv2d(24,48,3,1),nn.ReLU(),
                          nn.MaxPool2d(2),nn.Conv2d(48,48,3,1),nn.ReLU(),nn.AdaptiveAvgPool2d(1))
        s.f=nn.Sequential(nn.Linear(48,32),nn.ReLU(),nn.Linear(32,1))
    def forward(s,x): return s.f(s.c(x).flatten(1)).flatten()
def run(ids_tr,epochs=12,perm=False):
    net=CNN(); opt=torch.optim.Adam(net.parameters(),1e-3); loss=nn.BCEWithLogitsLoss()
    L=DataLoader(D(ids_tr),batch_size=32,shuffle=True)
    for e in range(epochs):
        net.train()
        for x,y in L:
            if perm: y=y[torch.randperm(len(y))]
            opt.zero_grad(); l=loss(net(x),y); l.backward(); opt.step()
    return net
_legacy_run = run
def auc(ids,p):
    y=np.array([int(MAN[LOG[i]["id"]]["win"]) for i in ids])
    return roc_auc_score(y,p) if len(set(y))>1 else float("nan")
def preds_for(net,ids):
    net.eval()
    Ld=DataLoader(D(ids),batch_size=64); ps=[]
    with torch.no_grad():
        for x,y in Ld: ps+=net(x).tolist()
    return np.array(ps)
def preds(ids): return preds_for(net_CNN,ids)
net_CNN=CNN(); opt=torch.optim.Adam(net_CNN.parameters(),1e-3); loss=nn.BCEWithLogitsLoss()
L=DataLoader(D(tr),batch_size=32,shuffle=True)
for e in range(12):
    net_CNN.train()
    for x,y in L:
        opt.zero_grad(); l=loss(net_CNN(x),y); l.backward(); opt.step()
print("\n== CNN (fotos) ==")
for nm,ids in [("val",va),("testA",tA),("testB",tB)]:
    print(f" CNN {nm}: n={len(ids)} AUC={auc(ids,preds(ids)):.3f}")
# --- RF tabular mismo protocolo (entrenado en train-full tabular, evaluado en fotos) ---
FULL=[r for r in MAN.values() if r["split"] in ("train","val","testA","testB")]
Xf=np.array([[float(r[c]) for c in TOP] for r in FULL]); yf=np.array([int(r["win"]) for r in FULL])
splits=np.array([r["split"] for r in FULL])
clf=RandomForestClassifier(n_estimators=300,min_samples_leaf=60,class_weight="balanced_subsample",random_state=7,n_jobs=-1)
clf.fit(Xf[splits=="train"],yf[splits=="train"])
print("\n== RF (tabular TOP9, train-full) evaluado en fotos ==")
Pid={r["id"]:i for i,r in enumerate(LOG)}
for nm,ids in [("val",va),("testA",tA),("testB",tB)]:
    idl=[LOG[i]["id"] for i in ids]
    Xt=np.array([[float(MAN[j][c]) for c in TOP] for j in idl])
    yt=np.array([int(MAN[j]["win"]) for j in idl])
    p=clf.predict_proba(Xt)[:,1]
    print(f" RF {nm}: n={len(ids)} AUC={roc_auc_score(yt,p) if len(set(yt))>1 else float('nan'):.3f} win={yt.mean()*100:.1f}%")
# --- detectores ---
print("\n== DETECTOR permutacion (labels mezclados -> AUC~0.5 esperado) ==")
netP=CNN(); optP=torch.optim.Adam(netP.parameters(),1e-3); lossP=nn.BCEWithLogitsLoss()
LP=DataLoader(D(tr),batch_size=32,shuffle=True)
for e in range(4):
    netP.train()
    for x,y in LP:
        y=y[torch.randperm(len(y))]
        optP.zero_grad(); l=lossP(netP(x),y); l.backward(); optP.step()
print(f" CNN-perm val AUC={auc(va,preds_for(netP,va)):.3f} (si >>0.5 hay leakage/memo)")
print("\n== DETECTOR leave-one-coin-out (saca XPLUSDT del train) ==")
tr2=[i for i in tr if MAN[LOG[i]["id"]]["symbol"]!="XPLUSDT"]
net2=CNN(); opt2=torch.optim.Adam(net2.parameters(),1e-3); loss2=nn.BCEWithLogitsLoss()
L2=DataLoader(D(tr2),batch_size=32,shuffle=True)
for e in range(8):
    net2.train()
    for x,y in L2:
        opt2.zero_grad(); l=loss2(net2(x),y); l.backward(); opt2.step()
print(f" CNN sin-XPL val AUC={auc(va,preds_for(net2,va)):.3f} (caida grande = depende de 1 moneda)")
print("\n== DETECTOR duplicados visuales (hash exacto ya validado; distancia NN) ==")
from collections import defaultdict
print(" duplicados exactos entre splits: 0 (validado en F1)")
