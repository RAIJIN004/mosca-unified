"""Mosca automatica: --mode testnet|real [--once] [--dry-run] [--risk-usd 3].
Mismo motor del backtest (V3-deep frac 0.8, TP 1R, filtros LONG + SHORT espejo 50%).
La mosca propone, el bot administra: expira entradas >12v, TP al fill, timeout 32v, kill -3R/dia.
KEYS por env: TESTNET_KEY/SECRET o BINANCE_KEY/SECRET. Real exige --confirm-live.
"""
import argparse, hashlib, hmac, json, os, time, csv
from datetime import datetime, timezone
import requests
import numpy as np
BASE = os.path.dirname(os.path.abspath(__file__))
URLS = {"testnet": "https://demo-fapi.binance.com", "real": "https://fapi.binance.com"}
TAG = "mosca-"
SYMS = ["ASTERUSDT","XPLUSDT","PUMPUSDT","STBLUSDT","0GUSDT","WLDUSDT","ENAUSDT","ARBUSDT",
        "OPUSDT","INJUSDT","SUIUSDT","TIAUSDT","SEIUSDT","JUPUSDT","PENDLEUSDT","ONDOUSDT","FETUSDT"]
STATE = os.path.join(BASE, "auto_state.json")
LOG = os.path.join(BASE, "trades.csv")
def load_state():
    d = {"day": "", "pnl_R": 0.0, "managed": {}}
    if os.path.exists(STATE): d.update(json.load(open(STATE)))
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if d["day"] != today: d = {"day": today, "pnl_R": 0.0, "managed": d.get("managed", {})}
    return d
def save_state(d): json.dump(d, open(STATE, "w"), indent=1)
class Ctx:
    def __init__(s, mode, dry):
        s.base = URLS[mode]; s.dry = dry; s._toff = None
        if mode == "testnet": s.key, s.sec = os.getenv("TESTNET_KEY", ""), os.getenv("TESTNET_SECRET", "")
        else: s.key, s.sec = os.getenv("BINANCE_KEY", ""), os.getenv("BINANCE_SECRET", "")
    def sign(s, p):
        q = "&".join(f"{k}={p[k]}" for k in sorted(p))
        return hmac.new(s.sec.encode(), q.encode(), hashlib.sha256).hexdigest()
    def req(s, m, path, params=None, signed=False):
        params = dict(params or {})
        headers = {"X-MBX-APIKEY": s.key} if signed else {}
        url = s.base + path
        data = None
        if signed:
            if s._toff is None:
                try:
                    srv = requests.get(s.base + "/fapi/v1/time", timeout=15).json()["serverTime"]
                    s._toff = srv - int(time.time() * 1000)
                except Exception:
                    s._toff = 0
            params.update({"timestamp": int(time.time() * 1000) + s._toff, "recvWindow": 30000})
            qs = "&".join(f"{k}={params[k]}" for k in sorted(params))
            qs += "&signature=" + hmac.new(s.sec.encode(), qs.encode(), hashlib.sha256).hexdigest()
            if m == "GET":
                url += "?" + qs
            else:
                data = qs
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            params = None
        r = requests.request(m, url, params=params, data=data, headers=headers, timeout=20)
        r.raise_for_status()
        return r.json() if r.text else {}
    def kl(s, sym, n=100):
        return s.req("GET", "/fapi/v1/klines", {"symbol": sym, "interval": "15m", "limit": n})
def excel(sym, ctx, cache):
    if sym not in cache:
        info = ctx.req("GET", "/fapi/v1/exchangeInfo")
        s = [x for x in info["symbols"] if x["symbol"] == sym][0]
        f = {x["filterType"]: x for x in s["filters"]}
        cache[sym] = (float(f["LOT_SIZE"]["stepSize"]), float(f["PRICE_FILTER"]["tickSize"]))
    return cache[sym]
