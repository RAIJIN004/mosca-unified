@echo off
REM Mosca trader — TESTNET demo. Uso: trade_testnet.bat status STBLUSDT
call "%~dp0keys_testnet.bat"
python "%~dp0trade_cli.py" --mode testnet %*
pause
