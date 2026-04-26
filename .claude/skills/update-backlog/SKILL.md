---
name: update-backlog
description: Sync backlog.md with current GitHub issue state (labels, status, new issues) while preserving hand-curated fields like time estimates and manual notes. Appends a change summary to backlog-updates.log.
---

Update `backlog.md` by syncing it against the current state of the omry/omegaconf GitHub repo. Follow these steps in order:

## 1. Fetch current open issues

```
gh issue list --repo omry/omegaconf --state open --limit 200 --json number,title,labels,state
```

## 2. Fetch full labels for all issues

```
gh issue list --repo omry/omegaconf --state open --limit 200 --json number,labels | jq -r '.[] | [.number, (.labels | map(.name) | join(", "))] | @tsv'
```

## 3. Identify status for each issue

Determine status using these rules (in priority order):
- **done**: issue is closed on GitHub, OR a merged PR formally closes it
- **in progress**: issue has an open PR that references or closes it
- **blocked**: issue carries the `awaiting response` label and has no open PR
- **not started**: everything else

To find open PRs and which issues they close:
```
gh api graphql -f query='{ repository(owner: "omry", name: "omegaconf") { pullRequests(states: OPEN, first: 50) { nodes { number title closingIssuesReferences(first: 10) { nodes { number } } } } } }' | jq -r '.data.repository.pullRequests.nodes[] | select(.closingIssuesReferences.nodes | length > 0) | "PR #\(.number) -> \(.closingIssuesReferences.nodes | map(.number) | join(", "))"'
```

Also scan PR bodies for informal issue mentions:
```
gh pr list --repo omry/omegaconf --state open --limit 50 --json number,title,body | jq -r '.[] | . as $pr | (.body | scan("#([0-9]+)") | .[0]) as $i | "PR #\($pr.number) mentions #\($i)"'
```

## 4. Check for newly resolvable issues

Look at recently merged PRs for issues that should now be marked done:
```
gh pr list --repo omry/omegaconf --state merged --limit 30 --json number,title,body,mergedAt
```

Cross-reference against issues still marked `not started` or `in progress` in backlog.md. If a merged PR clearly fixes a tracked issue (by title match or body reference), mark it `done` and note the PR number.

## 5. Update backlog.md

For each issue in backlog.md, update:
- **Labels**: replace with current labels from GitHub (full, untruncated)
- **Status**: update based on rules above
- **PR column**: add/update PR number if status is `in progress` or `done`

**Preserve without changes:**
- Time estimates (hand-curated judgment calls)
- Any notes or annotations added manually below the table
- Issues that were manually removed from the list

**Handle new issues** (in GitHub but not in backlog.md):
- Add them at the top of the table with status `not started`
- Assign a time estimate based on category and complexity (see methodology at bottom of backlog.md)
- Leave the PR column blank

**Handle closed issues** (in backlog.md but no longer open on GitHub):
- Mark status as `done` if not already
- Keep the row so the history is preserved

## 6. Update summary statistics

Recount By Status and By Category tables. Do not change the Time Estimates section.

## 7. Update the generation timestamp

Change the `Generated on` date at the top to today's date.

## 8. Append to backlog-updates.log

Before committing, append a structured entry to `backlog-updates.log` (create the file if it doesn't exist). The entry format is:

```
## YYYY-MM-DD

### New issues
- #NNNN Title (Category, Xh)
... or "none"

### Status changes
- #NNNN Title: not started → in progress (PR #MMMM)
- #NNNN Title: in progress → done (PR #MMMM)
... or "none"

### Label changes
- #NNNN: added "foo", removed "bar"
... or "none"

### Closed on GitHub (should be removed/archived)
- #NNNN Title — suggest closing: reason
... or "none"

---
```

Only log changes that actually occurred in this run. If a section has no changes, write "none" under it. Do not rewrite or modify previous entries — only append.

## 9. Commit the result

```
sl add backlog.md backlog-updates.log 2>/dev/null
sl commit -m "Update backlog.md: sync labels, status, and PRs from GitHub"
```

If there are newly identified done issues that haven't been formally closed on GitHub, ask the user whether to close them before committing.
