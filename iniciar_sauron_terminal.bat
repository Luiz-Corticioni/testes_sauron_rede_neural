@echo off
setlocal
cd /d "%~dp0"
title Sauron - Inventario de Ciberseguranca

if not exist ".venv\Scripts\python.exe" (
    echo [SAURON] Criando ambiente virtual...
    py -3.12 -m venv .venv
    if errorlevel 1 goto :erro
)

".venv\Scripts\python.exe" -c "import django, numpy, whitenoise" >nul 2>&1
if errorlevel 1 (
    echo [SAURON] Instalando dependencias na primeira execucao...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto :erro
)

".venv\Scripts\python.exe" scripts\preparar_ambiente.py
".venv\Scripts\python.exe" sauron.py
goto :fim

:erro
echo.
echo [ERRO] Nao foi possivel preparar o Sauron.
echo Verifique se o Python esta instalado e se ha acesso a internet.
echo Se faltar Python 3.12, use: py install 3.12

:fim
echo.
pause
endlocal
