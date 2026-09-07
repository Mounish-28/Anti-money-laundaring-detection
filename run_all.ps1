# ==============================================================================
# QuantumAML Nexus - Unified Multi-Process Orchestration Runner (PowerShell)
# ==============================================================================
# Launches and coordinates all 4 platform subsystems with health-gated staging:
#   1. Backend:        FastAPI + Uvicorn (app.main:app --port 8000 --reload)
#   2. Banking Stream: Procedural Indian Switch (streamer.py --interval 1.5)
#   3. Crypto Stream:  Bitcoin Mempool Ingestion (live_crypto_feed.py --rate-limit 1.0)
#   4. Frontend:       Vite React UI (npm run dev in nexus-frontend/)
#
# Features:
#   - Staged health-gated boot sequence (polls /docs with 0.5s cadence, 20s timeout)
#   - Fail-safe process tree termination (taskkill /F /T) to prevent port leaks
#   - CLI custom flags: -NoCrypto, -NoFrontend, -BackendPort, -StreamerInterval
#
# Usage:
#   .\run_all.ps1
#   .\run_all.ps1 -BackendPort 8000 -StreamerInterval 1.5
#   .\run_all.ps1 -NoCrypto -NoFrontend
#   .\run_all.ps1 --no-crypto --backend-port 8080
# ==============================================================================

[CmdletBinding()]
param (
    [Alias("Port")]
    [int]$BackendPort = 8000,

    [Alias("Interval")]
    [double]$StreamerInterval = 1.5,

    [Alias("CryptoRate")]
    [double]$CryptoRateLimit = 1.0,

    [switch]$NoCrypto,
    [switch]$NoFrontend
)

# Enforce strict error-handling
$ErrorActionPreference = "Stop"
$repoRoot = $PSScriptRoot

# ------------------------------------------------------------------------------
# 0. CLI Argument Fallback Normalization (supports --flag style)
# ------------------------------------------------------------------------------
if ($args -contains "--no-crypto") { $NoCrypto = $true }
if ($args -contains "--no-frontend") { $NoFrontend = $true }
for ($i = 0; $i -lt $args.Count; $i++) {
    if ($args[$i] -in @("--backend-port", "-backend-port", "--port") -and ($i + 1) -lt $args.Count) {
        $BackendPort = [int]$args[$i + 1]
    }
    if ($args[$i] -in @("--streamer-interval", "-streamer-interval", "--interval") -and ($i + 1) -lt $args.Count) {
        $StreamerInterval = [double]$args[$i + 1]
    }
    if ($args[$i] -in @("--crypto-rate-limit", "-crypto-rate-limit") -and ($i + 1) -lt $args.Count) {
        $CryptoRateLimit = [double]$args[$i + 1]
    }
}

# ------------------------------------------------------------------------------
# 1. Environment & Path Resolution
# ------------------------------------------------------------------------------
$venvPython = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host "[ERROR] Virtual environment Python not found at: $venvPython" -ForegroundColor Red
    Write-Host "[REMEDIATION] Please initialize the repository virtual environment:" -ForegroundColor Yellow
    Write-Host "    python -m venv .venv" -ForegroundColor Gray
    Write-Host "    .\.venv\Scripts\pip.exe install -r requirements.txt" -ForegroundColor Gray
    exit 1
}
$pythonExe = $venvPython

$frontendDir = Join-Path $repoRoot "nexus-frontend"

# Resolve npm binary on Windows
$npmCmd = "npm.cmd"
$npmLookup = Get-Command npm.cmd -ErrorAction SilentlyContinue
if ($null -ne $npmLookup) {
    $npmCmd = $npmLookup.Source
}

# ------------------------------------------------------------------------------
# 2. Port Mitigation & Process Tree Cleanup Utilities
# ------------------------------------------------------------------------------
$processList = @()

