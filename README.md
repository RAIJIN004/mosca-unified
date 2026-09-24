# Mosca-Unified — V3-deep entry system + fly-brain RL track

Champion (locked in `FINDING_CHAMPION_LOCKED.md`): LONG limit at **80% retracement** of 4h range on unified-TOP setups → **85.9% win, +0.59R net, 5.2 trades/day** (119d, 25 coins, validated on unseen coins + future time).

## Estructura
- `config.json` — seeds, monedas vistas/no-vistas, parámetros.
- `f0_make_photos.py` / `f0_validate.py` — demo + validador PASS/FAIL.
- `f1_manifest.py` — manifiesto full (40.6k señales, splits train/val/testA/testB).
- `f1_render.py` — fotos triple-panel (BTC + alt + estado), con resume.
- `f1_validate.py` — validador 12 checks (IMPECABLE).
- `f1_cnn.py` — baseline CNN-vs-RF + detectores de memorización.
- `f2_winrate.py` / `f3_menu.py` / `f4_remate.py` — sweeps y frontera winrate.
- `f5_champion.py` — validación del campeón por split + fees.
- `f6_extra.py` — SHORT espejo + sensibilidad.
- `manifests/` — CSVs (inmutables, con checksums en `CHECKSUMS.txt`).
- `testnet_bot.py` — bot de prueba testnet (tamaño mínimo).

## Repro
```bash
pip install requests numpy matplotlib scikit-learn torch pillow
python f1_manifest.py   # ~5 min (descarga klines Binance)
python f1_render.py     # fotos (resume seguro)
python f1_validate.py   # debe decir IMPECABLE
python f5_champion.py
```
`data/` (fotos, cache) se excluye de git: regenerable.

## Disclaimer
Investigación, no asesoría financiera. DYOR.
