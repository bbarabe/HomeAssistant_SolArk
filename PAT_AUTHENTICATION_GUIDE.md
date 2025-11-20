# Using PowerShell Scripts with Personal Access Token (PAT)

## 🔑 New PAT-Enabled Scripts

I've created enhanced PowerShell scripts that can use your GitHub Personal Access Token automatically:

- **deploy_hammond_with_pat.ps1** - Deploy with PAT authentication
- **fix_hacs_with_pat.ps1** - Fix HACS with PAT authentication

These scripts eliminate the need to manually enter credentials every time!

---

## 🚀 Three Ways to Provide Your PAT

### Method 1: Environment Variable (Recommended for Security)

```powershell
# Set for current session
$env:GITHUB_PAT = "ghp_your_token_here"

# Then run script
.\deploy_hammond_with_pat.ps1
```

**Pros**: Most secure, token not saved to disk  
**Cons**: Need to set each PowerShell session

To set permanently (Windows):
```powershell
# Open System Properties
[System.Environment]::SetEnvironmentVariable('GITHUB_PAT', 'ghp_your_token_here', 'User')
```

### Method 2: Save to .github_pat File (Convenient)

The script will ask if you want to save your token:

```powershell
.\deploy_hammond_with_pat.ps1
# When prompted, enter 'y' to enter PAT
# Enter your token
# When asked to save, enter 'y'
```

This creates `.github_pat` file with your token.

**Pros**: Convenient, automatic for future runs  
**Cons**: Token stored on disk (but added to .gitignore)

### Method 3: Enter Each Time (Most Secure)

Just run the script and enter 'n' when asked to save:

```powershell
.\deploy_hammond_with_pat.ps1
# Enter token when prompted
# Select 'n' when asked to save
```

**Pros**: Token never saved  
**Cons**: Must enter every time

---

## 📋 Complete Workflow

### Initial Deployment with PAT

```powershell
# Navigate to project
cd C:\path\to\solark_cloud_integration

# Option A: Set PAT as environment variable
$env:GITHUB_PAT = "ghp_your_token_here"

# Run deployment script
.\deploy_hammond_with_pat.ps1

# Script will automatically push using PAT - no manual git push needed!
```

### Fix HACS with PAT

```powershell
cd C:\path\to\solark_cloud_integration

# Option A: PAT already set
$env:GITHUB_PAT = "ghp_your_token_here"

# Run fix script - automatically pushes!
.\fix_hacs_with_pat.ps1
```

### Using Saved PAT File

```powershell
# First time - save your PAT
.\deploy_hammond_with_pat.ps1
# Enter 'y' and your token
# Select 'y' to save

# Future runs - automatically uses saved PAT
.\fix_hacs_with_pat.ps1  # No need to enter token!
```

---

## 🔐 Creating a GitHub Personal Access Token

### Step-by-Step

1. **Go to GitHub Settings**
   - https://github.com/settings/tokens
   - Or: GitHub → Settings → Developer settings → Personal access tokens → Tokens (classic)

2. **Generate New Token**
   - Click "Generate new token (classic)"
   - Note: "Home Assistant Integration"
   - Expiration: Choose duration (recommend 90 days or No expiration)
   - Scopes: Check **☑ repo** (full control of private repositories)

3. **Generate and Copy**
   - Click "Generate token"
   - **Copy the token immediately!**
   - Format: `ghp_xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx`
   - Save it somewhere safe (password manager)

### Token Format

Valid token looks like:
```
ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefg123456789
```

Starts with `ghp_` or `github_pat_`

---

## 🆚 PAT Scripts vs Regular Scripts

### Regular Scripts (deploy_hammond.ps1, fix_hacs.ps1)
- ✅ Commits changes
- ❌ Doesn't push automatically
- 📝 You run `git push` manually
- 🔑 Git asks for username/password

### PAT Scripts (deploy_hammond_with_pat.ps1, fix_hacs_with_pat.ps1)
- ✅ Commits changes
- ✅ Pushes automatically using PAT
- ✅ No manual `git push` needed
- ✅ No username/password prompts

---

## 📝 Example Sessions

### Example 1: Using Environment Variable

```powershell
PS C:\> cd C:\Projects\solark_cloud_integration
PS C:\Projects\solark_cloud_integration> $env:GITHUB_PAT = "ghp_abc123..."
PS C:\Projects\solark_cloud_integration> .\deploy_hammond_with_pat.ps1

=======================================
  Sol-Ark Cloud - GitHub Deployer
  (with PAT authentication)
=======================================

Using GitHub PAT from environment variable
Configuration:
  GitHub User: HammondAutomationHub
  Repository: HomeAssistant_SolArk
  
Git repository already initialized.
Adding files to git...
Creating initial commit...
Configuring GitHub remote...

=======================================
Ready to Push!
=======================================

Pushing to GitHub with PAT authentication...

Successfully deployed to GitHub!
Your repository: https://github.com/HammondAutomationHub/HomeAssistant_SolArk
```

### Example 2: Save PAT to File

