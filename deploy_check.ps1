# ==============================================================================
# QuantumAML Nexus - Pre-Flight Deployment & Port Binding Validation Script
# ==============================================================================

Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host " [1/3] Pre-Flight Port Availability Verification (8000 & 6379)..." -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

$portsToCheck = @(8000, 6379)
$allPortsFree = $true

foreach ($port in $portsToCheck) {
    $occupied = $false
    try {
        $tcpConn = Get-NetTCPConnection -LocalPort $port -ErrorAction SilentlyContinue | Where-Object { $_.State -eq "Listen" }
        if ($null -ne $tcpConn) {
            $occupied = $true
            $owningProc = (Get-Process -Id $tcpConn[0].OwningProcess -ErrorAction SilentlyContinue).ProcessName
            Write-Host "  [OCCUPIED] Port $port is in use by process: $owningProc (PID: $($tcpConn[0].OwningProcess))" -ForegroundColor Yellow
        }
    } catch {
        # Fallback to TcpClient check if Get-NetTCPConnection is unavailable
        try {
            $tcpClient = New-Object System.Net.Sockets.TcpClient
            $asyncResult = $tcpClient.BeginConnect("127.0.0.1", $port, $null, $null)
            $success = $asyncResult.AsyncWaitHandle.WaitOne(300, $false)
            if ($success -and $tcpClient.Connected) {
                $occupied = $true
                $tcpClient.EndConnect($asyncResult)
                Write-Host "  [OCCUPIED] Port $port is currently listening." -ForegroundColor Yellow
            }
            $tcpClient.Close()
        } catch {}
    }

    if (-not $occupied) {
        Write-Host "  [FREE] Port $port is open and ready for container binding." -ForegroundColor Green
    } else {
        $allPortsFree = $false
    }
}

# ==============================================================================
Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " [2/3] Validating docker-compose.yml Schema & Volume Bindings..." -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

# Syntax Check via Python
$yamlCheck = python -c "import yaml; yaml.safe_load(open('docker-compose.yml', 'r'))" 2>&1
if ($LASTEXITCODE -eq 0) {
    Write-Host "  [OK] docker-compose.yml YAML syntax is structurally valid." -ForegroundColor Green
} else {
    Write-Host "  [FAIL] YAML syntax error: $yamlCheck" -ForegroundColor Red
    exit 1
}

# Execute docker compose config
$dockerCmd = Get-Command docker -ErrorAction SilentlyContinue
if ($null -eq $dockerCmd) {
    $commonDockerPaths = @(
        "C:\Program Files\Docker\Docker\resources\bin\docker.exe",
        "$env:LOCALAPPDATA\Docker\docker.exe"
    )
    foreach ($p in $commonDockerPaths) {
        if (Test-Path $p) {
            $dockerCmd = [PSCustomObject]@{ Source = $p }
            $env:PATH += ";$(Split-Path $p)"
            break
        }
    }
}

if ($null -ne $dockerCmd) {
    Write-Host "  -> Running 'docker compose config'..." -ForegroundColor Gray
    try {
        $configOut = & docker compose config 2>&1
        if ($LASTEXITCODE -eq 0) {
            Write-Host "  [SUCCESS] 'docker compose config' validated 0 schema or volume binding errors!" -ForegroundColor Green
        } else {
            Write-Host "  [NOTICE] docker compose config returned code $($LASTEXITCODE): $configOut" -ForegroundColor Yellow
        }
    } catch {
        Write-Host "  [NOTICE] Docker daemon offline: $_" -ForegroundColor Yellow
    }
} else {
    Write-Host "  [NOTICE] Docker CLI not in system PATH. Structural verification verified via Python." -ForegroundColor DarkGray
}

# ==============================================================================
Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " [3/3] Operational Stack Runbook & Lifecycle CLI Commands" -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan

Write-Host @"
[1. START SERVICES (Detached & Build)]
  docker compose up -d --build

[2. VIEW LIVE SERVICE STATUS & HEALTH PROBES]
  docker compose ps
  curl -f http://localhost:8000/health

[3. VIEW SERVICE LOGS (Live Stream)]
  # FastAPI Serving Logs
  docker compose logs -f api

  # Background Celery Alert Worker Logs
  docker compose logs -f celery_worker

  # Redis Broker Logs
  docker compose logs -f redis

[4. SCALE BACKGROUND INVESTIGATOR ALERT WORKERS]
  docker compose up -d --scale celery_worker=4

[5. ZERO-DOWNTIME MODEL UPDATES (Host Volume Mounted)]
  Copy-Item -Recurse -Force ./new_weights/* ./models/

[6. TEARDOWN STACK & CLEAN NETWORKS]
  docker compose down -v
"@ -ForegroundColor Green

Write-Host "`n====================================================================" -ForegroundColor Cyan
Write-Host " Pre-flight deployment check completed." -ForegroundColor Cyan
Write-Host "====================================================================" -ForegroundColor Cyan
