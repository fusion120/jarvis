---
lang: general
keywords: git, commit, push, branch, commit, github, repo
---
# Git workflow for this project

Every change to the jarvis repo flows: edit → commit → push → Render/Netlify
auto-deploy. Commit small, commit often.

```
git status                    # what changed
git diff backend/app11.py     # review before committing
git add backend/app11.py
git commit -m "vision: structured gaze analysis"
git push origin main          # triggers deploy
```

Good habits:
- Commit each logical change separately with a short, specific message
  (`"esp32: add talk expression"`, not `"stuff"`).
- Don't commit secrets — `agent_config.json` and API keys are gitignored.
- If stuck in a bad state: `git status` first, then decide. Never `git reset
  --hard` unless you're sure you want to lose the changes.
- A new feature → branch: `git checkout -b feature/x`, merge back after it
  works. Small personal projects can just commit to `main`.
- If a push is rejected, `git pull --rebase` then push again.

Gotchas: don't `git add .` blindly (you'll grab logs and keys); check
`git status` output first.
