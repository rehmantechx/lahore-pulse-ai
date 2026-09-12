@echo off
REM ============================================================
REM  ONE-CLICK LAYERBASE MIGRATION
REM  Run this AFTER: lbase login (completed in browser)
REM ============================================================
echo.
echo  [1/4] Authenticating with Layerbase...
lbase whoami 2>nul
if %errorlevel% neq 0 (
    echo  Not logged in. Please run: lbase login
    echo  Then re-run this script.
    pause
    exit /b 1
)
echo  Authenticated.

echo.
echo  [2/4] Getting connection string...
lbase cloud connection-string lahore-pulse --show-secrets > .layerbase_conn.txt
if %errorlevel% neq 0 (
    echo  Failed. Does the database "lahore-pulse" exist?
    echo  Create it: lbase create --engine sqlite --name lahore-pulse
    pause
    exit /b 1
)
echo  Connection string saved.

echo.
echo  [3/4] Running migration (this may take 10-30 minutes)...
.venv\Scripts\python.exe scripts\chunked_migrate_to_layerbase.py
if %errorlevel% neq 0 (
    echo  Migration failed. Check output above.
    pause
    exit /b 1
)

echo.
echo  [4/4] Updating .env with connection string...
set /p CONN=<.layerbase_conn.txt
powershell -Command "$env:CONN='%CONN%'; (Get-Content .env) -replace '# LAYERBASE_DB_URL=.*', ('LAYERBASE_DB_URL=' + $env:CONN) | Set-Content .env"
echo  .env updated.

echo.
echo ============================================================
echo  MIGRATION COMPLETE!
echo  Next: Update Railway env var LAYERBASE_DB_URL
echo ============================================================
pause
