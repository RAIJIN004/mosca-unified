@echo off
REM Mosca AUTOMATICA - REAL. Dinero de verdad. Igual que el backtest.
call "%~dp0keys_real.bat"
python "%~dp0auto_bot.py" --mode real --confirm-live --loop --live %*
pause
