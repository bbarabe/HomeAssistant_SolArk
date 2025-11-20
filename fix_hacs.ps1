# Fix HACS Compliance and Push to GitHub - PowerShell Version
# For Sol-Ark Cloud Integration

# Set error action preference
$ErrorActionPreference = "Stop"

Write-Host "=======================================" -ForegroundColor Blue
Write-Host "  HACS Compliance Fix & Push" -ForegroundColor Blue
Write-Host "=======================================" -ForegroundColor Blue
Write-Host ""

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

# Add files
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
Write-Host "Next step: Push to GitHub" -ForegroundColor Yellow
Write-Host "Run: " -NoNewline -ForegroundColor Yellow
Write-Host "git push" -ForegroundColor Cyan
Write-Host ""
Write-Host "Then in Home Assistant:" -ForegroundColor Yellow
Write-Host "1. Open HACS -> Integrations"
Write-Host "2. Three dots -> Custom repositories"
Write-Host "3. Add: https://github.com/HammondAutomationHub/HomeAssistant_SolArk"
Write-Host "4. Category: Integration"
Write-Host "5. Should now work! " -NoNewline
Write-Host "✨" -ForegroundColor Green
Write-Host ""

Read-Host "Press Enter to exit"
