# Troubleshooting Notes

## 1. jamdict-data Installation — WinError 32
**Error:**
```
[WinError 32] 程序無法存取檔案，因為檔案正由另一個程序使用。: 'jamdict_data/jamdict.db.xz'
```
**Cause:** Windows Defender locks the `.xz` file during extraction.

**Fix:**
- Temporarily disable Windows Defender real-time protection during installation
- Or download `jamdict.db.xz` directly from Google Drive and extract manually with 7-Zip:
  https://drive.google.com/drive/u/1/folders/1z4zF9ImZlNeTZZplflvvnpZfJp3WVLPk
- Put extracted `jamdict.db` in `jamdictdb/jamdict.db`

---

## 2. jamdict Cannot Open Database
**Error:**
```
sqlite3.OperationalError: unable to open database file
```
**Cause 1:** Wrong parameter name — use `db_file` not `db_path`:
```python
# wrong
jam = Jamdict(db_path="...")

# correct
jam = Jamdict(db_file="...")
```

**Cause 2:** Folder and file have the same name:
```
jamdict.db/        ← folder
└── jamdict.db     ← actual file
```
Use the full nested path:
```python
jam = Jamdict(db_file=str(BASE_DIR / "jamdictdb" / "jamdict.db"))
```

---

## 3. Git Not Found in PowerShell
**Error:**
```
git : 無法辨識 'git' 詞彙
```
**Cause:** Git was installed after PowerShell was opened, so PATH wasn't updated.

**Fix:**
- Close and reopen PowerShell
- Or add Git to PATH permanently:
```powershell
[System.Environment]::SetEnvironmentVariable("PATH", $env:PATH + ";C:\Program Files\Git\cmd", "User")
```
- Note: In PowerShell use `where.exe git` not `where git`

---

## 4. Git Not Found in VSCode Terminal
**Error:**
```
FileNotFoundError: [WinError 2] 系統找不到指定的檔案
```
**Cause:** VSCode terminal doesn't inherit updated system PATH.

**Fix — add to VSCode settings.json:**
```json
{
    "terminal.integrated.env.windows": {
        "PATH": "C:\\Program Files\\Git\\cmd;${env:PATH}"
    }
}
```
Or hardcode the path directly in the bot:
```python
GIT = r"C:\Program Files\Git\cmd\git.exe"
```

---

## 5. GitHub File Size Limit
**Error:**
```
remote: error: File jamdictdb/jamdict.db is 310.32 MB; this exceeds GitHub's file size limit of 100.00 MB
```
**Cause:** `jamdictdb/` was not in `.gitignore` before first commit.

**Fix:**
```cmd
git rm -r --cached jamdictdb/
git filter-repo --path jamdictdb/ --invert-paths --force
git remote add origin https://github.com/username/repo.git
git push origin master --force
```
Make sure `.gitignore` contains:
```
jamdictdb/
```

---

## 6. Token Accidentally Pushed to GitHub
**Cause:** `.env` was not in `.gitignore` before first commit.

**Fix:**
1. Revoke token immediately via @BotFather → `/mybots` → Revoke token
2. Remove from Git history:
```cmd
python -m git_filter_repo --path .env --invert-paths --force
git remote add origin https://github.com/username/repo.git
git push origin master --force
```
3. Create new `.env` with new token
4. Make sure `.gitignore` contains `.env`

---

## 7. git filter-repo Not Recognized
**Error:**
```
git: 'filter-repo' is not a git command
```
**Fix:**
```cmd
pip install git-filter-repo
python -m git_filter_repo --path .env --invert-paths --force
```

---

## 8. Wrong Branch Name
**Error:**
```
error: src refspec main does not match any
```
**Cause:** Default branch is `master` not `main`.

**Fix:**
```cmd
git branch          ← check current branch name
git push -u origin master
```

---

## 9. Author Identity Unknown
**Error:**
```
Author identity unknown — Please tell me who you are.
```
**Fix:**
```cmd
git config --global user.email "your@email.com"
git config --global user.name "YourName"
```

---

## 10. run_polling() Unexpected Keyword Argument
**Error:**
```
Application.run_polling() got an unexpected keyword argument 'read_timeout'
```
**Cause:** Timeout arguments moved to `ApplicationBuilder` in newer versions.

**Fix:**
```python
app = (
    ApplicationBuilder()
    .token(TOKEN)
    .read_timeout(30)
    .write_timeout(30)
    .connect_timeout(30)
    .pool_timeout(30)
    .build()
)
app.run_polling(
    allowed_updates=Update.ALL_TYPES,
    drop_pending_updates=True,
)
```

---

## 11. Kotobank 404 Error
**Error:** Page not found on Kotobank.

**Cause:** Kotobank direct word URLs require an internal ID number.

**Fix:** Use search URL instead:
```python
# wrong
https://kotobank.jp/word/{word}

# correct
https://kotobank.jp/search/{word}
```

---

## 12. MkDocs gh-deploy — Git Not Found
**Error:**
```
ERROR - Could not find git - is it installed and on your path?
```
**Fix:** Run in Command Prompt instead of PowerShell:
```cmd
conda activate myenv
cd C:\Users\User\Documents\Japanese
mkdocs gh-deploy
```

---

## General Tips
- Always run `git status` before `git push` to check what files will be committed
- Use `git reset HEAD~1` to undo the last commit before pushing
- `.env` and `jamdictdb/` should never appear in `git status` as staged files
- In PowerShell use `where.exe git` instead of `where git`
- Restart VSCode completely after installing new tools for PATH to update