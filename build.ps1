# Сборка exe: powershell -ExecutionPolicy Bypass -File build.ps1
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path

if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "Python не найден — установи python.org, галочка Add to PATH" -ForegroundColor Red
    exit 1
}

python -m pip install --upgrade pyinstaller
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

python -m PyInstaller --onefile --clean --name nursultan-internet-bridge `
    --distpath "$root\dist" --workpath "$root\build" --specpath "$root\build" `
    "$root\bridge\nursultan_bridge.py"
if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }

Copy-Item "$root\bridge\bridge.json" "$root\dist\bridge.json" -Force
Write-Host "Готово: dist\nursultan-internet-bridge.exe + dist\bridge.json" -ForegroundColor Green
