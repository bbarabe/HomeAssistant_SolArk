# Running PowerShell Scripts on Windows 10

## Quick Start

### For HACS Compliance Fix:
```powershell
cd path\to\solark_cloud_integration
.\fix_hacs.ps1
git push
```

### For Initial Deployment:
```powershell
cd path\to\solark_cloud_integration
.\deploy_hammond.ps1
git push -u origin main
```

---

## Enabling PowerShell Script Execution

By default, Windows 10 blocks PowerShell scripts for security. You need to enable them:

### Option 1: Allow for Current Session (Temporary)

Open PowerShell and run:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
Then run your script in the same window.

### Option 2: Allow Permanently (Recommended)

Open PowerShell **as Administrator** and run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

This allows locally-created scripts to run.

### Option 3: Run Without Changing Policy

```powershell
powershell -ExecutionPolicy Bypass -File .\fix_hacs.ps1
```

---

## Prerequisites

### 1. Install Git for Windows

Download from: https://git-scm.com/download/win

During installation:
- ✅ Check "Git from the command line and also from 3rd-party software"
- ✅ Check "Use Git and optional Unix tools from the Command Prompt"

### 2. Configure Git

After installation, open PowerShell and configure:
```powershell
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

### 3. Get a GitHub Personal Access Token

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "Home Assistant Integration"
4. Scopes: Check ☑ **repo** (full control)
5. Click "Generate token"
6. **Copy the token immediately** (you won't see it again!)

---

## Step-by-Step Guide

### Initial Deployment

1. **Open PowerShell** (not Command Prompt)
   - Press `Win + X` → "Windows PowerShell"

2. **Navigate to your project folder**
   ```powershell
   cd C:\path\to\solark_cloud_integration
   ```

3. **Allow script execution** (if needed)
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

4. **Run deployment script**
   ```powershell
   .\deploy_hammond.ps1
   ```

5. **Push to GitHub**
   ```powershell
   git push -u origin main
   ```
   - Username: Your GitHub username
   - Password: Your Personal Access Token (paste it)

### Fixing HACS Compliance

1. **Open PowerShell**

2. **Navigate to project**
   ```powershell
   cd C:\path\to\solark_cloud_integration
   ```

3. **Run fix script**
   ```powershell
   .\fix_hacs.ps1
   ```

4. **Push changes**
   ```powershell
   git push
   ```

---

## Alternative: Manual Git Commands

If you prefer not to use scripts, here are the manual commands:

### Initial Deployment
```powershell
# Initialize repository
git init
git branch -M main

# Add all files
git add .

# Commit
git commit -m "Initial commit: Sol-Ark Cloud Integration v1.0.0"

# Add remote
git remote add origin https://github.com/HammondAutomationHub/HomeAssistant_SolArk.git

# Push
git push -u origin main
```

### HACS Compliance Fix
```powershell
# Add changed files
git add hacs.json info.md .github/ HACS_COMPLIANCE.md

# Commit
git commit -m "Fix HACS compliance"

# Push
git push
```

---

## Troubleshooting

### "cannot be loaded because running scripts is disabled"

**Solution**: Run PowerShell as Administrator and execute:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

### "git: command not found"

**Solution**: 
1. Install Git for Windows: https://git-scm.com/download/win
2. Restart PowerShell
3. Verify: `git --version`

### Authentication Failed

**Solution**:
- Use your Personal Access Token, NOT your GitHub password
- Token needs `repo` scope
- Create new token at: https://github.com/settings/tokens

### SSL Certificate Errors

**Solution**:
```powershell
git config --global http.sslVerify true
```

### Line Ending Warnings

**Solution** (safe to ignore, or fix with):
```powershell
git config --global core.autocrlf true
```

---

## File Locations

After you download/extract the files, you might have them at:
- `C:\Users\YourName\Downloads\solark_cloud_integration\`
- `C:\Projects\solark_cloud_integration\`
- Or wherever you extracted them

**Important**: Make sure you're in the correct directory before running scripts!

```powershell
# Check current directory
Get-Location

# List files (should see the .ps1 scripts)
Get-ChildItem
```

---

## Quick Reference

### PowerShell Scripts Included

| Script | Purpose | Run After |
|--------|---------|-----------|
| `deploy_hammond.ps1` | Initial deployment | First time only |
| `fix_hacs.ps1` | Fix HACS compliance | When HACS reports issues |

### Git Commands You'll Use

```powershell
git status              # Check what's changed
git add .               # Add all files
git commit -m "msg"     # Commit with message
git push                # Push to GitHub
git pull                # Pull from GitHub
git log --oneline       # View commit history
```

---

## Summary

**Quickest Path**:

1. Install Git for Windows
2. Open PowerShell
3. Navigate to project folder
4. Run: `.\deploy_hammond.ps1` (first time)
5. Run: `git push -u origin main`
6. For HACS fix later: `.\fix_hacs.ps1` then `git push`

**That's it!** 🎉

---

## Need Help?

- **Git Documentation**: https://git-scm.com/doc
- **PowerShell Help**: `Get-Help about_Execution_Policies`
- **GitHub Guides**: https://guides.github.com/

All scripts include helpful output messages and pause at the end so you can read the instructions!
