# Nursultan Internet Kit — проверка установки
# Запуск: powershell -ExecutionPolicy Bypass -File doctor.ps1

$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $MyInvocation.MyCommand.Path
$configPath = Join-Path $root "bridge\bridge.json"
$fail = 0

function Pass($msg) { Write-Host "[PASS] $msg" -ForegroundColor Green }
function Fail($msg) { Write-Host "[FAIL] $msg" -ForegroundColor Red; $script:fail++ }

if (-not (Test-Path $configPath)) {
    Fail "bridge\bridge.json не найден"
    exit 1
}
Pass "конфиг найден: $configPath"

try {
    $cfg = Get-Content $configPath -Raw -Encoding UTF8 | ConvertFrom-Json
    Pass "bridge.json читается"
} catch {
    Fail "bridge.json не разбирается: $($_.Exception.Message)"
    exit 1
}

if ([string]::IsNullOrWhiteSpace($cfg.mcpLink)) {
    Fail "mcpLink пуст — клиент → Scripts → MCP → Enabled → Copy link"
    exit 1
}
Pass "mcpLink заполнен"

$body = @{
    jsonrpc = "2.0"
    id = 1
    method = "tools/call"
    params = @{ name = "scripts_list"; arguments = @{} }
} | ConvertTo-Json -Depth 6

try {
    $resp = Invoke-RestMethod -Uri $cfg.mcpLink -Method Post -Body $body `
        -ContentType "application/json" -TimeoutSec 8
    $text = $resp.result.content | Where-Object { $_.type -eq "text" } | Select-Object -First 1
    $payload = $text.text | ConvertFrom-Json
    Pass "MCP отвечает, скриптов: $($payload.scripts.Count)"
} catch {
    Fail "MCP не отвечает: $($_.Exception.Message)"
    exit 1
}

if ($payload.assetsDir) {
    $probe = Join-Path $payload.assetsDir "_net\.doctor.tmp"
    try {
        $dir = Split-Path -Parent $probe
        if (-not (Test-Path $dir)) { New-Item -ItemType Directory -Path $dir -Force | Out-Null }
        "ok" | Set-Content -Path $probe -Encoding UTF8
        Remove-Item $probe -Force
        Pass "assets доступна на запись: $($payload.assetsDir)"
    } catch {
        Fail "assets недоступна на запись: $($_.Exception.Message)"
    }
} else {
    Fail "scripts_list не вернул assetsDir"
}

$secrets = @()
if ($cfg.secrets) { $secrets = @($cfg.secrets.PSObject.Properties.Name) }
if ($secrets.Count -gt 0) {
    Pass "secrets: $($secrets -join ', ')"
} else {
    Write-Host "[WARN] secrets пуст — ключи API не подставятся" -ForegroundColor Yellow
}

if ($fail -eq 0) {
    Write-Host "Установка в порядке. Запускай мост." -ForegroundColor Green
    exit 0
}
Write-Host "Ошибок: $fail" -ForegroundColor Red
exit 1
