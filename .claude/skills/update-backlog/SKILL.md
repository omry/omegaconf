---
name: update-backlog
description: Sync backlog.md with current GitHub issue state (labels, status, new issues) while preserving hand-curated notes. Appends a change summary to backlog-updates.md.
---

Update `backlog.md` by syncing it against the current state of the omry/omegaconf GitHub repo. Follow these steps in order:

## 1. Fetch maintainers

```
gh api repos/omry/omegaconf/collaborators --jq '.[].login'
```

Any PR author whose login appears in this list is a maintainer (`in progress`); all others are community contributors (`community PR`).

## 2. Fetch current open issues

```
gh issue list --repo omry/omegaconf --state open --limit 1000 --json number,title,labels,state
```

## 3. Fetch full labels for all issues

```
gh issue list --repo omry/omegaconf --state open --limit 1000 --json number,labels | jq -r '.[] | [.number, (.labels | map(.name) | join(", "))] | @tsv'
```

## 4. Identify status for each issue

Determine status using these rules (in priority order):
- **done**: issue is closed on GitHub, OR a merged PR formally closes it
- **in progress**: issue has an open PR by a maintainer (from step 1) that references or closes it
- **community PR**: issue has an open PR by a non-maintainer that references or closes it
- **blocked**: issue carries the `awaiting response` label and has no open PR
- **not started**: everything else

To find open PRs with their authors and which issues they close:
```
gh api graphql -f query='{ repository(owner: "omry", name: "omegaconf") { pullRequests(states: OPEN, first: 50) { nodes { number title author { login } closingIssuesReferences(first: 10) { nodes { number } } } } } }' | jq -r '.data.repository.pullRequests.nodes[] | select(.closingIssuesReferences.nodes | length > 0) | "PR #\(.number) [\(.author.login)] -> \(.closingIssuesReferences.nodes | map(.number) | join(", "))"'
```

Also scan PR bodies for informal issue mentions:
```
gh pr list --repo omry/omegaconf --state open --limit 50 --json number,title,body,author | jq -r '.[] | . as $pr | (.body | scan("#([0-9]+)") | .[0]) as $i | "PR #\($pr.number) [\($pr.author.login)] mentions #\($i)"'
```

## 5. Check for newly resolvable issues

Look at recently merged PRs for issues that should now be marked done:
```
gh pr list --repo omry/omegaconf --state merged --limit 30 --json number,title,body,mergedAt
```

Cross-reference against issues still marked `not started` or `in progress` in backlog.md. If a merged PR clearly fixes a tracked issue (by title match or body reference), mark it `done` and note the PR number.

## 6. Update backlog.md

The required file structure and table format are defined in `backlog-template.md` (same directory as this skill). Follow it exactly — column order, header text, separator, and status legend must all match the template. Key rules:
- Titles longer than ~55 chars should be truncated with `...`
- A literal `|` in a title must be escaped as `\|`
- Valid categories: `Bug`, `Enhancement`, `Refactor`, `Build`, `Documentation`, `Question`

For each issue in backlog.md, update:
- **Labels**: replace with current labels from GitHub (full, untruncated)
- **Status**: update based on rules above
- **PR column**: add/update PR number if status is `in progress`, `community PR`, or `done`

**Preserve without changes:**
- Any notes or annotations added manually below the table
- Issues that were manually removed from the list

**Handle new issues** (in GitHub but not in backlog.md):
- Add them at the bottom of the table (in issue-number order) with status `not started`
- Leave the PR column blank

**Handle closed issues** (in backlog.md but no longer open on GitHub):
- Mark status as `done` if not already
- Keep the row so the history is preserved

## 7. Sort the table by status

After all row updates, re-sort the table rows in this priority order (top to bottom):

1. `in progress`
2. `community PR`
3. `blocked`
4. `not started`
5. `done`

Within each status group, preserve the existing row order (do not re-sort by issue number).

Note: `#1006` has a literal `\|` in its title — split on unescaped `|` only when determining column positions.

## 8. Update summary statistics

Recount By Status (all issues) and By Category (open issues only — exclude `done` rows) tables.

## 8. Update the generation timestamp

Change the `Generated on` date at the top to today's date.

## 9. Append to backlog-updates.md

**Only append if at least one change occurred** (new issues, status changes, or label changes). If nothing changed, skip this step entirely — do not write a "none" entry.

Append a structured entry to `backlog-updates.md` (create the file if it doesn't exist). The entry format is:

```
## YYYY-MM-DD

### New issues
- #NNNN Title
... or omit section if none

### Status changes
- #NNNN Title: not started → in progress (PR #MMMM by omry)
- #NNNN Title: not started → community PR (PR #MMMM by someuser)
- #NNNN Title: in progress → done (PR #MMMM)
... or omit section if none

### Label changes
- #NNNN: added "foo", removed "bar"
... or omit section if none

### Closed on GitHub (should be removed/archived)
- #NNNN Title — suggest closing: reason
... or omit section if none

---
```

Only include sections that have actual changes. Do not rewrite or modify previous entries — only append.

## 10. Commit the result

```
sl add backlog.md backlog-updates.md 2>/dev/null
sl commit -m "Update backlog.md: sync labels, status, and PRs from GitHub"
```

If there are newly identified done issues that haven't been formally closed on GitHub, ask the user whether to close them before committing.
