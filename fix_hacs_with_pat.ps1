# Fix HACS Compliance and Push to GitHub - PowerShell Version with PAT Support
# For Sol-Ark Cloud Integration

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "=======================================" -ForegroundColor Blue
Write-Host "  HACS Compliance Fix & Push" -ForegroundColor Blue
Write-Host "  (with PAT authentication)" -ForegroundColor Blue
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""

# Repository configuration
$GitHubUser = "HammondAutomationHub"
$RepoName = "HomeAssistant_SolArk"

# Check if we're in the right directory
if (-not (Test-Path "hacs.json")) {
    Write-Host "Error: Not in project directory" -ForegroundColor Red
    Write-Host "Please run from: solark_cloud_integration folder" -ForegroundColor Yellow
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Fixed HACS compliance issues:" -ForegroundColor Green
Write-Host "   - Simplified hacs.json" -ForegroundColor White
Write-Host "   - Added info.md" -ForegroundColor White
Write-Host "   - Created .github structure" -ForegroundColor White
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
            
            # Add to .gitignore if not already there
            if (Test-Path ".gitignore") {
                $gitignoreContent = Get-Content ".gitignore" -Raw
                if ($gitignoreContent -notmatch "\.github_pat") {
                    Add-Content ".gitignore" "`n# GitHub Personal Access Token`n.github_pat"
                    Write-Host "Added .github_pat to .gitignore" -ForegroundColor Green
                }
            }
        }
    } else {
        Write-Host ""
        Write-Host "No PAT provided. You'll need to enter credentials when pushing." -ForegroundColor Yellow
        Write-Host "Username: Your GitHub username" -ForegroundColor White
        Write-Host "Password: Your Personal Access Token" -ForegroundColor White
        Write-Host ""
        $GitHubPat = $null
    }
}

# Add files
Write-Host ""
Write-Host "Adding files to git..." -ForegroundColor Green
git add hacs.json info.md .github/ HACS_COMPLIANCE.md

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error adding files to git" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

# Commit
Write-Host "Creating commit..." -ForegroundColor Green
$commitMessage = @"
Fix HACS compliance

- Simplified hacs.json to required fields only (removed invalid fields)
- Added info.md for HACS integration display
- Created .github directory structure
- Added HACS_COMPLIANCE.md documentation

Repository now fully HACS compliant and can be added as custom repository.
"@

git commit -m $commitMessage

if ($LASTEXITCODE -ne 0) {
    Write-Host "Error creating commit" -ForegroundColor Red
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host ""
Write-Host "Changes committed successfully!" -ForegroundColor Green
Write-Host ""

# Push to GitHub
if ($GitHubPat) {
    Write-Host "Pushing to GitHub with PAT authentication..." -ForegroundColor Green
    
    # Configure git credential helper to use the PAT
    $repoUrl = "https://${GitHubPat}@github.com/${GitHubUser}/${RepoName}.git"
    
    # Get current remote
    $currentRemote = git remote get-url origin 2>$null
    
    if ($currentRemote) {
        # Update remote with PAT
        git remote set-url origin $repoUrl
    } else {
        # Add remote with PAT
        git remote add origin $repoUrl
    }
    
    # Push
    git push
    $pushResult = $LASTEXITCODE
    
    # Restore remote URL without PAT for security
    $cleanUrl = "https://github.com/${GitHubUser}/${RepoName}.git"
    git remote set-url origin $cleanUrl
    
    if ($pushResult -eq 0) {
        Write-Host ""
        Write-Host "Successfully pushed to GitHub!" -ForegroundColor Green
        Write-Host ""
        Write-Host "Next: Add to HACS" -ForegroundColor Yellow
        Write-Host "1. Open HACS -> Integrations"
        Write-Host "2. Three dots -> Custom repositories"
        Write-Host "3. Add: https://github.com/$GitHubUser/$RepoName"
        Write-Host "4. Category: Integration"
        Write-Host "5. Should now work! " -NoNewline
        Write-Host "✨" -ForegroundColor Green
    } else {
        Write-Host ""
        Write-Host "Error pushing to GitHub" -ForegroundColor Red
        Write-Host "Check that your PAT has 'repo' scope" -ForegroundColor Yellow
        Write-Host "Create token at: https://github.com/settings/tokens" -ForegroundColor Cyan
    }
} else {
    Write-Host "Run this command to push:" -ForegroundColor Yellow
    Write-Host "git push" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "When prompted:" -ForegroundColor Yellow
    Write-Host "Username: Your GitHub username"
    Write-Host "Password: Your Personal Access Token"
    Write-Host ""
    Write-Host "Then in Home Assistant:" -ForegroundColor Yellow
    Write-Host "1. Open HACS -> Integrations"
    Write-Host "2. Three dots -> Custom repositories"
    Write-Host "3. Add: https://github.com/$GitHubUser/$RepoName"
    Write-Host "4. Category: Integration"
    Write-Host "5. Should now work! " -NoNewline
    Write-Host "✨" -ForegroundColor Green
}

Write-Host ""
Read-Host "Press Enter to exit"
