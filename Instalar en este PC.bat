@echo off
chcp 65001 >nul
title Instalar Caster Hub
echo.
echo   Instalando Caster Hub en este PC...
echo   (no necesita permisos de administrador ni internet)
echo.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0tools\instalar.ps1"
if errorlevel 1 (
  echo.
  echo   ERROR: no se pudo instalar. Revisa el mensaje de arriba.
  pause
  exit /b 1
)
echo.
echo   Listo. Puedes cerrar esta ventana.
timeout /t 8 >nul