```powershell
PS C:\Projects\solark_cloud_integration> .\fix_hacs_with_pat.ps1

=======================================
  HACS Compliance Fix & Push
  (with PAT authentication)
=======================================

No GitHub PAT found.

You can provide your GitHub Personal Access Token in three ways:
1. Set environment variable
2. Create file .github_pat with your token
3. Enter it now (will not be saved)

Enter PAT now? (y/n): y
Enter your GitHub Personal Access Token: ********
Save token to .github_pat file for future use? (y/n): y
Token saved to .github_pat

Adding files to git...
Creating commit...
Changes committed successfully!

Pushing to GitHub with PAT authentication...

Successfully pushed to GitHub!

Next: Add to HACS
1. Open HACS -> Integrations
2. Three dots -> Custom repositories
3. Add: https://github.com/HammondAutomationHub/HomeAssistant_SolArk
4. Category: Integration
5. Should now work! ✨
```

### Example 3: Using Saved PAT File

```powershell
PS C:\Projects\solark_cloud_integration> .\fix_hacs_with_pat.ps1

=======================================
  HACS Compliance Fix & Push
  (with PAT authentication)
=======================================

Using GitHub PAT from file: .\.github_pat

Adding files to git...
Creating commit...
Changes committed successfully!

Pushing to GitHub with PAT authentication...

Successfully pushed to GitHub!
```

---

## 🔒 Security Best Practices

### DO ✅
- Use environment variables when possible
- Set expiration dates on tokens (90 days)
- Use minimal scopes (only 'repo' for this)
- Keep .github_pat in .gitignore (script does this)
- Delete tokens you're not using
- Regenerate tokens periodically

### DON'T ❌
- Commit .github_pat to git (it's in .gitignore)
- Share your PAT with anyone
- Use PAT in public scripts
- Email or message your PAT
- Use same PAT for multiple projects (create separate ones)

---

## 🛠️ Troubleshooting

### "Error pushing to GitHub"

**Check**:
1. PAT has 'repo' scope
2. Repository exists on GitHub (create at https://github.com/new)
3. PAT hasn't expired
4. Token is correct (no extra spaces/characters)

**Fix**:
```powershell
# Verify token works
$env:GITHUB_PAT = "ghp_your_token_here"
.\deploy_hammond_with_pat.ps1
```

### "Authentication failed"

**Solution**:
1. Go to https://github.com/settings/tokens
2. Generate new token
3. Copy it immediately
4. Try again

### PAT File Not Working

**Check file contents**:
```powershell
Get-Content .\.github_pat
# Should show: ghp_xxxxxxxxxxxxx (token only, no extra characters)
```

**Fix if needed**:
```powershell
"ghp_your_token_here" | Out-File -FilePath .\.github_pat -NoNewline -Encoding ASCII
```

### Token in .gitignore?

**Verify**:
```powershell
Get-Content .\.gitignore | Select-String "github_pat"
```

Should show:
```
.github_pat
```

If not, add it:
```powershell
Add-Content .\.gitignore "`n.github_pat"
```

---

## 📊 Comparison Table

| Feature | Regular Scripts | PAT Scripts |
|---------|----------------|-------------|
| Commits changes | ✅ Yes | ✅ Yes |
| Automatic push | ❌ No | ✅ Yes |
| Need manual `git push` | ✅ Yes | ❌ No |
| Password prompts | ✅ Yes | ❌ No |
| More convenient | ❌ No | ✅ Yes |
| Faster workflow | ❌ No | ✅ Yes |

---

## 🎯 Recommended Workflow

### For Regular Use (Recommended)

1. **First time**: Save PAT to file
   ```powershell
   .\deploy_hammond_with_pat.ps1
   # Save PAT when prompted
   ```

2. **Future updates**: Run and forget!
   ```powershell
   .\fix_hacs_with_pat.ps1
   # Automatically uses saved PAT
   ```

### For Maximum Security

1. **Each time**: Set environment variable
   ```powershell
   $env:GITHUB_PAT = "ghp_token"
   .\deploy_hammond_with_pat.ps1
   ```

2. **Close PowerShell** when done (clears env variable)

---

## 📍 Quick Reference

### Deploy First Time
```powershell
$env:GITHUB_PAT = "ghp_your_token"
.\deploy_hammond_with_pat.ps1
# Done! Automatically pushed.
```

### Fix HACS
```powershell
$env:GITHUB_PAT = "ghp_your_token"
.\fix_hacs_with_pat.ps1
# Done! Automatically pushed.
```

### Using Saved PAT
```powershell
.\fix_hacs_with_pat.ps1
# Uses .github_pat file automatically
```

---

## ✨ Benefits of PAT Scripts

- ✅ **Faster**: No manual git push or credential entry
- ✅ **Convenient**: Save token once, use forever
- ✅ **Automated**: One command does everything
- ✅ **Secure**: Token in environment variable or file (not in git)
- ✅ **Smart**: Automatically adds .github_pat to .gitignore
- ✅ **Flexible**: Three ways to provide token
- ✅ **Safe**: Removes token from remote URL after push

---

**Use PAT scripts for the smoothest deployment experience!** 🚀
