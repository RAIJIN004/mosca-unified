@echo off
REM Mosca trader — REAL. Dinero de verdad. Uso: trade_real.bat status BTCUSDT
call "%~dp0keys_real.bat"
python "%~dp0trade_cli.py" --mode real %*
pause
