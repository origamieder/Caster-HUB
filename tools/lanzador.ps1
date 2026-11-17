# Abre Caster Hub en su propia ventana servido desde http://localhost, para que Windows muestre
# el icono del campeonato en la barra de título y en la barra de tareas (con file:// el navegador
# siempre pone el globo genérico). El servidor solo escucha en este PC y se apaga al cerrar la ventana.
# Lo lanza "lanzar.vbs" (sin ventana de consola); lo instala tools\instalar.ps1.
param([string]$Dir = $PSScriptRoot, [int]$Port = 47826)
$ErrorActionPreference = "Stop"
$url = "http://localhost:$Port/"
$perfil = Join-Path $Dir "perfil-navegador"

$navegador = @(
    "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe",
    "$env:ProgramFiles\Google\Chrome\Application\chrome.exe",
    "${env:ProgramFiles(x86)}\Google\Chrome\Application\chrome.exe",
    "$env:LOCALAPPDATA\Google\Chrome\Application\chrome.exe"
) | Where-Object { $_ -and (Test-Path $_) } | Select-Object -First 1

if (-not $navegador) { Start-Process (Join-Path $Dir "index.html"); exit }   # sin Chrome/Edge: abre el archivo tal cual
$abrir = { Start-Process -FilePath $navegador -ArgumentList "--app=$url", "--user-data-dir=`"$perfil`"", "--no-first-run", "--start-maximized" -PassThru }

$l = New-Object System.Net.HttpListener
$l.Prefixes.Add($url)
try { $l.Start() } catch { & $abrir | Out-Null; exit }   # ya hay un Hub abierto sirviendo: solo abre otra ventana

$tipos = @{ ".html" = "text/html; charset=utf-8"; ".ico" = "image/x-icon"; ".png" = "image/png"; ".json" = "application/json" }
$raiz = (Resolve-Path $Dir).Path
$proc = & $abrir
$pend = $l.BeginGetContext($null, $null)
try {
    while ($true) {
        if ($pend.AsyncWaitHandle.WaitOne(500)) {
            $ctx = $l.EndGetContext($pend); $pend = $l.BeginGetContext($null, $null)
            $ruta = [Uri]::UnescapeDataString($ctx.Request.Url.AbsolutePath.TrimStart("/"))
            if (-not $ruta) { $ruta = "index.html" }
            $f = [IO.Path]::GetFullPath((Join-Path $raiz $ruta))
            $res = $ctx.Response
            if ($f.StartsWith($raiz) -and (Test-Path $f -PathType Leaf)) {
                $bytes = [IO.File]::ReadAllBytes($f)
                $res.ContentType = $tipos[[IO.Path]::GetExtension($f).ToLower()]
                $res.Headers.Add("Cache-Control", "no-cache")
                $res.ContentLength64 = $bytes.Length; $res.OutputStream.Write($bytes, 0, $bytes.Length)
            } else { $res.StatusCode = 404 }
            $res.Close()
        }
        # La ventana usa su propio perfil, así que el proceso del navegador vive mientras esté abierta.
        if ($proc.HasExited -and -not (Get-CimInstance Win32_Process -Filter "Name='$(Split-Path $navegador -Leaf)'" | Where-Object { $_.CommandLine -like "*$perfil*" })) { break }
    }
} finally { $l.Stop(); $l.Close() }
