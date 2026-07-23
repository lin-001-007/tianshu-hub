# Tianshu HUD - one-click launcher (normal browser window, resizable panels)
param(
    [switch]$Kiosk
)

$ErrorActionPreference = "Stop"
$Root = $PSScriptRoot
if (-not $Root) { $Root = Split-Path -Parent $MyInvocation.MyCommand.Path }
if (-not $Root) { $Root = (Get-Location).Path }
$ServerDir = Join-Path $Root "server"
$WebDir = Join-Path $Root "web"
$HudUrl = if ($Kiosk) { "http://127.0.0.1:5199/?desktop=1" } else { "http://127.0.0.1:5199" }

function Test-Port($url) {
    try { (Invoke-WebRequest -Uri $url -UseBasicParsing -TimeoutSec 2).StatusCode -eq 200 } catch { $false }
}

function Stop-ListenPort($port) {
    Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
        ForEach-Object { Stop-Process -Id $_.OwningProcess -Force -ErrorAction SilentlyContinue }
}

function Test-ApiReady {
    if (-not (Test-Port "http://127.0.0.1:8799/health")) { return $false }
    try {
        $r = Invoke-WebRequest -Uri "http://127.0.0.1:8799/api/metrics" -UseBasicParsing -TimeoutSec 6
        return $r.StatusCode -eq 200
    } catch { return $false }
}

function Start-ApiServer {
    Write-Host "Starting metrics server :8799 ..." -ForegroundColor Yellow
    $script:apiJob = Start-Job -ScriptBlock {
        param($dir, $apiKey)
        Set-Location $dir
        if ($apiKey) { $env:DASHSCOPE_API_KEY = $apiKey }
        python -m uvicorn main:app --host 127.0.0.1 --port 8799
    } -ArgumentList $ServerDir, $env:DASHSCOPE_API_KEY
    $deadline = (Get-Date).AddSeconds(30)
    while ((Get-Date) -lt $deadline) {
        if (Test-ApiReady) { return $true }
        Start-Sleep -Seconds 1
    }
    return $false
}

# 加载 AI 密钥（server\.env）
# 注意：变量名不可用 $envFile，PowerShell 会误解析为 $env:File
$serverDotEnv = Join-Path $ServerDir ".env"
if ($serverDotEnv -and (Test-Path -LiteralPath $serverDotEnv)) {
    Get-Content -LiteralPath $serverDotEnv | ForEach-Object {
        if ($_ -match '^\s*DASHSCOPE_API_KEY\s*=\s*(.+)\s*$') {
            $env:DASHSCOPE_API_KEY = $matches[1].Trim()
        }
    }
}

$py = "python"
Write-Host "=== Tianshu HUD ===" -ForegroundColor Cyan
& $py -c "import fastapi, psutil, uvicorn, httpx" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host "Installing Python deps..." -ForegroundColor Yellow
    & $py -m pip install -r (Join-Path $ServerDir "requirements.txt") -q
}

if (-not (Test-ApiReady)) {
    Write-Host "API not ready, restarting :8799 ..." -ForegroundColor Yellow
    Stop-ListenPort 8799
    Start-Sleep -Seconds 1
    if (-not (Start-ApiServer)) {
        Write-Host "ERROR: API failed to start on :8799" -ForegroundColor Red
        exit 1
    }
} else {
    # 强制重启 API 以加载最新 metrics（含 GPU 检测）
    try {
        $probe = Invoke-RestMethod -Uri "http://127.0.0.1:8799/api/metrics" -TimeoutSec 8
        if (-not $probe.data.gpu) {
            Write-Host "API missing GPU metrics, restarting :8799 ..." -ForegroundColor Yellow
            Stop-ListenPort 8799
            Start-Sleep -Seconds 1
            if (-not (Start-ApiServer)) { exit 1 }
        }
    } catch {
        Stop-ListenPort 8799
        Start-Sleep -Seconds 1
        if (-not (Start-ApiServer)) { exit 1 }
    }
}

if (-not (Test-Path (Join-Path $WebDir "node_modules"))) {
    Write-Host "Installing frontend deps..." -ForegroundColor Yellow
    Push-Location $WebDir
    $env:NO_PROXY = "*"
    npm install --registry https://registry.npmmirror.com 2>&1 | Out-Null
    Pop-Location
}

if (-not (Test-Port "http://127.0.0.1:5199")) {
    Write-Host "Starting HUD frontend :5199 ..." -ForegroundColor Yellow
    $webJob = Start-Job -ScriptBlock {
        param($dir)
        Set-Location $dir
        $env:NO_PROXY = "*"
        npm run dev 2>&1
    } -ArgumentList $WebDir
    $deadline = (Get-Date).AddSeconds(45)
    while ((Get-Date) -lt $deadline) {
        if (Test-Port "http://127.0.0.1:5199") { break }
        Start-Sleep -Seconds 1
    }
}

$edge = "${env:ProgramFiles(x86)}\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path $edge)) { $edge = "$env:ProgramFiles\Microsoft\Edge\Application\msedge.exe" }
if (-not (Test-Path $edge)) {
    Write-Host "Open manually: $HudUrl" -ForegroundColor Yellow
    Start-Process $HudUrl
} elseif ($Kiosk) {
    Write-Host "Opening kiosk fullscreen HUD..." -ForegroundColor Green
    Start-Process $edge -ArgumentList @(
        "--kiosk", $HudUrl,
        "--edge-kiosk-type=fullscreen",
        "--disable-extensions", "--no-first-run", "--disable-infobars"
    )
} else {
    Write-Host "Opening resizable browser window..." -ForegroundColor Green
    Start-Process $edge -ArgumentList @("--new-window", $HudUrl)
}

Write-Host "OK: HUD running. API :8799 | Web :5199" -ForegroundColor Green
if ($Kiosk) {
    Write-Host "Kiosk mode: Press Esc to exit. Ctrl+C here to stop services." -ForegroundColor DarkGray
} else {
    Write-Host "Drag panel dividers to resize. Use -Kiosk for fullscreen mode." -ForegroundColor DarkGray
}

try {
    if ($apiJob) { Wait-Job $apiJob }
    elseif ($webJob) { Wait-Job $webJob }
} catch {}
