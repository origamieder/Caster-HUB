@echo off
chcp 65001 >nul
title Desinstalar Caster Hub
powershell -NoProfile -ExecutionPolicy Bypass -Command ^
  "$d=[Environment]::GetFolderPath('Desktop'); $m=Join-Path ([Environment]::GetFolderPath('Programs')) 'Caster Hub';" ^
  "Remove-Item (Join-Path $d 'Caster Hub.lnk') -ErrorAction SilentlyContinue;" ^
  "Remove-Item $m -Recurse -ErrorAction SilentlyContinue;" ^
  "Remove-Item (Join-Path $env:LOCALAPPDATA 'CasterHub') -Recurse -ErrorAction SilentlyContinue;" ^
  "Write-Host '  Caster Hub desinstalado de este PC.' -ForegroundColor Green"
timeout /t 5 >nul
