"""Testnet trial campeon (2026-09-24): STBLUSDT LONG.
Senal: eff=0.51 alpha=+5.2 fb OK. Niveles: entry 0.02731 / SL 0.02693 / TP 0.02769, qty 1922 (~$52, riesgo ~$3).
Ordenes: entry LIMIT orderId 286427756; SL STOP_MARKET reduceOnly algoId 1000000217221642.
TP: NO pre-colocar (esta bajo el precio actual -> trigger inmediato). Al llenar entry, LIMIT SELL 1922 @ 0.02769.
"""
ENTRY=286427756
SYM="STBLUSDT"; QTY=1922; TP=0.02769
print(f"Monitorear {SYM} entry {ENTRY}; al fill: LIMIT SELL {QTY} @ {TP}")
