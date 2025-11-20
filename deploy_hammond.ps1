# GitHub Deployment Script for Sol-Ark Cloud Integration - PowerShell Version
# Pre-configured for HammondAutomationHub/HomeAssistant_SolArk

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$GitHubUser = "HammondAutomationHub"
$RepoName = "HomeAssistant_SolArk"
$RepoUrl = "https://github.com/$GitHubUser/$RepoName.git"

Write-Host "=======================================" -ForegroundColor Blue
Write-Host "  Sol-Ark Cloud - GitHub Deployer" -ForegroundColor Blue
Write-Host "  Repository: $GitHubUser/$RepoName" -ForegroundColor Blue
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  GitHub User: $GitHubUser" -ForegroundColor White
Write-Host "  Repository: $RepoName" -ForegroundColor White
Write-Host "  URL: $RepoUrl" -ForegroundColor White
Write-Host ""

# Initialize git if not already done
if (-not (Test-Path ".git")) {
    Write-Host "Initializing git repository..." -ForegroundColor Green
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error initializing git" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    git branch -M main
} else {
    Write-Host "Git repository already initialized." -ForegroundColor Green
}

# Create .gitignore if it doesn't exist
if (-not (Test-Path ".gitignore")) {
    Write-Host "Creating .gitignore..." -ForegroundColor Green
    $gitignoreContent = @"
# Python
__pycache__/
*.py[cod]
*`$py.class
*.so
.Python
build/
develop-eggs/
dist/
downloads/
eggs/
.eggs/
lib/
lib64/
parts/
sdist/
var/
wheels/
*.egg-info/
.installed.cfg
*.egg

# Virtual environments
venv/
ENV/
env/
.venv

# IDE
.vscode/
.idea/
*.swp
*.swo
*~
.DS_Store

# Testing
.tox/
.coverage
.pytest_cache/

# Project specific
*.zip
.secrets
"@
    Set-Content -Path ".gitignore" -Value $gitignoreContent
}

# Add all files
Write-Host ""
Write-Host "Adding files to git..." -ForegroundColor Green
git add .

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error adding files" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Commit
Write-Host "Creating initial commit..." -ForegroundColor Green
$commitMessage = @"
Initial commit: Sol-Ark Cloud Integration v1.0.0

Complete Home Assistant custom integration for Sol-Ark Cloud monitoring.

Features:
- Full UI configuration flow with no YAML required
- Options flow for easy settings updates
- Multi-mode authentication (Auto/Strict/Legacy)
- 8 comprehensive sensors (PV, Load, Grid, Battery, Energy)
- Production-ready code with comprehensive error handling
- Complete documentation suite
- HACS compatible

Sensors:
- PV Power (W)
- Load Power (W)
- Grid Import/Export Power (W)
- Battery Power (W) with charge/discharge detection
- Battery State of Charge (%)
- Energy Today (kWh)
- Last Error (diagnostics)

Documentation:
- Quick Start Guide (5 minutes)
- Detailed Installation Guide
- Complete Configuration Reference
- Usage Examples with Automations
- Energy Dashboard Integration
- Comprehensive Troubleshooting

See README.md for complete documentation.
"@

git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error creating commit" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Add remote
Write-Host ""
Write-Host "Adding GitHub remote..." -ForegroundColor Green
git remote remove origin 2>$null
git remote add origin $RepoUrl

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error adding remote" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Blue
Write-Host "IMPORTANT: Next Steps" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""
Write-Host "1. Create the repository on GitHub (if not already created):" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/new"
Write-Host "   - Repository name: $RepoName"
Write-Host "   - Description: Home Assistant integration for Sol-Ark Cloud solar monitoring"
Write-Host "   - Public (recommended for HACS)"
Write-Host "   - Do NOT initialize with README"
Write-Host "   - Click 'Create repository'"
Write-Host ""
Write-Host "2. Push to GitHub:" -ForegroundColor Yellow
Write-Host "   Run this command:"
Write-Host ""
Write-Host "   git push -u origin main" -ForegroundColor Cyan
Write-Host ""
Write-Host "3. Get a Personal Access Token (if you don't have one):" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/settings/tokens"
Write-Host "   - Click 'Generate new token (classic)'"
Write-Host "   - Name: 'Home Assistant Integration'"
Write-Host "   - Scopes: Check 'repo'"
Write-Host "   - Click 'Generate token'"
Write-Host "   - COPY THE TOKEN (you won't see it again!)"
Write-Host "   - Use as password when pushing"
Write-Host ""
Write-Host "4. Create a release (optional but recommended):" -ForegroundColor Yellow
Write-Host "   - Go to: https://github.com/$GitHubUser/$RepoName/releases/new"
Write-Host "   - Tag version: v1.0.0"
Write-Host "   - Release title: Sol-Ark Cloud Integration v1.0.0"
Write-Host "   - Run .\package.sh to create distribution zips"
Write-Host "   - Attach the generated zip files"
Write-Host "   - Click 'Publish release'"
Write-Host ""
Write-Host "5. For HACS installation:" -ForegroundColor Yellow
Write-Host "   Users can add your repository as a custom repository:"
Write-Host "   - HACS -> Integrations -> Three dots -> Custom repositories"
Write-Host "   - URL: https://github.com/$GitHubUser/$RepoName"
Write-Host "   - Category: Integration"
Write-Host ""
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""
Write-Host "Git repository is ready!" -ForegroundColor Green
Write-Host "Repository: https://github.com/$GitHubUser/$RepoName" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next command to run:" -ForegroundColor Yellow
Write-Host "git push -u origin main" -ForegroundColor Cyan
Write-Host ""

Read-Host "Press Enter to exit"
