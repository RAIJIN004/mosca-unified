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

## Bot autónomo
```bash
python auto_bot.py --selftest                        # tests offline (debe dar VERDE)
python auto_bot.py --mode testnet --once             # dry-run por defecto (seguro)
python auto_bot.py --mode testnet --loop --live      # opera demo cada 15 min
python auto_bot.py --mode real --confirm-live --live # REAL (doble seguro)
python watcher.py                                    # auditor read-only
```
## Doble-clic (.bat, sin IA)
```bat
trade_testnet.bat status STBLUSDT
trade_testnet.bat place-entry STBLUSDT BUY 1922 0.02731 --sl 0.02693
trade_testnet.bat cancel STBLUSDT --order-id 286427756
trade_testnet.bat close STBLUSDT
trade_real.bat status BTCUSDT   (exige CONFIRM_LIVE=1, ya incluido)
```
Verificado en testnet: status/place/cancel/close OK (reloj auto-sincronizado, firma exacta).
`keys_testnet.bat` / `keys_real.bat` viven solo en local (gitignored). OJO: contienen secretos.
Investigación, no asesoría financiera. DYOR.
