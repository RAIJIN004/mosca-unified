"""CLI robusto estilo MCP: status / place-entry / cancel / close / tp. Exit 0=ok, 1=error claro."""
import argparse, hashlib, hmac, json, os, sys, time
import requests
URLS = {"testnet": "https://demo-fapi.binance.com", "real": "https://fapi.binance.com"}
TAG = "mosca-"
def keys(mode):
    if mode == "testnet": k, s = os.getenv("TESTNET_KEY", ""), os.getenv("TESTNET_SECRET", "")
    else: k, s = os.getenv("BINANCE_KEY", ""), os.getenv("BINANCE_SECRET", "")
    if not k or not s: sys.exit("FATAL: faltan keys en env. Testnet: keys_testnet.bat. Real: keys_real.bat.")
    return k, s
class B:
    def __init__(s, mode):
        s.base = URLS[mode]; s.key, s.sec = keys(mode); s._toff = None
    def ts(s):
        if s._toff is None:
            try:
                srv = requests.get(s.base + "/fapi/v1/time", timeout=15).json()["serverTime"]
                s._toff = srv - int(time.time() * 1000)
            except Exception:
                s._toff = 0
        return int(time.time() * 1000) + s._toff
    def req(s, m, path, p=None, signed=False, retry=True):
        p = dict(p or {})
        headers = {"X-MBX-APIKEY": s.key} if signed else {}
        url = s.base + path
        data = None
        if signed:
            p.update({"timestamp": s.ts(), "recvWindow": 30000})
            qs = "&".join(f"{k}={p[k]}" for k in sorted(p))
            qs += "&signature=" + hmac.new(s.sec.encode(), qs.encode(), hashlib.sha256).hexdigest()
            if m == "GET":
                url += "?" + qs
            else:
                data = qs
                headers["Content-Type"] = "application/x-www-form-urlencoded"
            params = None
        else:
            params = p or None
        try:
            r = requests.request(m, url, params=params, data=data, headers=headers, timeout=20)
            r.raise_for_status()
            return r.json() if r.text else {}
        except requests.HTTPError as e:
            if retry and r.status_code in (418, 429, 500, 502, 503):
                time.sleep(2); return s.req(m, path, p, signed, False)
            try: msg = r.json().get("msg", r.text[:150])
            except Exception: msg = r.text[:150]
            sys.exit(f"BINANCE {r.status_code}: {msg}")
    def filt(s, sym):
        info = s.req("GET", "/fapi/v1/exchangeInfo")
        x = [z for z in info["symbols"] if z["symbol"] == sym]
        if not x: sys.exit(f"FATAL: {sym} no existe en este modo.")
        f = {z["filterType"]: z for z in x[0]["filters"]}
        return float(f["LOT_SIZE"]["stepSize"]), float(f["PRICE_FILTER"]["tickSize"]), float(f.get("MIN_NOTIONAL", {}).get("notional", 5))
def rnd(v, step):
    return round(round(v / step) * step, 8)
def cmd_status(b, sym):
    px = float(b.req("GET", "/fapi/v1/ticker/price", {"symbol": sym})["price"])
    pr = [p for p in b.req("GET", "/fapi/v2/positionRisk", signed=True) if p["symbol"] == sym]
    pa = float(pr[0]["positionAmt"]) if pr else 0
    oo = b.req("GET", "/fapi/v1/openOrders", {"symbol": sym}, True)
    ao = b.req("GET", "/fapi/v1/openAlgoOrders", {"symbol": sym}, True)
    ao = ao.get("orders", ao) if isinstance(ao, dict) else ao
    print(json.dumps({"symbol": sym, "mark": px, "positionAmt": pa,
                      "entry": pr[0]["entryPrice"] if pr else None,
                      "uPnL": pr[0]["unRealizedProfit"] if pr else None,
                      "open_orders": [{k: o.get(k) for k in ("orderId", "type", "side", "price", "origQty", "stopPrice", "status", "clientOrderId")} for o in oo],
                      "algo_orders": [{k: o.get(k) for k in ("algoId", "orderType", "side", "triggerPrice", "quantity", "algoStatus")} for o in (ao or [])]}, indent=1))
