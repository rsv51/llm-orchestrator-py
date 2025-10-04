@echo off
echo =====================================
echo Database Migration Runner
echo =====================================
echo.

cd /d "%~dp0.."

if not exist "llm_orchestrator.db" (
    echo Error: Database file not found!
    echo Expected location: llm_orchestrator.db
    pause
    exit /b 1
)

echo Running migration...
python migrations\run_migration.py llm_orchestrator.db

if %ERRORLEVEL% EQU 0 (
    echo.
    echo =====================================
    echo Migration completed successfully!
    echo =====================================
) else (
    echo.
    echo =====================================
    echo Migration failed! Check errors above.
    echo =====================================
)

echo.
pause