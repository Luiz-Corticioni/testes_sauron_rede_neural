@echo off
setlocal
cd /d "%~dp0"
title Sauron - Interface Web
if not exist ".venv\Scripts\python.exe" (
    py -3.12 -m venv .venv
    if errorlevel 1 goto :erro
)
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :erro
".venv\Scripts\python.exe" scripts\iniciar_web.py
if errorlevel 1 goto :erro
goto :fim
:erro
echo [SAURON] Confira a mensagem acima. O servidor nao iniciou com configuracao incompleta.
echo Se faltar Python 3.12, use: py install 3.12
:fim
pause
endlocal
