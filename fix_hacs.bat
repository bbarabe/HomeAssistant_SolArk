@echo off
REM Fix HACS Compliance and Push to GitHub - Windows Version

echo =======================================
echo   HACS Compliance Fix and Push
echo =======================================
echo.

REM Check if we're in the right directory
if not exist "hacs.json" (
    echo Error: Not in project directory
    echo Please run from the solark_cloud_integration folder
    pause
    exit /b 1
)

echo Fixed HACS compliance issues:
echo    - Simplified hacs.json
echo    - Added info.md
echo    - Created .github structure
echo.

REM Add files
echo Adding files to git...
git add hacs.json info.md .github/ HACS_COMPLIANCE.md

REM Commit
echo Creating commit...
git commit -m "Fix HACS compliance - simplified hacs.json and added info.md"

echo.
echo Changes committed successfully!
echo.
echo Next step: Push to GitHub
echo Run: git push
echo.
echo Then in Home Assistant:
echo 1. Open HACS - Integrations
echo 2. Three dots - Custom repositories
echo 3. Add: https://github.com/HammondAutomationHub/HomeAssistant_SolArk
echo 4. Category: Integration
echo 5. Should now work!
echo.
pause
