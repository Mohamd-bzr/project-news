# Push this project to GitHub — current state

The repo is committed and ready: **5 commits on `main`** (redesign, security
fixes, viral tab, integrations, orjson/normalization). Only the remote + the
first push remain.

## Easiest path — double-click `push.bat`

1. Create the repo at https://github.com/new if it doesn't exist yet
   (name: `mohmd-news`, do NOT tick "Add a README").
2. Double-click `push.bat` in the project folder.
3. First run only: a browser window opens → sign in to GitHub once → done.

The script asks for the repo URL the first time and remembers it.

## Or manually

```
git remote add origin https://github.com/<YOUR-USERNAME>/mohmd-news.git
git push -u origin main
```

(Git Credential Manager opens the browser login on the first push.)

## What is excluded on purpose (.gitignore)

- `.venv/`, `backups/` (94 MB of pre-redesign copies), `*.bak`
- `.mohmd_news.db*`, all caches (`*.json` dot-caches, `correlation.json`), `logs/`
- **`settings.json`** and **`data/api_keys.json`** — a Telegram token or the
  API keystore can never reach GitHub by accident

## CI

`.github/workflows/ci.yml` runs on every push: full pytest + the
inline-dashboard-JS syntax gate. If it fails, GitHub emails you.
