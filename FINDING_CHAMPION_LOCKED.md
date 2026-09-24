# HALLAZGO BLOQUEADO — No editar. 2026-09-24. Champion V3-deep LONG.

## Política
- Gate: unified TOP (escalera v6>v12>v24 + alpha + book), lado LONG.
- Filtro: eff>=0.45, |alpha|>=1.5, NO pullback-inmediato-con-volumen (1ra vela 15m <-0.3% con vol>=1.2x).
- Entrada: LIMIT al 80% de retroceso del rango 4h (16x15m). Expira 12 velas. Invalida si SL toca primero (misma vela = SL primero).
- SL: low_4h. TP: 1R. Timeout: 32 velas (8h) a mercado.

## Resultado validado (119 días, 25 monedas, N=40643 señales, 622 fills)
- GLOBAL: 5.2 tr/día, win 85.9%, avgR bruto +0.720, fee medio 0.126R → neto +0.594.
- train 85.8% | val 89.2% | testA (no vistas+futuro) 84.7% | testB (no vistas) 84.1%.
- Escala: frac 0.618→54% / 0.7→66% / 0.75→76% / 0.8→86% win.

## No-hallazgos (igual de importantes)
- Breakeven +0.5R DESTRUYE (misma-vela stop-primero). Fuera.
- Scalp TP 0.4-0.5 sin edge: win 32-44%, avgR negativo.
- Hedge-pullback pierde vs hold (-0.2R/trade).
- RF LONG AUC 0.49 (azar, no usar); RF SHORT AUC 0.75-0.78 (veto).
- CNN fotos no supera tabular (kill-criteria → híbrido).

## Repro
`f1_manifest.py → f1_render.py → f1_validate.py → f5_champion.py` (PASS IMPECABLE).
Scripts previos: pullback_backtest, pattern_mining/validate, hedge_pullback, rf_exit/big/eval/final, f2/f3/f4.
