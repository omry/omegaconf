# backlog-tool

Generates a structured view of a GitHub repo's open issues — Markdown for in-repo browsing, JSON for a static web UI, and a structured changelog.

> The `backlog-tool` name is a placeholder. A naming pass is planned.

## What it produces

Outputs land on a dedicated `backlog` branch (kept off `main` so issue churn doesn't pollute the main history):

- `BACKLOG.md` — categorized table of open issues + recently-done.
- `BACKLOG-UPDATES.md` — append-only human changelog of new/closed/status/label events.
- `backlog.json` — same data as `BACKLOG.md` but structured, consumed by the web UI.
- `updates.jsonl` — append-only structured event log (machine-readable changelog). Bootstrapped from `BACKLOG-UPDATES.md` on first run.
- `last_snapshot.json` — internal state used to diff against the next run.
- `events.jsonl` — log of GitHub issue/PR events queued for the next debounced run.
- `index.html` — bundled with the package; copied to the `backlog` branch by the workflow so a static page can be served via GitHub Pages.

## Install

```
pip install ./subprojects/backlog-tool   # from this monorepo
# or, once published:
# pip install backlog-tool
```

## CLI

```
backlog-tool update [flags]        # regenerate outputs from current GitHub state
backlog-tool install [flags]       # set up backlog branch + workflow YAML in a target repo
backlog-tool uninstall [flags]     # reverse install
backlog-tool dump-web --output X   # write the bundled index.html (or full web/ dir)
```

### `update`

Fetches issues/PRs from GitHub via `gh` and rewrites the backlog files. Useful flags:

- `--repo owner/name` — override repo detection (defaults to `sl`/`git` remote).
- `--dry-run` — print what would change without writing.
- `--snapshot-path` / `--event-log-path` / `--commit-msg-path` — workflow-driven I/O paths.
- `--data-json-path` / `--updates-jsonl-path` — override default output locations.

Defaults write everything under `<target-repo>/.backlog-tool/` so the file system isn't littered.

### `install`

```
backlog-tool install --repo owner/name [--pip-spec <pip arg>]
```

Creates the `backlog` branch via the GitHub API (if missing) and drops `.github/workflows/update-backlog.yml` into the target repo. The generated workflow does `pip install <pip-spec>` and runs `backlog-tool update` + `backlog-tool dump-web`. Default `--pip-spec` is `backlog-tool` (PyPI). Override with a git URL or local path until publication.

### `uninstall`

Removes the workflow YAML and (with confirmation) deletes the `backlog` branch.

## Web UI

The page is served from the `backlog` branch via GitHub Pages: enable Pages → branch `backlog` / `/`. It fetches `backlog.json` and renders an interactive view with search, category/status filters, sortable columns, dark/light themes, and a fixed bottom activity panel.

For local preview:

```
backlog-tool dump-web --output ./preview/
backlog-tool update --data-json-path ./preview/backlog.json
cd preview && python3 -m http.server 8000
# open http://localhost:8000/
```

## Tests

```
pytest subprojects/backlog-tool/test_update_backlog.py
```

## Layout

```
subprojects/backlog-tool/
├── pyproject.toml
├── README.md
├── backlog_tool/
│   ├── __init__.py             # CLI + all logic (single-module package for now)
│   ├── config.yaml             # default category/keyword/emoji config
│   ├── templates/
│   │   ├── backlog.md.tmpl
│   │   ├── backlog_updates_entry.md.tmpl
│   │   └── workflow.yml.tmpl   # GitHub Actions workflow template installed by `install`
│   └── web/
│       └── index.html          # bundled static UI
└── test_update_backlog.py
```
