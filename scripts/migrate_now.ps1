#Requires -Version 5.1
<#
.SYNOPSIS
    One-command migration of lahore_pulse.db to Layerbase.
.DESCRIPTION
    1. Fetches connection string from authenticated lbase CLI
    2. Saves to .layerbase_conn.txt (gitignored)
    3. Runs chunked migration (1.36M rows in 2000-row batches)
    4. Verifies row counts for all 11 tables
.USAGE
    Run from the project root in an AUTHENTICATED PowerShell:
    .\scripts\migrate_now.ps1
#>
$ErrorActionPreference = "Stop"
$projectRoot = Split-Path $PSScriptRoot -Parent

Write-Host "`n╔══════════════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "║  Lahore Pulse → Layerbase Migration                ║" -ForegroundColor Cyan
Write-Host "╚══════════════════════════════════════════════════════╝`n" -ForegroundColor Cyan

# Step 1: Verify authentication
Write-Host "[1/3] Checking Layerbase auth..." -ForegroundColor Yellow
$lbaseWhoami = lbase whoami 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "  NOT authenticated. Run 'lbase login' first.`n" -ForegroundColor Red
    exit 1
}
Write-Host "  ✓ $lbaseWhoami`n" -ForegroundColor Green

# Step 2: Get connection string
Write-Host "[2/3] Fetching connection string for 'lahore-pulse'..." -ForegroundColor Yellow
$connFile = Join-Path $projectRoot ".layerbase_conn.txt"
$connStr = lbase cloud connection-string lahore-pulse --show-secrets 2>&1
if ($LASTEXITCODE -ne 0 -or $connStr -notmatch "postgres") {
    Write-Host "  Failed to get connection string: $connStr`n" -ForegroundColor Red
    exit 1
}
# Save without displaying the secret
$connStr.Trim() | Out-File -FilePath $connFile -Encoding utf8 -NoNewline
# Verify file was created and is non-empty
if (-not (Test-Path $connFile) -or (Get-Item $connFile).Length -eq 0) {
    Write-Host "  Failed to save .layerbase_conn.txt`n" -ForegroundColor Red
    exit 1
}
$masked = $connStr.Trim() -replace '://([^:]+):[^@]+@', '://`$1:***@'
Write-Host "  ✓ Connection string saved (masked: $masked)`n" -ForegroundColor Green

# Step 3: Run migration
Write-Host "[3/3] Running chunked migration (this may take 10-30 minutes)...`n" -ForegroundColor Yellow
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$script = Join-Path $PSScriptRoot "chunked_migrate_to_layerbase.py"

if (-not (Test-Path $python)) {
    Write-Host "  Python venv not found at $python" -ForegroundColor Red
    Write-Host "  Falling back to system python..."
    $python = "python"
}

& $python $script
if ($LASTEXITCODE -ne 0) {
    Write-Host "`n  Migration FAILED. Check output above.`n" -ForegroundColor Red
    exit 1
}

Write-Host "`n══════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "  MIGRATION COMPLETE!" -ForegroundColor Green
Write-Host "  Next: Update Railway LAYERBASE_DB_URL env var" -ForegroundColor Yellow
Write-Host "══════════════════════════════════════════════════════`n" -ForegroundColor Green