function Free-TcpPort([int]$TargetPort) {
    try {
        # Netstat regex scan for active listening PIDs
        $netstatOutput = netstat.exe -ano -p tcp 2>$null | Select-String ":$TargetPort\s+.*LISTENING\s+(\d+)"
        foreach ($match in $netstatOutput) {
            if ($match.Matches.Groups.Count -ge 2) {
                $ownerPid = $match.Matches.Groups[1].Value.Trim()
                if ($ownerPid -and $ownerPid -ne "0" -and $ownerPid -ne $PID) {
                    Write-Host "  -> Releasing port $TargetPort (force-killing orphaned PID $ownerPid)..." -ForegroundColor Yellow
                    taskkill.exe /F /T /PID $ownerPid 2>$null | Out-Null
                }
            }
        }
    } catch {
        # Non-fatal port check
    }
}

function Stop-AllProcessTrees {
    Write-Host "`n[ORCHESTRATOR] Initiating fail-safe shutdown of all QuantumAML Nexus child processes..." -ForegroundColor Yellow
    foreach ($p in $processList) {
        if ($null -ne $p) {
            try {
                $pidToKill = $p.Id
                Write-Host "  -> Terminating process tree for PID $pidToKill ($($p.ProcessName))..." -ForegroundColor Gray
                # Reliably kill process and subtree using taskkill and Stop-Process
                taskkill.exe /PID $pidToKill /T /F 2>$null | Out-Null
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            } catch {
                # Process already terminated
            }
        }
    }

    # Ensure ports are completely unlocked on Windows
    Free-TcpPort -TargetPort $BackendPort
    if (-not $NoFrontend) {
        Free-TcpPort -TargetPort 5173
    }

    Write-Host "[ORCHESTRATOR] Clean teardown complete. Ports $BackendPort and 5173 freed.`n" -ForegroundColor Green
}

# ------------------------------------------------------------------------------
# 3. Interactive Execution Banner
# ------------------------------------------------------------------------------
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "     QUANTUMAML NEXUS - MULTI-PROCESS ORCHESTRATOR (POWERSHELL)    " -ForegroundColor White
Write-Host "====================================================================" -ForegroundColor Cyan
Write-Host "  Python:       $pythonExe" -ForegroundColor Gray
Write-Host "  Backend Port: http://localhost:$BackendPort" -ForegroundColor Cyan
Write-Host "  WebSocket:    ws://localhost:$BackendPort/ws/live" -ForegroundColor Cyan
Write-Host "  Frontend:     $(if ($NoFrontend) { 'DISABLED (--no-frontend)' } else { $frontendDir })" -ForegroundColor Gray
Write-Host "  Crypto Feed:  $(if ($NoCrypto) { 'DISABLED (--no-crypto)' } else { 'ACTIVE (' + $CryptoRateLimit + '/s)' })" -ForegroundColor Gray
Write-Host "  Banking Rate: $StreamerInterval sec/tx" -ForegroundColor Gray
Write-Host "====================================================================" -ForegroundColor Cyan

# Pre-execution port sweep
Free-TcpPort -TargetPort $BackendPort
if (-not $NoFrontend) {
    Free-TcpPort -TargetPort 5173
}

