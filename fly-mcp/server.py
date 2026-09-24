"""MCP de la mosca-unified: score de setups, scan campeon live, sync de estado, plan de salida."""
import os
import pickle
import numpy as np
import requests
from mcp.server.fastmcp import FastMCP

BASE = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE, "rf_top9.pkl"), "rb") as f:
    ART = pickle.load(f)
TOP = ART["TOP"]

REAL = "https://fapi.binance.com"
TEST = "https://demo-fapi.binance.com"

mcp = FastMCP(
    "fly-mcp",
    description="Mosca-unified V3-deep: score de setups (veto p20), scan live campeón, sync de estado con conciencia, plan de salida. La mosca propone, la IA dispone.",
)


def _score(side: str, feats: dict) -> dict:
    m = ART[side]
    x = np.array([[float(feats[c]) for c in TOP]])
    p = float(m["model"].predict_proba(x)[0, 1])
    return {"p_win": round(p, 3), "veto_p20": bool(p < m["p20"]),
            "veredicto": ("SKIP" if p < m["p20"] else ("TOP" if p >= m["p40"] else "OK")),
            "th": {"p20": round(m["p20"], 3), "p40": round(m["p40"], 3)}}


def _klines(symbol: str, mode: str, n: int = 100):
    base = TEST if mode == "testnet" else REAL
    r = requests.get(base + "/fapi/v1/klines",
                     params={"symbol": symbol.upper(), "interval": "15m", "limit": n}, timeout=20)
    r.raise_for_status()
    return r.json()


@mcp.tool()
def score_setup(side: str, alpha: float, spike: float, risk: float, rng: float,
                eff: float, v6: float = 0, v12: float = 0, v24: float = 0,
                btc4h: float = 0) -> dict:
    """Scorea UN setup estilo-unified. Veto p20 = SKIP (gratis: mismo total, mejor avgR).

    Args:
        side: 1 LONG, -1 SHORT (SHORT rinde menos en no-vistas: size 50%).
        alpha/spike/risk/rng/eff: features del impulso 4h. v6/v12/v24/btc4h: ladder y régimen.
    Returns: p_win, veto_p20, veredicto SKIP/OK/TOP. ESTO NO ES ASESORÍA FINANCIERA. DYOR.
    """
    s = "1" if str(side) == "1" else "-1"
    out = _score(s, {"alpha": alpha, "spike": spike, "risk": risk, "rng": rng,
                     "eff": eff, "v6": v6, "v12": v12, "v24": v24, "btc4h": btc4h})
    if s == "-1":
        out["nota"] = "SHORT: en monedas no vistas win 71-73% vs LONG 84%. Size 50%."
    out["disclaimer"] = "ESTO NO ES ASESORÍA FINANCIERA. DYOR."
    return out


