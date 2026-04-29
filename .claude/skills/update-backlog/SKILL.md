---
name: update-backlog
description: Synchronize BACKLOG.md and BACKLOG-UPDATES.md with the current GitHub issue state using the backlog script.
---

BACKLOG.md lives on the `backlog` branch (not `main`) to keep main history clean.
That branch also holds `BACKLOG-UPDATES.md`, `events.jsonl`, and `last_snapshot.json`.

## Running locally

```bash
# 1. Fetch current files from the backlog branch into the working tree
sl cat -r origin/backlog BACKLOG.md > BACKLOG.md
sl cat -r origin/backlog BACKLOG-UPDATES.md > BACKLOG-UPDATES.md
sl cat -r origin/backlog last_snapshot.json > last_snapshot.json

# 2. Preview changes (no writes)
python3 .claude/skills/update-backlog/scripts/update_backlog.py \
  --snapshot-path last_snapshot.json \
  --dry-run

# 3. Apply updates
python3 .claude/skills/update-backlog/scripts/update_backlog.py \
  --snapshot-path last_snapshot.json \
  --commit-msg-path /tmp/backlog_commit_msg.txt

# 4. Commit the updated files back to the backlog branch via GitHub API
BACKLOG_SHA=$(gh api "repos/omry/omegaconf/contents/BACKLOG.md?ref=backlog" --jq '.sha')
UPDATES_SHA=$(gh api "repos/omry/omegaconf/contents/BACKLOG-UPDATES.md?ref=backlog" --jq '.sha')
SNAPSHOT_SHA=$(gh api "repos/omry/omegaconf/contents/last_snapshot.json?ref=backlog" --jq '.sha')
COMMIT_MSG=$(cat /tmp/backlog_commit_msg.txt)

gh api repos/omry/omegaconf/contents/BACKLOG.md --method PUT \
  -f message="$COMMIT_MSG" -f content="$(base64 -w0 BACKLOG.md)" \
  -f sha="$BACKLOG_SHA" -f branch=backlog
gh api repos/omry/omegaconf/contents/BACKLOG-UPDATES.md --method PUT \
  -f message="$COMMIT_MSG" -f content="$(base64 -w0 BACKLOG-UPDATES.md)" \
  -f sha="$UPDATES_SHA" -f branch=backlog
gh api repos/omry/omegaconf/contents/last_snapshot.json --method PUT \
  -f message="$COMMIT_MSG" -f content="$(base64 -w0 last_snapshot.json)" \
  -f sha="$SNAPSHOT_SHA" -f branch=backlog

# 5. Clean up the temporary files from the working tree
sl forget BACKLOG.md BACKLOG-UPDATES.md last_snapshot.json
rm -f BACKLOG.md BACKLOG-UPDATES.md last_snapshot.json
```

The script accepts `--repo owner/name` to override repo detection. By default it resolves the GitHub repo from Sapling paths first, then Git remotes.

The script owns the generated backlog content and will:
- detect the GitHub repo from `sl` or `git` metadata unless `--repo` is provided
- fetch current collaborators, open issues, and open PRs with pagination
- render issue and PR references as GitHub links
- preserve the structured manual comments block
- preserve historical `done` rows already present in `BACKLOG.md`
- append `BACKLOG-UPDATES.md` only when there is a real change
- write a descriptive commit message to `--commit-msg-path` if provided
