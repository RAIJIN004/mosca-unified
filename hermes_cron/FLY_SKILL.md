# FLY SKILL — Instrucciones del cron Hermes para operar a la mosca (campeón V3-deep)
# La mosca PROPONE, la IA DISPONE (veto, riesgo, ejecución). Leer state_schema.json primero.

## Cada run (cada 15 min, +60s tras cierre de vela)
1. SYNC: trae posiciones, órdenes abiertas y balance. Marca kill_switch=true si pnl_día <= -3R o margen>50%. Si kill, solo gestiona salidas, cero entradas nuevas.
2. GESTIONA lo abierto (solo origen=mosca):
   - Entrada limit con edad>12 velas → CANCELAR.
   - Entry llenada sin TP → LIMIT opuesto a TP(1R) YA.
   - Posición con 32 velas → MARKET close. SL/TP condicionales ya hacen su trabajo; verifica que existan.
   - Trial abierto STBLUSDT (entry 286427756, SL algo 1000000217221642): si filled y sin TP → colocar TP.
3. SCAN (testnet o real según modo): klines 15m universo 25 monedas + BTC. Detecta impulso 4h (chg>=2%, eff>=0.35, borde<=3%, rango>=1.5%, riesgo<=8%).
4. FILTRA: LONG eff>=0.45, |alpha|>=1.5, sin pullback-con-volumen (1ra vela <-0.3% con vol>=1.2x). SHORT espejo solo con size 50%.
5. MENÚ: elige máx 3 entradas nuevas (mejor score RF/prob; si empate, mayor |alpha|). Cupo: máx 5 posiciones mosca. Riesgo $3 c/u (testnet; real se define aparte).
6. COLOCA: LIMIT al 80% retroceso + SL STOP_MARKET reduceOnly. clientOrderId prefijo `mosca-`. TP al fill.
7. LOG: anexa a trades.csv (ts, symbol, lado, entry, sl, tp, fill_ts, exit_ts, R, fees, split-regimen). Sin log no hay reentreno.

## Prohibido
- Tocar posiciones/órdenes sin prefijo mosca- (ej. AVAUSDT).
- Entradas SHORT size full (tope 50% hasta nuevo aviso: en no-vistas rinden 71-73%).
- BE manual, hedge-pullback, piramidar arriba (todo refutado en tests).
- Más de 3 entradas por run / operar con kill_switch.

## Reentreno semanal
- Domingos: re-corre f5/f6 con datos nuevos; si AUC<0.55 o win testA<75% → fallback a reglas y avisa.