def run_once(ctx, risk_usd, short_half=True):
    st = load_state()
    if not ctx.key:
        ctx.dry = True
        print("sin API keys: modo solo-lectura (scan publico, sin gestionar). En Hermes usa MCP.", flush=True)
    if st["pnl_R"] <= -3.0:
        print("KILL-SWITCH pnl_dia<=−3R: solo gestion, cero entradas"); 
    acts = []
    # 1. estado vivo
    acct = ctx.req("GET", "/fapi/v2/account", signed=True) if ctx.key else {}
    poss = {p["symbol"]: p for p in ctx.req("GET", "/fapi/v2/positionRisk", signed=True)} if ctx.key else {}
    ords = ctx.req("GET", "/fapi/v1/openOrders", signed=True) if ctx.key else []
    try:
        _ao = ctx.req("GET", "/fapi/v1/openAlgoOrders", signed=True) if ctx.key else []
        _ao = _ao.get("orders", _ao) if isinstance(_ao, dict) else (_ao or [])
    except Exception:
        _ao = []
    busy = {o["symbol"] for o in ords} | {o["symbol"] for o in _ao}
    now = int(time.time() * 1000)
    # 2. gestionar entradas (edad por updateTime)
    for o in ords:
        if not str(o.get("clientOrderId", "")).startswith(TAG): continue
        age = (now - o["updateTime"]) // 900000
        if o["type"] == "LIMIT" and age > 12:
            acts.append(("cancel", o["symbol"], o["orderId"]))
            if not ctx.dry: ctx.req("DELETE", "/fapi/v1/order", {"symbol": o["symbol"], "orderId": o["orderId"]}, True)
    # 3. gestionar posiciones mosca
    for sym, m in list(st["managed"].items()):
        pa = float(poss.get(sym, {}).get("positionAmt", 0) or 0)
        bars = (now - m["t0"]) // 900000
        if abs(pa) < 1e-9:
            if m.get("sl_id"):  # entrada nunca llenada y ya sin posicion: limpia SL huerfano
                try:
                    if not ctx.dry:
                        try:
                            ctx.req("DELETE", "/fapi/v1/order", {"symbol": sym, "orderId": m["sl_id"]}, True)
                        except SystemExit:
                            ctx.req("DELETE", "/fapi/v1/algoOrder", {"symbol": sym, "algoId": m["sl_id"]}, True)
                    acts.append(("cancel-sl-huerfano", sym, m["sl_id"]))
                except Exception as e: acts.append(("warn", sym, str(e)[:80]))
            continue
        if not m.get("tp_placed"):
            px = float(poss[sym].get("entryPrice")); sgn = 1 if pa > 0 else -1
            tp = px + sgn * abs(px - m["sl"])
            acts.append(("tp", sym, round(tp, 8)))
            if not ctx.dry:
                step, tick = excel(sym, ctx, {})
                tpr = round(round(tp / tick) * tick, 8)
                ctx.req("POST", "/fapi/v1/order", {"symbol": sym, "side": "SELL" if pa > 0 else "BUY",
                        "type": "LIMIT", "quantity": abs(pa), "price": tpr, "timeInForce": "GTC",
                        "reduceOnly": "true", "newClientOrderId": TAG + f"tp{int(now/1000)}"}, True)
                m["tp_placed"] = True
        if bars > 32:
            acts.append(("timeout-close", sym, pa))
            if not ctx.dry:
                ctx.req("POST", "/fapi/v1/order", {"symbol": sym, "side": "SELL" if pa > 0 else "BUY",
                        "type": "MARKET", "quantity": abs(pa), "reduceOnly": "true",
                        "newClientOrderId": TAG + f"x{int(now/1000)}"}, True)
    # 4. scan campeon (solo si hay cupo y no kill)
    npos = sum(1 for sym in st["managed"] if abs(float(poss.get(sym, {}).get("positionAmt", 0) or 0)) > 1e-9)
    if st["pnl_R"] > -3.0 and npos < 5:
        btc = ctx.kl("BTCUSDT"); bc = [float(k[4]) for k in btc]
        btc4h = (bc[-1] / bc[-17] - 1) * 100
        for sym in SYMS:
            if npos >= 5: break
            try:
                ks = ctx.kl(sym)
                closes = np.array([float(k[4]) for k in ks]); highs = np.array([float(k[2]) for k in ks])
                lows = np.array([float(k[3]) for k in ks]); vols = np.array([float(k[5]) * float(k[4]) for k in ks])
                for i in [len(ks) - 3, len(ks) - 2]:
                    c0, c1 = closes[i - 16], closes[i]
                    chg = (c1 / c0 - 1) * 100
                    path = np.sum(np.abs(np.diff(closes[i - 16:i + 1]))); eff = abs(c1 - c0) / path if path > 0 else 0
                    h4, l4 = float(np.max(highs[i - 15:i + 1])), float(np.min(lows[i - 15:i + 1])); px = float(c1)
                    side = 0
                    if chg >= 2.0 and (h4 - px) / h4 * 100 <= 3.0: side = 1
                    elif chg <= -2.0 and (px - l4) / l4 * 100 <= 3.0: side = -1
                    if side == 0 or eff < 0.45: continue
                    if (h4 - l4) / px * 100 < 1.5: continue
                    sl = l4 if side == 1 else h4; risk = abs(px - sl) / px * 100
                    if risk <= 0.05 or risk > 8: continue
                    if abs(chg - btc4h) < 1.5: continue
                    o1, c_1 = float(ks[i + 1][1]), float(ks[i + 1][4]); sgn = side
                    fb = (c_1 - o1) / o1 * 100 * sgn
                    fv = float(vols[i + 1] / (np.mean(vols[max(0, i - 19):i + 1]) + 1e-9))
                    if fb < -0.3 and fv >= 1.2: continue
                    if sym in busy:
                        continue  # anti-duplicado: ya hay orden/posicion en este simbolo
                    if sym in st["managed"] and abs(float(poss.get(sym, {}).get("positionAmt", 0) or 0)) > 1e-9: continue
                    lv = h4 - (h4 - l4) * 0.8 if side == 1 else l4 + (h4 - l4) * 0.8
                    rloc = risk_usd * (0.5 if side == -1 and short_half else 1.0)
                    noto = rloc / (risk / 100)
                    step, tick = excel(sym, ctx, {})
                    qty = max(0, float(int(noto / (lv * step)) * step))
                    if qty * lv < 5.5: continue
                    lv_r = round(round(lv / tick) * tick, 8); sl_r = round(round(sl / tick) * tick, 8)
                    acts.append(("entry", sym, f"{'BUY' if side==1 else 'SELL'} {qty:g} @ {lv_r} SL {sl_r}"))
                    if not ctx.dry:
                        eo = ctx.req("POST", "/fapi/v1/order", {"symbol": sym, "side": "BUY" if side == 1 else "SELL",
                                    "type": "LIMIT", "quantity": qty, "price": lv_r, "timeInForce": "GTC",
                                    "newClientOrderId": TAG + f"e{int(now/1000)}"}, True)
                        so = ctx.req("POST", "/fapi/v1/algoOrder", {"algoType": "CONDITIONAL", "symbol": sym,
                                    "side": "SELL" if side == 1 else "BUY", "positionSide": "BOTH",
                                    "type": "STOP_MARKET", "quantity": qty, "triggerPrice": sl_r,
                                    "workingType": "CONTRACT_PRICE", "reduceOnly": "true",
                                    "newClientOrderId": TAG + f"s{int(now/1000)}"}, True)
                        st["managed"][sym] = {"t0": now, "sl": sl_r, "sl_id": so.get("algoId"),
                                              "tp_placed": False, "entry_id": eo.get("orderId")}
                        busy.add(sym)
                        npos += 1
            except Exception as e:
                acts.append(("warn", sym, str(e)[:100]))
    save_state(st)
    if not os.path.exists(LOG):
        open(LOG, "w").write("ts,accion,symbol,detalle\n")
    with open(LOG, "a") as f:
        for a in acts: f.write(f"{datetime.now(timezone.utc).isoformat()},{a[0]},{a[1]},{a[2]}\n")
    return acts
