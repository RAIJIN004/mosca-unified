@echo off
REM Mosca AUTOMATICA - TESTNET demo. Opera sola cada 15 min (igual que el backtest).
call "%~dp0keys_testnet.bat"
python "%~dp0auto_bot.py" --mode testnet --loop --live %*
pause
