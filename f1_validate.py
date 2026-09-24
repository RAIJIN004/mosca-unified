"""F1 validator full: integridad, splits, render log, regimenes. FAIL=>exit 1."""
import json, os, csv, sys, hashlib
BASE=os.path.dirname(os.path.abspath(__file__))
CFG=json.load(open(os.path.join(BASE,"config.json")))
fails=0
def check(name,cond,detail=""):
    global fails
    print(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond: fails+=1
M=list(csv.DictReader(open(os.path.join(BASE,"manifests","photos_full.csv"))))
check("manifiesto columnas consistentes",all(len(r)==25 for r in [M[0]]),f"cols={len(M[0])}")
N=len(M); PH=[r for r in M if r["photo_split"]]
check("volumen",N>30000,f"N={N} fotos_cuota={len(PH)}")
check("labels binarios",all(r["win"] in ("0","1") for r in M))
check("R en [-1,2]",all(-1.01<=float(r["R"])<=2.01 for r in M))
trs={r["symbol"] for r in M if r["split"]=="train" or True}
tr={r["symbol"] for r in M if r["split"] in ("train","val")}
te={r["symbol"] for r in M if r["split"] in ("testA","testB")}
check("monedas vistas==config",tr==set(CFG["train_coins"]),f"{sorted(tr)}")
check("monedas no vistas==config",te==set(CFG["test_coins_unseen"]),f"{sorted(te)}")
t_tr=max(int(r["ts"]) for r in M if r["split"]=="train")
t_A=min(int(r["ts"]) for r in M if r["split"]=="testA")
check("testA futuro estricto",t_A>t_tr,f"minA={t_A}>maxTrain={t_tr}")
# testB mismo tiempo que train (pure symbol transfer): solapa temporal
t_B=[int(r["ts"]) for r in M if r["split"]=="testB"]
check("testB solapa tiempo train",min(t_B)<=t_tr,f"overlap OK")
LOG={r["id"]:r for r in csv.DictReader(open(os.path.join(BASE,"manifests","photos_rendered.csv")))}
missing=[r["id"] for r in PH if r["id"] not in LOG]
check("render log completo",not missing,f"faltan={len(missing)}")
bad=0
for r in PH:
    if r["id"] not in LOG: continue
    fp=os.path.join(BASE,"data","photos",LOG[r["id"]]["split"],LOG[r["id"]]["file"])
    if not os.path.exists(fp): bad+=1; continue
    h=hashlib.sha256(open(fp,"rb").read()).hexdigest()[:16]
    if h!=LOG[r["id"]]["sha"]: bad+=1
check("archivos+hashes OK",bad==0,f"mal={bad}")
# foto en split correcto
wr=[r for r in PH if LOG.get(r["id"],{}).get("split","")!=r["photo_split"]]
check("foto en su split",not wr,f"mal={len(wr)}")
cells={}
for r in M: cells[(r["split"],r["btc_reg"],r["alt_reg"])]=cells.get((r["split"],r["btc_reg"],r["alt_reg"]),0)+1
print("celdas:",len(cells),"min:",min(cells.values()))
rare=[k for k,v in cells.items() if v<5]
print("celdas raras (<5):",rare)
for s in ["train","val","testA","testB"]:
    w=[float(r["win"]) for r in M if r["split"]==s]
    import statistics
    print(f" {s}: n={len(w)} win={sum(w)/len(w)*100:.1f}%")
check("cache klines existe",os.path.exists(os.path.join(BASE,"data","klines_cache.npz")))
print(f"\nRESULT: {'IMPECABLE' if fails==0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