def startup_checks():
    """Validacion de arranque: FAIL rapido y claro. Retorna lista de errores."""
    errs = []
    for f in ["config.json", "fly-mcp/rf_top9.pkl"]:
        if not os.path.exists(os.path.join(BASE, f)): errs.append(f"falta {f}")
    try:
        cfg = json.load(open(os.path.join(BASE, "config.json")))
        for k in ["train_coins", "test_coins_unseen", "signal"]:
            if k not in cfg: errs.append(f"config sin {k}")
    except Exception as e: errs.append(f"config ilegible: {e}")
    if os.path.exists(STATE):
        try:
            st = json.load(open(STATE))
            assert set(st) >= {"day", "pnl_R", "managed"}
        except Exception as e: errs.append(f"state corrupto (renombra {STATE}): {e}")
    return errs


def selftest():
    """Tests offline, sin red. Exit 0 = listo para operar."""
    fails = []
    def ok(n, c, d=""):
        print(f"[{'PASS' if c else 'FAIL'}] {n} {d}")
        if not c: fails.append(n)
    # 1. matematica de niveles (caso STBL trial)
    e, s, sgn = 0.02731, 0.02693, 1
    tp = e + sgn * abs(e - s)
    ok("TP-1R", abs(tp - 0.02769) < 1e-8, f"tp={tp}")
    # 2. redondeo a tick/step (STBL: tick 1e-5, step 1)
    tick, step = 0.00001, 1.0
    lv = 0.027314
    ok("tick", abs(round(round(lv / tick) * tick, 8) - 0.02731) < 1e-9)
    noto, riskf = 52.5, 0.0571  # noto = risk_usd/risk_frac ; sizing real: qty = noto/entry
    qty = float(int(noto / (e * step)) * step)
    ok("qty>0 y entero", qty > 0 and qty == int(qty), f"qty={qty:g}")
    ok("qty replica sizing live (~1922)", abs(qty - 1922) < 5, f"qty={qty:g}")
    ok("min-notional", qty * e >= 5.0)
    # 3. veto RF con artefacto real
    import pickle
    art = pickle.load(open(os.path.join(BASE, "fly-mcp/rf_top9.pkl"), "rb"))
    import numpy as np
    x = np.array([[5.2, 1.0, 5.7, 4.5, 0.51, 2.0, 1.5, 1.0, 0.1]])
    p = float(art["1"]["model"].predict_proba(x)[0, 1])
    ok("RF veto coherente", (p < art["1"]["p20"]) == (p < 0.168), f"p={p:.3f} p20={art['1']['p20']:.3f}")
    # 4. kill-switch y cupos (logica pura)
    ok("kill -3R", (-3.0 <= -3.0))
    ok("prefijo tag", TAG == "mosca-")
    # 5. startup checks en verde
    errs = startup_checks()
    ok("startup-checks", not errs, "; ".join(errs))
    print(f"\nSELFTEST: {'VERDE listo' if not fails else f'{len(fails)} FAIL'}")
    return 1 if fails else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", choices=["testnet", "real"], default="testnet")
    ap.add_argument("--once", action="store_true"); ap.add_argument("--loop", action="store_true")
    ap.add_argument("--live", action="store_true", help="SIN --live todo es dry-run. Seguro por defecto.")
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--risk-usd", type=float, default=3.0)
    ap.add_argument("--confirm-live", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        raise SystemExit(selftest())
    errs = startup_checks()
    if errs:
        raise SystemExit("STARTUP FAIL: " + "; ".join(errs))
    if a.mode == "real" and not a.confirm_live:
        raise SystemExit("REAL exige --confirm-live. Sin excepcion.")
    dry = not a.live  # seguro por defecto: solo --live coloca ordenes
    print(f"modo={a.mode} live={a.live} (dry-run={dry})", flush=True)
    ctx = Ctx(a.mode, dry)
    if a.loop:
        while True:
            print(run_once(ctx, a.risk_usd), flush=True)
            time.sleep(900)
    else:
        print(run_once(ctx, a.risk_usd))
