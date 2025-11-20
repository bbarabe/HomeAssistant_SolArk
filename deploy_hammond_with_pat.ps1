# GitHub Deployment Script with PAT Support - PowerShell Version
# Pre-configured for HammondAutomationHub/HomeAssistant_SolArk

# Set error action preference
$ErrorActionPreference = "Stop"

# Configuration
$GitHubUser = "HammondAutomationHub"
$RepoName = "HomeAssistant_SolArk"
$RepoUrl = "https://github.com/$GitHubUser/$RepoName.git"

Write-Host "=======================================" -ForegroundColor Blue
Write-Host "  Sol-Ark Cloud - GitHub Deployer" -ForegroundColor Blue
Write-Host "  (with PAT authentication)" -ForegroundColor Blue
Write-Host "  Repository: $GitHubUser/$RepoName" -ForegroundColor Blue
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""

Write-Host "Configuration:" -ForegroundColor Green
Write-Host "  GitHub User: $GitHubUser" -ForegroundColor White
Write-Host "  Repository: $RepoName" -ForegroundColor White
Write-Host "  URL: $RepoUrl" -ForegroundColor White
Write-Host ""

# Check for Personal Access Token
$PatEnvVar = $env:GITHUB_PAT
$PatFile = ".\.github_pat"

if ($PatEnvVar) {
    Write-Host "Using GitHub PAT from environment variable" -ForegroundColor Green
    $GitHubPat = $PatEnvVar
} elseif (Test-Path $PatFile) {
    Write-Host "Using GitHub PAT from file: $PatFile" -ForegroundColor Green
    $GitHubPat = Get-Content $PatFile -Raw
    $GitHubPat = $GitHubPat.Trim()
} else {
    Write-Host "No GitHub PAT found." -ForegroundColor Yellow
    Write-Host ""
    Write-Host "You can provide your GitHub Personal Access Token in three ways:" -ForegroundColor Cyan
    Write-Host "1. Set environment variable: `$env:GITHUB_PAT = 'your_token_here'" -ForegroundColor White
    Write-Host "2. Create file .github_pat with your token" -ForegroundColor White
    Write-Host "3. Enter it now (will not be saved)" -ForegroundColor White
    Write-Host ""
    Write-Host "Get token at: https://github.com/settings/tokens" -ForegroundColor Cyan
    Write-Host "Required scope: 'repo' (full control)" -ForegroundColor Yellow
    Write-Host ""
    
    $choice = Read-Host "Enter PAT now? (y/n)"
    
    if ($choice -eq "y" -or $choice -eq "Y") {
        $SecurePat = Read-Host "Enter your GitHub Personal Access Token" -AsSecureString
        $BSTR = [System.Runtime.InteropServices.Marshal]::SecureStringToBSTR($SecurePat)
        $GitHubPat = [System.Runtime.InteropServices.Marshal]::PtrToStringAuto($BSTR)
        [System.Runtime.InteropServices.Marshal]::ZeroFreeBSTR($BSTR)
        
        $save = Read-Host "Save token to .github_pat file for future use? (y/n)"
        if ($save -eq "y" -or $save -eq "Y") {
            $GitHubPat | Out-File -FilePath $PatFile -NoNewline -Encoding ASCII
            Write-Host "Token saved to $PatFile" -ForegroundColor Green
            Write-Host "WARNING: Keep this file secure and add to .gitignore!" -ForegroundColor Yellow
        }
    } else {
        Write-Host ""
        Write-Host "No PAT provided. You'll need to enter credentials when pushing." -ForegroundColor Yellow
        $GitHubPat = $null
    }
}

# Initialize git if not already done
if (-not (Test-Path ".git")) {
    Write-Host ""
    Write-Host "Initializing git repository..." -ForegroundColor Green
    git init
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Error initializing git" -ForegroundColor Red
        Read-Host "Press Enter to exit"
        exit 1
    }
    git branch -M main
} else {
    Write-Host ""
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

# GitHub Personal Access Token
.github_pat
"@
    Set-Content -Path ".gitignore" -Value $gitignoreContent
}

