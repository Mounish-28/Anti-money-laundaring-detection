<#
.SYNOPSIS
    scripts/cleanup.ps1: PowerShell wrapper for QuantumAML Nexus Safe Cleanup Utility
.EXAMPLE
    .\scripts\cleanup.ps1              # Dry-run inspection
    .\scripts\cleanup.ps1 --purge      # Interactive confirmation purge
    .\scripts\cleanup.ps1 --purge -y   # Automated force purge
    .\scripts\cleanup.ps1 --audit-only # Run 5-pipeline integrity audit
#>

[CmdletBinding()]
param (
    [switch]$Purge,
    [switch]$Yes,
    [switch]$AuditOnly
)

$RootDir = Split-Path -Parent $PSScriptRoot
$PythonExe = Join-Path $RootDir ".venv\Scripts\python.exe"

if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

$Arguments = @("$PSScriptRoot\safe_project_cleanup.py")
if ($Purge) { $Arguments += "--purge" }
if ($Yes) { $Arguments += "--yes" }
if ($AuditOnly) { $Arguments += "--audit-only" }

& $PythonExe @Arguments
