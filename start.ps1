param(
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"

$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendPort = 8000
$FrontendPort = 5173
$BackendUrl = "http://127.0.0.1:$BackendPort/api/health"
$FrontendUrl = "http://127.0.0.1:$FrontendPort"
$Python = Join-Path $Root ".venv\Scripts\python.exe"
$NpmCmd = "npm.cmd"

function Write-Step {
    param([string]$Message)
    Write-Host ""
    Write-Host "==> $Message" -ForegroundColor Green
}

function Test-Http {
    param([string]$Url)
    try {
        Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 2 | Out-Null
        return $true
    }
    catch {
        return $false
    }
}

function Wait-Http {
    param(
        [string]$Url,
        [string]$Name,
        [int]$TimeoutSeconds = 45
    )

    $Deadline = (Get-Date).AddSeconds($TimeoutSeconds)
    while ((Get-Date) -lt $Deadline) {
        if (Test-Http $Url) {
            Write-Host "$Name is ready: $Url" -ForegroundColor Cyan
            return
        }
        Start-Sleep -Milliseconds 750
    }

    throw "$Name did not become ready at $Url within $TimeoutSeconds seconds."
}

Set-Location $Root

Write-Step "Checking Python environment"
if (-not (Test-Path $Python)) {
    Write-Host "Creating virtual environment..."
    python -m venv .venv
}

Write-Step "Installing backend dependencies"
& $Python -m pip install -r (Join-Path $Root "backend\requirements.txt")

Write-Step "Installing frontend dependencies"
if (-not (Test-Path (Join-Path $Root "frontend\node_modules"))) {
    Push-Location (Join-Path $Root "frontend")
    & $NpmCmd install
    Pop-Location
}
else {
    Write-Host "frontend\node_modules already exists; skipping npm install."
}

Write-Step "Starting backend"
if (Test-Http $BackendUrl) {
    Write-Host "Backend is already running on port $BackendPort."
}
else {
    Start-Process -FilePath $Python `
        -ArgumentList "-m", "uvicorn", "backend.main:app", "--host", "127.0.0.1", "--port", "$BackendPort" `
        -WorkingDirectory $Root `
        -WindowStyle Hidden
}
Wait-Http -Url $BackendUrl -Name "Backend"

Write-Step "Starting frontend"
if (Test-Http $FrontendUrl) {
    Write-Host "Frontend is already running on port $FrontendPort."
}
else {
    Start-Process -FilePath $NpmCmd `
        -ArgumentList "run", "dev", "--", "--port", "$FrontendPort" `
        -WorkingDirectory (Join-Path $Root "frontend") `
        -WindowStyle Hidden
}
Wait-Http -Url $FrontendUrl -Name "Frontend"

if (-not $NoBrowser) {
    Write-Step "Opening app"
    Start-Process $FrontendUrl
}

Write-Host ""
Write-Host "Chess Review Engine is running." -ForegroundColor Green
Write-Host "App:     $FrontendUrl"
Write-Host "Backend: http://127.0.0.1:$BackendPort"
Write-Host ""
Write-Host "You can close this window. The app servers were started in the background."
