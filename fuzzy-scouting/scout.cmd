@echo off
rem Lanceur Windows : double-clic (ou `scout`) = interface web. Voir `scout help`.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\scout.ps1" %*
set RC=%errorlevel%
rem Double-clic (aucun argument) : garder la fenetre ouverte si une erreur s'est produite.
if "%~1"=="" if not "%RC%"=="0" pause
exit /b %RC%
