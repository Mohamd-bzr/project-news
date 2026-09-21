# Push this project to GitHub — 2 commands

The repository is already initialized, committed (3 commits on `main`),
and clean. Only the remote + push remain, because the fine-grained token
available to the agent has no write permissions.

## 1. Create the repo (if not already)

Open https://github.com/new

- Repository name: `mohmd-news`
- Visibility: **Private** (or Public — your choice)
- **Do NOT** tick "Add a README" (the local repo already has commits)
- Click **Create repository**

## 2. Connect and push

In a terminal opened at `E:\freebuff` run:

```
git remote add origin https://github.com/<YOUR-USERNAME>/mohmd-news.git
git push -u origin main
```

A browser window (Git Credential Manager) will open → sign in to GitHub
once → done. No token needed; the browser login is the easiest path.

If you prefer a token instead of the browser login, create one at
https://github.com/settings/tokens/new (tick `repo`), then:

```
git remote add origin https://<YOUR-USERNAME>:<YOUR-TOKEN>@github.com/<YOUR-USERNAME>/mohmd-news.git
git push -u origin main
```

## What is already excluded (on purpose)

- `.venv/` (200 MB), `freebuff.rar` / `freebuff.zip` (217 MB)
- `.mohmd_news.db`, caches, `.freebuff/`, logs
- `settings.json` and `backups/settings.json*` — so a future Telegram
  token pasted into the dashboard can never reach GitHub by accident

Everything else (55 files, ~36k lines: app, dashboard, scrapers, tests,
docs) is committed and ready.
