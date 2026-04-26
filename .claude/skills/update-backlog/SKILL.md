---
name: update-backlog
description: Synchronize BACKLOG.md and BACKLOG-UPDATES.md with the current GitHub issue state using the backlog script.
---

Use the script in this directory to refresh the backlog from GitHub:

```bash
python3 .claude/skills/update-backlog/scripts/update_backlog.py --dry-run
python3 .claude/skills/update-backlog/scripts/update_backlog.py
```

The script accepts `--repo owner/name` if you want to override repo detection. By default it resolves the GitHub repo from Sapling paths first and then Git remotes.

The script owns the generated backlog content and will:
- detect the GitHub repo from `sl` or `git` metadata unless `--repo` is provided
- fetch current collaborators, open issues, and open PRs with pagination
- render issue and PR references as GitHub links
- preserve the structured manual comments block
- preserve historical `done` rows already present in `BACKLOG.md`
- append `BACKLOG-UPDATES.md` only when there is a real change
