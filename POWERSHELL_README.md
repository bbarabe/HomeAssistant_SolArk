# ✅ PowerShell Scripts Ready for Windows 10!

## 🎯 What You Have

I've created **PowerShell versions** of all deployment scripts for Windows 10:

### PowerShell Scripts

1. **deploy_hammond.ps1** - Initial deployment to GitHub
2. **fix_hacs.ps1** - Fix HACS compliance and push updates
3. **WINDOWS_GUIDE.md** - Complete guide for running on Windows 10

### Also Included (for reference)

- `deploy_hammond.bat` - Batch file version
- `fix_hacs.bat` - Batch file version
- Original bash scripts (`.sh`) - For Linux/Mac

---

## 🚀 Quick Start on Windows 10

### First Time Setup

1. **Install Git for Windows** (if not installed)
   - Download: https://git-scm.com/download/win
   - Install with default options

2. **Open PowerShell**
   - Press `Win + X` → "Windows PowerShell"

3. **Navigate to project folder**
   ```powershell
   cd C:\path\to\solark_cloud_integration
   ```

4. **Allow scripts to run** (one time only)
   ```powershell
   Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
   ```

5. **Run deployment**
   ```powershell
   .\deploy_hammond.ps1
   ```

6. **Push to GitHub**
   ```powershell
   git push -u origin main
   ```

### Fix HACS Compliance

```powershell
cd C:\path\to\solark_cloud_integration
.\fix_hacs.ps1
git push
```

---

## 📁 Files You Need

To fix HACS compliance, these files need to be in GitHub:

1. ✅ `hacs.json` (root) - Fixed format
2. ✅ `info.md` (root) - NEW file
3. ✅ `.github/workflows/.gitkeep` (new directory)
4. ✅ `HACS_COMPLIANCE.md` - Documentation

The PowerShell script will commit and push all of these automatically!

---

## 🔑 Authentication

You'll need a **Personal Access Token**:

1. Go to: https://github.com/settings/tokens
2. Click "Generate new token (classic)"
3. Name: "Home Assistant Integration"
4. Scope: Check ☑ **repo**
5. Click "Generate token"
6. **Copy it immediately!**

When `git push` asks:
- Username: Your GitHub username
- Password: **Paste your token** (not your GitHub password)

---

## 📋 Complete Workflow

### Initial Deployment
```powershell
# 1. Navigate to project
cd C:\path\to\solark_cloud_integration

# 2. Run deployment script
.\deploy_hammond.ps1

# 3. Push to GitHub (use token as password)
git push -u origin main
```

### Fix HACS (if repository is already on GitHub)
```powershell
# 1. Navigate to project
cd C:\path\to\solark_cloud_integration

# 2. Run HACS fix script
.\fix_hacs.ps1

# 3. Push changes
git push
```

---

## ✨ What the Scripts Do

### deploy_hammond.ps1
- ✅ Initializes git repository
- ✅ Creates .gitignore
- ✅ Adds all files
- ✅ Creates initial commit with detailed message
- ✅ Adds remote: HammondAutomationHub/HomeAssistant_SolArk
- ✅ Shows next steps

### fix_hacs.ps1
- ✅ Adds HACS compliance files (hacs.json, info.md, .github/)
- ✅ Commits changes with proper message
- ✅ Shows instructions for pushing
- ✅ Shows HACS installation steps

---

## 🎨 Color-Coded Output

The PowerShell scripts include helpful color-coded messages:
- 🔵 **Blue** - Section headers
- 🟢 **Green** - Success messages and what's being done
- 🟡 **Yellow** - Important instructions and next steps
- 🔴 **Red** - Errors (if any)
- 🔷 **Cyan** - Commands to run

---

## 📚 Documentation

**For detailed help**: Read [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md)

It covers:
- Enabling PowerShell script execution
- Installing Git for Windows
- Step-by-step instructions
- Troubleshooting common issues
- Alternative manual commands
- Quick reference guide

---

## 🆘 Common Issues

### Script won't run?
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```

### Git not found?
Install from: https://git-scm.com/download/win

### Authentication failed?
Use Personal Access Token, not password

### Already have repository?
Just run `fix_hacs.ps1` to push the fixes

---

## 🎯 Your Repository Info

All scripts are pre-configured for:

- **Organization**: HammondAutomationHub
- **Repository**: HomeAssistant_SolArk
- **URL**: https://github.com/HammondAutomationHub/HomeAssistant_SolArk

No need to edit anything - just run!

---

## ✅ After Pushing

Once you push the HACS fixes, try adding to HACS:

1. Open **HACS** in Home Assistant
2. Go to **Integrations**
3. Click **⋮** (three dots) → **Custom repositories**
4. Add: `https://github.com/HammondAutomationHub/HomeAssistant_SolArk`
5. Category: **Integration**
6. Click **Add**

Should work now! ✨

---

## 📍 File Locations

All files ready in:
```
/mnt/user-data/outputs/solark_cloud_integration/
```

PowerShell scripts:
- ✅ `deploy_hammond.ps1`
- ✅ `fix_hacs.ps1`
- ✅ `WINDOWS_GUIDE.md`

---

## 🎊 Ready to Deploy!

Everything is configured for Windows 10 PowerShell. Just:

1. Extract/download the files
2. Open PowerShell
3. Navigate to folder
4. Run `.\deploy_hammond.ps1` or `.\fix_hacs.ps1`
5. Run `git push`

**That's it!** 🚀

See [WINDOWS_GUIDE.md](WINDOWS_GUIDE.md) for complete instructions!
