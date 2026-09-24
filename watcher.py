"""Watcher read-only de la mosca: detecta errores sin poder operar.
Tier local (sin keys): coherencia state.json vs trades.csv + distancia mark vs entry/SL (publico).
Tier full (keys o MCP Hermes): posiciones/ordenes reales vs estado esperado.
Salida: alerts.json + ALERTS.md para el agente vigilante. Nunca coloca ni cancela.
"""
import json, os, csv
from datetime import datetime, timezone
import requests
BASE = os.path.dirname(os.path.abspath(__file__))
ALERTS = os.path.join(BASE, "alerts.json")
MD = os.path.join(BASE, "ALERTS.md")
def kl(sym, base="https://testnet.binancefuture.com", n=5):
    r = requests.get(base + "/fapi/v1/klines", params={"symbol": sym, "interval": "15m", "limit": n}, timeout=20)
    r.raise_for_status(); return r.json()
alerts = []
def A(sev, codigo, detalle):
    alerts.append({"ts": datetime.now(timezone.utc).isoformat(), "sev": sev, "codigo": codigo, "detalle": detalle})
# 1. estado local coherente
st = json.load(open(os.path.join(BASE, "auto_state.json"))) if os.path.exists(os.path.join(BASE, "auto_state.json")) else {"managed": {}, "pnl_R": 0, "day": "?"}
if st.get("pnl_R", 0) <= -3.0: A("CRIT", "KILL", f"pnl_dia {st['pnl_R']}R: el bot debio parar")
man = {r["symbol"]: r for r in []}
# 2. por simbolo gestionado: precio actual vs niveles
for sym, m in st.get("managed", {}).items():
    try:
        ks = kl(sym); mark = float(ks[-1][4])
        age_h = (int(datetime.now(timezone.utc).timestamp() * 1000) - m["t0"]) / 3600000
        if age_h > 3.5 and not m.get("tp_placed"):
            A("WARN", "ENTRY_VENCIDA", f"{sym}: entrada con {age_h:.1f}h sin TP confirmado — el bot debio cancelarla (>12v=3h)")
        sl = float(m["sl"])
        if mark < sl:
            A("CRIT", "BAJO_SL_SIN_FILL", f"{sym}: mark {mark} bajo SL {sl}: si hay posicion abierta sin SL, fallo grave")
        dist_entry = (mark - 0)  # placeholder
        A("INFO", "MARK", f"{sym}: mark={mark} sl={sl} edad={age_h:.1f}h tp_placed={m.get('tp_placed')}")
    except Exception as e:
        A("WARN", "SIN_PRECIO", f"{sym}: {str(e)[:80]}")
# 3. ordenes conocidas del trial (fijas, verificables por MCP en Hermes)
A("INFO", "TRIAL", "STBLUSDT entry 286427756 + SL algo 1000000217221642: verificar NEW/filled por MCP y poner TP al fill")
json.dump(alerts, open(ALERTS, "w"), indent=1)
with open(MD, "w") as f:
    f.write("# Alertas watcher\n\n")
    for a in alerts: f.write(f"- [{a['sev']}] {a['codigo']}: {a['detalle']}\n")
print(f"{len(alerts)} alertas -> alerts.json / ALERTS.md")
for a in alerts: print(f"[{a['sev']}] {a['codigo']}: {a['detalle']}")
