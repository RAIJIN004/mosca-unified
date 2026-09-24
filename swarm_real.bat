@echo off
REM Enjambre x3 REAL. Dinero de verdad.
call "%~dp0keys_real.bat"
start "mosca0R" python "%~dp0auto_bot.py" --mode real --confirm-live --loop --live --shard 0/3 --tag mosca0- --state auto_state0.json --log trades0.csv
start "mosca1R" python "%~dp0auto_bot.py" --mode real --confirm-live --loop --live --shard 1/3 --tag mosca1- --state auto_state1.json --log trades1.csv
start "mosca2R" python "%~dp0auto_bot.py" --mode real --confirm-live --loop --live --shard 2/3 --tag mosca2- --state auto_state2.json --log trades2.csv
echo 3 moscas REAL lanzadas.
pause
