@echo off
title MediaFinder - Buscador Rapido de Midias
echo Iniciando o MediaFinder...
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocorreu um erro ao iniciar. Verifique se as dependencias estao instaladas:
    echo pip install -r requirements.txt
    pause
)
