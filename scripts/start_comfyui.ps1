# Inicia ComfyUI en el puerto 8188 (local). FrameFactory-AI usa COMFYUI_URL=http://127.0.0.1:8188
# Uso: .\scripts\start_comfyui.ps1 [ruta_a_ComfyUI]
# Si no pasás ruta, usa $env:COMFYUI_PATH o busca en ubicaciones habituales.

$ErrorActionPreference = "Stop"
$PORT = 8188

$comfyPath = $args[0]
if (-not $comfyPath -and $env:COMFYUI_PATH) {
    $comfyPath = $env:COMFYUI_PATH.Trim()
}
if (-not $comfyPath) {
    $candidates = @(
        (Join-Path $PSScriptRoot "..\ComfyUI"),
        (Join-Path $env:USERPROFILE "ComfyUI"),
        "C:\ComfyUI"
    )
    foreach ($c in $candidates) {
        $mainPy = Join-Path $c "main.py"
        if (Test-Path $mainPy) {
            $comfyPath = $c
            break
        }
    }
}

if (-not $comfyPath -or -not (Test-Path (Join-Path $comfyPath "main.py"))) {
    Write-Host "No se encontró ComfyUI (main.py)." -ForegroundColor Red
    Write-Host "  - Pasá la ruta: .\scripts\start_comfyui.ps1 C:\ruta\a\ComfyUI"
    Write-Host "  - O definí COMFYUI_PATH en .env / entorno apuntando a la carpeta de ComfyUI."
    exit 1
}

Write-Host "Iniciando ComfyUI en http://127.0.0.1:$PORT (carpeta: $comfyPath)" -ForegroundColor Green
Set-Location $comfyPath
& python main.py --port $PORT