def cmd_place(b, a):
    step, tick, minN = b.filt(a.symbol)
    qty = float(int(a.qty / step) * step)
    if qty <= 0: sys.exit("FATAL: qty bajo el stepSize.")
    if qty * a.entry < minN: sys.exit(f"FATAL: nocional {qty*a.entry:.2f} < minimo {minN}.")
    e = b.req("POST", "/fapi/v1/order", {"symbol": a.symbol, "side": a.side, "type": "LIMIT",
              "quantity": qty, "price": rnd(a.entry, tick), "timeInForce": "GTC",
              "newClientOrderId": TAG + f"e{int(time.time())}"}, True)
    print("ENTRY:", e.get("orderId"), e.get("status"))
    if a.sl:
        s = b.req("POST", "/fapi/v1/order", {"symbol": a.symbol, "side": "SELL" if a.side == "BUY" else "BUY",
                  "type": "STOP_MARKET", "stopPrice": rnd(a.sl, tick), "closePosition": "false",
                  "reduceOnly": "true", "quantity": qty,
                  "newClientOrderId": TAG + f"s{int(time.time())}"}, True)
        print("SL:", s.get("algoId", s.get("orderId")), s.get("algoStatus", s.get("status")))
def cmd_cancel(b, a):
    oo = b.req("GET", "/fapi/v1/openOrders", {"symbol": a.symbol}, True)
    mine = [o for o in oo if str(o.get("clientOrderId", "")).startswith(TAG) or a.all]
    if a.order_id: mine = [o for o in oo if str(o["orderId"]) == str(a.order_id)]
    if not mine: print("nada que cancelar"); return
    for o in mine:
        b.req("DELETE", "/fapi/v1/order", {"symbol": a.symbol, "orderId": o["orderId"]}, True)
        print("cancelada:", o["orderId"], o.get("clientOrderId"))
def cmd_close(b, a):
    pr = [p for p in b.req("GET", "/fapi/v2/positionRisk", signed=True) if p["symbol"] == a.symbol][0]
    pa = float(pr["positionAmt"])
    if abs(pa) < 1e-9: print("sin posicion"); return
    step, _, _ = b.filt(a.symbol)
    q = float(int(abs(pa) / step) * step)
    r = b.req("POST", "/fapi/v1/order", {"symbol": a.symbol, "side": "SELL" if pa > 0 else "BUY",
              "type": "MARKET", "quantity": q, "reduceOnly": "true",
              "newClientOrderId": TAG + f"x{int(time.time())}"}, True)
    print("CLOSED:", r.get("orderId"), r.get("status"))
def cmd_tp(b, a):
    step, tick, _ = b.filt(a.symbol)
    r = b.req("POST", "/fapi/v1/order", {"symbol": a.symbol, "side": a.side, "type": "LIMIT",
              "quantity": float(int(a.qty / step) * step), "price": rnd(a.price, tick),
              "timeInForce": "GTC", "reduceOnly": "true",
              "newClientOrderId": TAG + f"tp{int(time.time())}"}, True)
    print("TP:", r.get("orderId"), r.get("status"))
if __name__ == "__main__":
    ap = argparse.ArgumentParser(prog="trade")
    ap.add_argument("--mode", choices=["testnet", "real"], default="testnet")
    sub = ap.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("status"); s.add_argument("symbol")
    p = sub.add_parser("place-entry"); p.add_argument("symbol"); p.add_argument("side", choices=["BUY", "SELL"])
    p.add_argument("qty", type=float); p.add_argument("entry", type=float); p.add_argument("--sl", type=float)
    c = sub.add_parser("cancel"); c.add_argument("symbol"); c.add_argument("--order-id"); c.add_argument("--all", action="store_true")
    x = sub.add_parser("close"); x.add_argument("symbol")
    t = sub.add_parser("tp"); t.add_argument("symbol"); t.add_argument("side", choices=["BUY", "SELL"])
    t.add_argument("qty", type=float); t.add_argument("price", type=float)
    a = ap.parse_args()
    if a.mode == "real" and os.getenv("CONFIRM_LIVE") != "1":
        sys.exit("FATAL: REAL exige CONFIRM_LIVE=1.")
    b = B(a.mode)
    {"status": lambda: cmd_status(b, a.symbol.upper()),
     "place-entry": lambda: cmd_place(b, a),
     "cancel": lambda: cmd_cancel(b, a),
     "close": lambda: cmd_close(b, a),
     "tp": lambda: cmd_tp(b, a)}[a.cmd]()
    print("OK")