@mcp.tool()
def scan_champion(symbols: str = "ASTERUSDT,XPLUSDT,PUMPUSDT,STBLUSDT,0GUSDT,WLDUSDT,ENAUSDT,ARBUSDT,OPUSDT,INJUSDT,SUIUSDT,TIAUSDT",
                  mode: str = "testnet") -> dict:
    """Escanea el universo y devuelve setups campeón LIVE (LONG eff>=0.45, |alpha|>=1.5, sin pullback-con-vol).

    Cada setup trae entry (80% retroceso), SL (extremo 4h), TP (1R) + score. La IA filtra (cupos) y coloca.
    """
    btc = _klines("BTCUSDT", mode)
    bc = [float(k[4]) for k in btc]
    btc4h = (bc[-1] / bc[-17] - 1) * 100
    out = []
    for sym in [s.strip().upper() for s in symbols.split(",") if s.strip()]:
        try:
            ks = _klines(sym, mode)
            closes = np.array([float(k[4]) for k in ks]); highs = np.array([float(k[2]) for k in ks])
            lows = np.array([float(k[3]) for k in ks]); vols = np.array([float(k[5]) * float(k[4]) for k in ks])
            for i in [len(ks) - 3, len(ks) - 2]:
                c0, c1 = closes[i - 16], closes[i]
                chg = (c1 / c0 - 1) * 100
                path = np.sum(np.abs(np.diff(closes[i - 16:i + 1])))
                eff = abs(c1 - c0) / path if path > 0 else 0
                h4, l4 = float(np.max(highs[i - 15:i + 1])), float(np.min(lows[i - 15:i + 1]))
                px = float(c1)
                side = 0
                if chg >= 2.0 and (h4 - px) / h4 * 100 <= 3.0: side = 1
                elif chg <= -2.0 and (px - l4) / l4 * 100 <= 3.0: side = -1
                if side != 1 or eff < 0.45: continue
                if (h4 - l4) / px * 100 < 1.5: continue
                risk = (px - l4) / px * 100
                if risk <= 0.05 or risk > 8: continue
                alpha = chg - btc4h
                if abs(alpha) < 1.5: continue
                o1, c_1 = float(ks[i + 1][1]), float(ks[i + 1][4])
                fb = (c_1 - o1) / o1 * 100
                fv = float(vols[i + 1] / (np.mean(vols[max(0, i - 19):i + 1]) + 1e-9))
                if fb < -0.3 and fv >= 1.2: continue
                lv = h4 - (h4 - l4) * 0.8
                qv = vols[i - 16:i + 1]
                base = float(np.mean(qv[:-4]))
                spike = float(np.mean(qv[-4:]) / base) if base > 0 else 0
                sc = _score("1", {"alpha": alpha, "spike": min(spike, 5), "risk": risk, "rng": (h4 - l4) / px * 100,
                                  "eff": eff, "v6": 0, "v12": 0, "v24": 0, "btc4h": btc4h})
                out.append({"symbol": sym, "side": "LONG", "entry_80": round(lv, 6),
                            "sl": round(l4, 6), "tp_1R": round(lv + (lv - l4), 6),
                            "risk_pct": round(risk, 2), "eff": round(float(eff), 2),
                            "alpha": round(float(alpha), 1), "score": sc})
        except Exception as e:
            out.append({"symbol": sym, "error": str(e)[:120]})
    return {"mode": mode, "btc4h": round(btc4h, 2), "setups": out,
            "nota": "TP bajo el mark no pre-colocar: va al fill. Expira entry en 12 velas.",
            "disclaimer": "ESTO NO ES ASESORÍA FINANCIERA. DYOR."}


@mcp.tool()
def sync_state(positions: list, orders: list, balance: float, pnl_dia_R: float) -> dict:
    """Conciencia de la mosca: recibe estado vivo y devuelve acciones (la IA ejecuta).

    Args:
        positions: [{symbol, side, qty, entry, uPnL_R, velas_abierta, sl_ok, tp_ok, origen}]
        orders: [{symbol, tipo(entry_limit/sl/tp), precio, edad_velas, clientId}]
        balance: USDT. pnl_dia_R: PnL del día en R.
    Returns: kill_switch, acciones [cancelar_vencida, poner_TP_al_fill, cerrar_timeout, SKIP_nuevas].
    """
    acts = []
    kill = pnl_dia_R <= -3.0
    if kill:
        acts.append({"accion": "KILL", "detalle": "pnl_dia<=-3R: solo salidas, cero entradas"})
    for o in orders or []:
        if o.get("tipo") == "entry_limit" and int(o.get("edad_velas", 0)) > 12:
            acts.append({"accion": "cancelar_vencida", "symbol": o["symbol"], "detalle": o.get("clientId", "")})
    for p in positions or []:
        if p.get("origen") != "mosca":
            continue
        if not p.get("tp_ok"):
            acts.append({"accion": "poner_TP_al_fill", "symbol": p["symbol"],
                         "detalle": "LIMIT opuesto a 1R por qty total"})
        if int(p.get("velas_abierta", 0)) > 32:
            acts.append({"accion": "cerrar_timeout", "symbol": p["symbol"], "detalle": ">32 velas a mercado"})
    n_mosca = len([p for p in (positions or []) if p.get("origen") == "mosca"])
    if n_mosca >= 5:
        acts.append({"accion": "SKIP_nuevas", "detalle": "cupo 5 lleno"})
    return {"kill_switch": kill, "posiciones_mosca": n_mosca, "acciones": acts}


@mcp.tool()
def exit_plan(entry: float, stop: float, side: str = "1") -> dict:
    """Plan de salida V3-deep: TP 1R, timeout 32 velas, arrastre de fees estimado."""
    sgn = 1 if str(side) == "1" else -1
    rr = abs(entry - stop)
    tp = entry + sgn * rr
    fee_R = 0.10 / (rr / entry * 100) if entry and rr else 0
    return {"tp_1R": round(tp, 6), "timeout_velas": 32, "fee_R_aprox": round(fee_R, 3),
            "nota": "Sin breakeven (refutado), sin piramidar. Expira entry en 12 velas."}


if __name__ == "__main__":
    mcp.run()
