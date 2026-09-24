@echo off
REM Mosca trader - TESTNET demo. Doble clic = menu. O con args: trade_testnet.bat status STBLUSDT
call "%~dp0keys_testnet.bat"
if "%~1"=="" goto menu
python "%~dp0trade_cli.py" --mode testnet %*
goto fin
:menu
:loop
echo.
echo === MOSCA TESTNET ===
echo 1. status SYMBOL
echo 2. place-entry SYMBOL BUY/SELL QTY ENTRY [--sl SL]
echo 3. cancel SYMBOL --order-id ID
echo 4. close SYMBOL
echo 5. tp SYMBOL BUY/SELL QTY PRICE
echo 0. salir
set /p op="opcion: "
if "%op%"=="0" goto fin
if "%op%"=="1" set cmd=status
if "%op%"=="2" set cmd=place-entry
if "%op%"=="3" set cmd=cancel
if "%op%"=="4" set cmd=close
if "%op%"=="5" set cmd=tp
set /p args="args: "
python "%~dp0trade_cli.py" --mode testnet %cmd% %args%
goto loop
:fin
pause
