@echo off
REM GitHub Deployment Script for Sol-Ark Cloud Integration - Windows Version
REM Pre-configured for HammondAutomationHub/HomeAssistant_SolArk

echo =======================================
echo   Sol-Ark Cloud - GitHub Deployer
echo   Repository: HammondAutomationHub/HomeAssistant_SolArk
echo =======================================
echo.

set GITHUB_USER=HammondAutomationHub
set REPO_NAME=HomeAssistant_SolArk
set REPO_URL=https://github.com/%GITHUB_USER%/%REPO_NAME%.git

echo Configuration:
echo   GitHub User: %GITHUB_USER%
echo   Repository: %REPO_NAME%
echo   URL: %REPO_URL%
echo.

REM Initialize git if not already done
if not exist ".git" (
    echo Initializing git repository...
    git init
    git branch -M main
) else (
    echo Git repository already initialized.
)

REM Add all files
echo.
echo Adding files to git...
git add .

REM Commit
echo Creating initial commit...
git commit -m "Initial commit: Sol-Ark Cloud Integration v1.0.0" -m "Complete Home Assistant custom integration for Sol-Ark Cloud monitoring." -m "" -m "Features:" -m "- Full UI configuration flow with no YAML required" -m "- Options flow for easy settings updates" -m "- Multi-mode authentication (Auto/Strict/Legacy)" -m "- 8 comprehensive sensors (PV, Load, Grid, Battery, Energy)" -m "- Production-ready code with comprehensive error handling" -m "- Complete documentation suite" -m "- HACS compatible" -m "" -m "See README.md for complete documentation."

REM Add remote
echo.
echo Adding GitHub remote...
git remote remove origin 2>nul
git remote add origin %REPO_URL%

echo.
echo =======================================
echo IMPORTANT: Next Steps
echo =======================================
echo.
echo 1. Create the repository on GitHub (if not already created):
echo    - Go to: https://github.com/new
echo    - Repository name: %REPO_NAME%
echo    - Description: Home Assistant integration for Sol-Ark Cloud solar monitoring
echo    - Public (recommended for HACS)
echo    - Do NOT initialize with README
echo    - Click 'Create repository'
echo.
echo 2. Push to GitHub:
echo    Run this command:
echo.
echo    git push -u origin main
echo.
echo 3. Get a Personal Access Token (if you don't have one):
echo    - Go to: https://github.com/settings/tokens
echo    - Click 'Generate new token (classic)'
echo    - Name: 'Home Assistant Integration'
echo    - Scopes: Check 'repo'
echo    - Click 'Generate token'
echo    - COPY THE TOKEN (you won't see it again!)
echo    - Use as password when pushing
echo.
echo =======================================
echo.
echo Git repository is ready!
echo Repository: https://github.com/%GITHUB_USER%/%REPO_NAME%
echo.
echo Next command to run:
echo git push -u origin main
echo.
pause
