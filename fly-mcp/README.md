# fly-mcp — la mosca como MCP de Hermes

Herramientas: `score_setup` (veto p20), `scan_champion` (setups live con entry/SL/TP),
`sync_state` (conciencia: acciones sobre posiciones/órdenes), `exit_plan` (TP 1R + fees).

Uso en Hermes: agrega este server a la config MCP y que el cron llame
`sync_state` → `scan_champion` → `score_setup` cada 15 min (ver `../hermes_cron/FLY_SKILL.md`).
La mosca propone, la IA dispone (coloca/cancela con sus tools de Binance).

Artefacto `rf_top9.pkl` (4.8 MB): RF por lado entrenado en split train + umbrales p20/p40.
Regenerar: `python ../train_artifact.py`.
