@echo off
REM Enjambre x3 TESTNET: 3 moscas en paralelo (31 monedas, sin solapes).
call "%~dp0keys_testnet.bat"
start "mosca0" python "%~dp0auto_bot.py" --mode testnet --loop --live --shard 0/3 --tag mosca0- --state auto_state0.json --log trades0.csv
start "mosca1" python "%~dp0auto_bot.py" --mode testnet --loop --live --shard 1/3 --tag mosca1- --state auto_state1.json --log trades1.csv
start "mosca2" python "%~dp0auto_bot.py" --mode testnet --loop --live --shard 2/3 --tag mosca2- --state auto_state2.json --log trades2.csv
echo 3 moscas lanzadas. Cada ventana muestra su latido cada 15 min.
pause
