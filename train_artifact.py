"""Entrena artefacto RF TOP9 + umbrales p20 por lado desde photos_full.csv (split train)."""
import csv, os, json, pickle
import numpy as np
from sklearn.ensemble import RandomForestClassifier
BASE=os.path.dirname(os.path.abspath(__file__))
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
TOP=["alpha","spike","risk","rng","eff","v6","v12","v24","btc4h"]
tr=[r for r in M if r["split"]=="train"]
X=np.array([[float(r[c]) for c in TOP] for r in tr])
y=np.array([int(r["win"]) for r in tr])
side=np.array([r["side"] for r in tr])
art={"TOP":TOP}
for s in ["1","-1"]:
    m=side==s
    clf=RandomForestClassifier(n_estimators=200,min_samples_leaf=60,class_weight="balanced_subsample",random_state=7,n_jobs=-1)
    clf.fit(X[m],y[m])
    p=clf.predict_proba(X[m])[:,1]
    art[s]={"model":clf,"p20":float(np.quantile(p,0.2)),"p40":float(np.quantile(p,0.4))}
    print(f"side {s}: n={m.sum()} p20={art[s]['p20']:.3f} p40={art[s]['p40']:.3f}",flush=True)
os.makedirs(os.path.join(BASE,"fly-mcp"),exist_ok=True)
with open(os.path.join(BASE,"fly-mcp","rf_top9.pkl"),"wb") as f: pickle.dump(art,f)
print("size MB:",round(os.path.getsize(os.path.join(BASE,"fly-mcp","rf_top9.pkl"))/1e6,1))