# Add .github_pat to .gitignore if not already there
if (Test-Path ".gitignore") {
    $gitignoreContent = Get-Content ".gitignore" -Raw
    if ($gitignoreContent -notmatch "\.github_pat") {
        Add-Content ".gitignore" "`n# GitHub Personal Access Token`n.github_pat"
        Write-Host "Added .github_pat to .gitignore" -ForegroundColor Green
    }
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

# Add/update remote
Write-Host ""
Write-Host "Configuring GitHub remote..." -ForegroundColor Green

if ($GitHubPat) {
    # Use PAT in URL for authentication
    $repoUrlWithPat = "https://${GitHubPat}@github.com/${GitHubUser}/${RepoName}.git"
    
    $currentRemote = git remote get-url origin 2>$null
    if ($currentRemote) {
        git remote set-url origin $repoUrlWithPat
    } else {
        git remote add origin $repoUrlWithPat
    }
} else {
    # Use standard URL without PAT
    $currentRemote = git remote get-url origin 2>$null
    if ($currentRemote) {
        git remote set-url origin $RepoUrl
    } else {
        git remote add origin $RepoUrl
    }
}

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error adding remote" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "=======================================" -ForegroundColor Blue
Write-Host "Ready to Push!" -ForegroundColor Yellow
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""

# Push to GitHub
if ($GitHubPat) {
    Write-Host "Pushing to GitHub with PAT authentication..." -ForegroundColor Green
    Write-Host ""
    
    git push -u origin main
    $pushResult = $LASTEXITCODE
    
    # Restore remote URL without PAT for security
    git remote set-url origin $RepoUrl
    
    if ($pushResult -eq 0) {
        Write-Host ""
        Write-Host "=======================================" -ForegroundColor Green
        Write-Host "Successfully deployed to GitHub!" -ForegroundColor Green
        Write-Host "=======================================" -ForegroundColor Green
        Write-Host ""
        Write-Host "Your repository: https://github.com/$GitHubUser/$RepoName" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Next Steps:" -ForegroundColor Yellow
        Write-Host ""
        Write-Host "1. View your repository:" -ForegroundColor White
        Write-Host "   https://github.com/$GitHubUser/$RepoName" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "2. For HACS installation (users):" -ForegroundColor White
        Write-Host "   - HACS -> Integrations -> Three dots"
        Write-Host "   - Custom repositories"
        Write-Host "   - Add: https://github.com/$GitHubUser/$RepoName"
        Write-Host "   - Category: Integration"
        Write-Host ""
        Write-Host "3. Optional: Create a release" -ForegroundColor White
        Write-Host "   - Go to: https://github.com/$GitHubUser/$RepoName/releases/new"
        Write-Host "   - Tag: v1.0.0"
        Write-Host "   - Title: Sol-Ark Cloud Integration v1.0.0"
        Write-Host ""
    } else {
        Write-Host ""
        Write-Host "Error pushing to GitHub" -ForegroundColor Red
        Write-Host ""
        Write-Host "Possible issues:" -ForegroundColor Yellow
        Write-Host "- PAT doesn't have 'repo' scope" -ForegroundColor White
        Write-Host "- Repository doesn't exist yet (create at https://github.com/new)" -ForegroundColor White
        Write-Host "- PAT has expired" -ForegroundColor White
        Write-Host ""
        Write-Host "Create/check token at: https://github.com/settings/tokens" -ForegroundColor Cyan
    }
} else {
    Write-Host "PAT not provided. Run this command to push:" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "   git push -u origin main" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "When prompted:" -ForegroundColor Yellow
    Write-Host "   Username: Your GitHub username"
    Write-Host "   Password: Your Personal Access Token"
    Write-Host ""
    Write-Host "Get token at: https://github.com/settings/tokens" -ForegroundColor Cyan
    Write-Host "Required scope: 'repo'" -ForegroundColor Yellow
    Write-Host ""
}

Write-Host ""
Read-Host "Press Enter to exit"
