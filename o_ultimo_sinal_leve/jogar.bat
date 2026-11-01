@echo off
cd /d "%~dp0"
echo Instalando/verificando dependencias...
py -3 -m pip install -r requirements.txt
echo Iniciando o jogo...
py -3 main.py
pause
