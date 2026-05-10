# Standalone publication checklist

> Temporary planning note. Delete this file once the tool is published as a standalone project.

High-level items to take this subproject to a published standalone project.

## Identity & repo

- [ ] Pick a real name. The current `backlog-tool` is a placeholder (see README). Check PyPI + GitHub availability before anything else; the name leaks into the package, CLI entry point, config dir (`.backlog-tool/`), workflow filename, and docs.
- [ ] Extract to its own git repo (history-preserving via `git filter-repo` from `subprojects/backlog-tool/`, or seed a fresh repo from the current tree).
- [ ] Add `LICENSE` (BSD to match omegaconf, or MIT) and any attribution.

## Dependencies & decoupling

- [ ] Re-evaluate the `omegaconf>=2.3` runtime dep in `pyproject.toml`. If it is only used for config loading, stdlib + PyYAML is lighter and avoids the optics of "omegaconf publishes a tool that depends on omegaconf". Keep only if it earns its place.
- [ ] Audit for monorepo coupling: relative paths, references to omegaconf docs/AGENTS.md, shared nox sessions, fixtures from the parent test suite.

## Tooling

- [ ] Own lint/format/typecheck config (black, flake8, isort, pyrefly or mypy) plus either a `noxfile.py` or just `pyproject.toml` tool sections. The omegaconf nox sessions do not come along.
- [ ] CI workflows: test matrix (Python 3.10–3.13), lint, build wheel/sdist, publish on tag (PyPI Trusted Publisher).
- [ ] Pin a release process: single version source of truth, changelog mechanism (reuse `news/` fragments or switch to `CHANGELOG.md`).

## Tests

- [ ] Verify `test_update_backlog.py` runs from a clean checkout with no omegaconf-repo assumptions. Add `pytest.ini`/`conftest.py` as needed, and document the `gh`-CLI mock strategy.

## Docs

- [ ] Expand README: install from PyPI, quick-start, web UI screenshot, a "what this does to your repo" section for `install` (creates a branch + workflow).
- [ ] Optional design note on the snapshot/diff/event-log model so contributors understand the moving parts.

## Dogfooding

- [ ] Run `backlog-tool install` on the new standalone repo itself. Best end-to-end validation of the install path.

## Cleanup

- [ ] Delete this file (`STANDALONE-TODO.md`) once the tool is published.

## Open questions to resolve early

- Name + PyPI availability (blocks repo extraction and CI publish step).
- Keep or drop the omegaconf runtime dep.
- Where does development continue: new standalone repo from day one, or keep developing under `subprojects/` and mirror until cutover?