try {
    # --------------------------------------------------------------------------
    # Phase 1: Start FastAPI Backend Core
    # --------------------------------------------------------------------------
    Write-Host "`n[1/4] Starting FastAPI Backend Core on port $BackendPort..." -ForegroundColor Cyan
    $backendPsi = New-Object System.Diagnostics.ProcessStartInfo
    $backendPsi.FileName = $pythonExe
    $backendPsi.Arguments = "-m uvicorn app.main:app --port $BackendPort --reload"
    $backendPsi.WorkingDirectory = $repoRoot
    $backendPsi.UseShellExecute = $false

    $backendProc = [System.Diagnostics.Process]::Start($backendPsi)
    $processList += $backendProc

    # --------------------------------------------------------------------------
    # Phase 2: Health Check Polling (0.5s interval, 20s timeout)
    # --------------------------------------------------------------------------
    $docsUrl = "http://localhost:$BackendPort/docs"
    Write-Host "  -> Health-gating: polling $docsUrl (0.5s interval, 20s timeout)..." -ForegroundColor Yellow
    $healthy = $false
    $maxAttempts = 40  # 40 * 0.5s = 20s

    for ($i = 1; $i -le $maxAttempts; $i++) {
        Start-Sleep -Milliseconds 500
        try {
            $resp = Invoke-WebRequest -Uri $docsUrl -UseBasicParsing -TimeoutSec 1 -ErrorAction Stop
            if ($resp.StatusCode -eq 200) {
                $elapsedSec = [math]::Round($i * 0.5, 1)
                Write-Host "  [PASS] Backend verified operational (HTTP 200 OK) in ${elapsedSec}s!" -ForegroundColor Green
                $healthy = $true
                break
            }
        } catch {
            # Continue polling until timeout
        }

        if ($backendProc.HasExited) {
            Write-Host "  [ERROR] Backend process terminated prematurely with exit code $($backendProc.ExitCode)!" -ForegroundColor Red
            break
        }
    }

    if (-not $healthy) {
        Write-Host "`n[FATAL] Backend did not pass health check within 20s. Aborting startup." -ForegroundColor Red
        exit 1
    }

    # --------------------------------------------------------------------------
    # Phase 3: Launch Remaining Services Concurrently
    # --------------------------------------------------------------------------
    # 3a. Banking Streamer
    Write-Host "`n[2/4] Starting Indian Banking Switch Streamer (interval: ${StreamerInterval}s)..." -ForegroundColor Green
    $bankingPsi = New-Object System.Diagnostics.ProcessStartInfo
    $bankingPsi.FileName = $pythonExe
    $bankingPsi.Arguments = "streamer.py --interval $StreamerInterval"
    $bankingPsi.WorkingDirectory = $repoRoot
    $bankingPsi.UseShellExecute = $false
    $bankingProc = [System.Diagnostics.Process]::Start($bankingPsi)
    $processList += $bankingProc

    # 3b. Live Crypto Feed
    if (-not $NoCrypto) {
        Write-Host "[3/4] Starting Live Crypto Mempool Feed (rate limit: ${CryptoRateLimit}/s)..." -ForegroundColor Yellow
        $cryptoPsi = New-Object System.Diagnostics.ProcessStartInfo
        $cryptoPsi.FileName = $pythonExe
        $cryptoPsi.Arguments = "live_crypto_feed.py --rate-limit $CryptoRateLimit"
        $cryptoPsi.WorkingDirectory = $repoRoot
        $cryptoPsi.UseShellExecute = $false
        $cryptoProc = [System.Diagnostics.Process]::Start($cryptoPsi)
        $processList += $cryptoProc
    } else {
        Write-Host "[3/4] [SKIP] Crypto Mempool Feed skipped (-NoCrypto)." -ForegroundColor DarkGray
    }

    # 3c. Vite React Frontend
    if (-not $NoFrontend) {
        if (Test-Path $frontendDir) {
            Write-Host "[4/4] Starting Vite React UI ($npmCmd run dev)..." -ForegroundColor Magenta
            $frontendPsi = New-Object System.Diagnostics.ProcessStartInfo
            $frontendPsi.FileName = "cmd.exe"
            $frontendPsi.Arguments = "/c `"$npmCmd run dev`""
            $frontendPsi.WorkingDirectory = $frontendDir
            $frontendPsi.UseShellExecute = $false
            $frontendProc = [System.Diagnostics.Process]::Start($frontendPsi)
            $processList += $frontendProc
        } else {
            Write-Host "[4/4] [WARN] Frontend directory not found at $frontendDir" -ForegroundColor Yellow
        }
    } else {
        Write-Host "[4/4] [SKIP] Vite React Frontend skipped (-NoFrontend)." -ForegroundColor DarkGray
    }

    Write-Host "`n====================================================================" -ForegroundColor Cyan
    Write-Host " [ONLINE] All requested QuantumAML Nexus services are active!" -ForegroundColor Green
    Write-Host " Press [Ctrl+C] to gracefully terminate all child processes." -ForegroundColor White
    Write-Host "====================================================================`n" -ForegroundColor Cyan

    # Main supervision loop
    while ($true) {
        Start-Sleep -Milliseconds 500
        if ($backendProc.HasExited) {
            Write-Host "`n[ERROR] FastAPI backend exited unexpectedly with code $($backendProc.ExitCode)." -ForegroundColor Red
            break
        }
    }

} finally {
    Stop-AllProcessTrees
}
