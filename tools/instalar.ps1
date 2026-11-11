# Instala Caster Hub en este PC: copia la app, crea accesos directos y la abre.
# Lo lanza "Instalar en este PC.bat"; no hace falta ejecutarlo a mano.
param(
    [string]$Origen = (Join-Path $PSScriptRoot "..\web"),
    [string]$Destino = (Join-Path $env:LOCALAPPDATA "CasterHub"),
    [string]$Escritorio = [Environment]::GetFolderPath("Desktop"),
    [string]$MenuInicio = (Join-Path ([Environment]::GetFolderPath("Programs")) "Caster Hub"),
    [switch]$NoAbrir
)
$ErrorActionPreference = "Stop"

$html = Join-Path $Origen "index.html"
if (-not (Test-Path $html)) { throw "No encuentro web\index.html. Ejecuta el instalador desde dentro de la carpeta CasterHub." }

New-Item -ItemType Directory -Force -Path $Destino | Out-Null
Copy-Item $html (Join-Path $Destino "index.html") -Force
$ico = Join-Path $Origen "casterhub.ico"
if (Test-Path $ico) { Copy-Item $ico (Join-Path $Destino "casterhub.ico") -Force }

$app = Join-Path $Destino "index.html"
$url = ([Uri]$app).AbsoluteUri

# Ventana propia sin barras: Edge (viene con Windows 10/11) o Chrome en modo aplicación.
$navegador = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

$perfil = Join-Path $Destino "perfil-navegador"
if ($navegador) {
    $exe = $navegador
    $args_ = "--app=`"$url`" --user-data-dir=`"$perfil`" --start-maximized --no-first-run"
} else {
    $exe = $app; $args_ = ""
}

$shell = New-Object -ComObject WScript.Shell
function Crear-Acceso($ruta) {
    $lnk = $shell.CreateShortcut($ruta)
    $lnk.TargetPath = $exe
    $lnk.Arguments = $args_
    $lnk.WorkingDirectory = $Destino
    $lnk.Description = "Caster Hub - Campeonato de España de Speedcubing 2026"
    if (Test-Path (Join-Path $Destino "casterhub.ico")) { $lnk.IconLocation = (Join-Path $Destino "casterhub.ico") + ",0" }
    $lnk.Save()
}
New-Item -ItemType Directory -Force -Path $Escritorio, $MenuInicio | Out-Null
Crear-Acceso (Join-Path $Escritorio "Caster Hub.lnk")
Crear-Acceso (Join-Path $MenuInicio "Caster Hub.lnk")

Write-Host ""
Write-Host "  Caster Hub instalado en: $Destino" -ForegroundColor Green
Write-Host "  Accesos directos: Escritorio y menu Inicio" -ForegroundColor Green
if ($navegador) { Write-Host "  Se abrira en ventana propia con: $(Split-Path $navegador -Leaf)" }
else { Write-Host "  No hay Edge ni Chrome: se abrira en el navegador predeterminado." -ForegroundColor Yellow }

if (-not $NoAbrir) {
    if ($navegador) { Start-Process -FilePath $navegador -ArgumentList $args_ } else { Start-Process $app }
}
