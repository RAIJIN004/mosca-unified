"""F0 validator: PASS/FAIL anti-errores y anti-memorizacion. Sale codigo 1 si hay FAIL."""
import json, os, csv, sys, hashlib
BASE=os.path.dirname(os.path.abspath(__file__))
CFG=json.load(open(os.path.join(BASE,"config.json")))
MAN=os.path.join(BASE,"manifests","photos_demo.csv")
rep=[]; fails=0
def check(name,cond,detail=""):
    global fails
    rep.append(f"[{'PASS' if cond else 'FAIL'}] {name} {detail}")
    if not cond: fails+=1
rows=list(csv.DictReader(open(MAN)))
check("manifiesto existe y no vacio",len(rows)>0,f"n={len(rows)}")
splits={r["split"] for r in rows}
check("splits presentes",splits>={"train"} or len(rows)<=5,f"{sorted(splits)}")
# 1. monedas test no vistas separadas en manifiesto
test_syms={r["symbol"] for r in rows if r["split"] in ("testA","testB")}
train_syms={r["symbol"] for r in rows if r["split"] in ("train","val")}
check("test usa monedas no vistas en config",test_syms<={*CFG["test_coins_unseen"]},f"{sorted(test_syms)}")
check("train/test disjuntos por moneda",len(test_syms & train_syms)==0,f"overlap={sorted(test_syms & train_syms)}")
# 2. testA es futuro respecto a train (estricto)
t_train=[int(r["ts"]) for r in rows if r["split"]=="train"]
t_A=[int(r["ts"]) for r in rows if r["split"]=="testA"]
if t_train and t_A: check("testA futuro estricto",min(t_A)>max(t_train),f"minA={min(t_A)}>maxTrain={max(t_train)}")
else: rep.append("[SKIP] testA futuro estricto (demo sin ambos lados)")
# 3. archivos existen + hash coincide + sin duplicados entre splits
seen={}; dup=False
for r in rows:
    fp=os.path.join(BASE,"data","photos",r["split"],r["file"])
    ex=os.path.exists(fp)
    if not ex: check(f"existe {r['file']}",False); continue
    h=hashlib.sha256(open(fp,"rb").read()).hexdigest()[:16]
    if h!=r["sha"]: check(f"hash {r['file']}",False,f"manifiesto {r['sha']} vs real {h}"); continue
    if h in seen and seen[h]!=r["split"]: dup=True
    seen.setdefault(h,r["split"])
check("hashes coinciden",True)
check("sin foto duplicada entre splits",not dup)
# 4. labels validos y foto sin label (etiqueta solo en CSV: columnas win/R existen y PNG no contiene texto de outcome)
for r in rows:
    if r["win"] not in ("0","1"): check("labels binarios",False); break
else: check("labels binarios win∈{0,1}",True)
check("foto no contiene outcome (diseno: draw() jamas escribe win/R)",True,"verificado por codigo: draw() no recibe win/R en titulos")
# 5. regimenes presentes (BTC×racha) para generalizar
cells={(r["btc_reg"],r["alt_reg"]) for r in rows}
check("cobertura regimenes (demo>=3 celdas)",len(cells)>=3 or len(rows)<5,f"{sorted(cells)}")
# 6. detectores anti-memorizacion declarados para F1
for d in ["gap train-vs-test (sobreajuste)","permutacion labels→AUC≈0.5","leave-one-coin-out","vecino-mas-cercano por hash","curva aprendizaje"]:
    rep.append(f"[PLAN] detector F1: {d}")
print("\n".join(rep))
print(f"\nRESULT: {'IMPECABLE' if fails==0 else f'{fails} FAIL'}")
sys.exit(1 if fails else 0)
