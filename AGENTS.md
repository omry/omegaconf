# AGENTS.md

Repo-specific directives for coding agents working in this project.

## Behavioral defaults

These guidelines are intended to reduce common LLM coding mistakes. Apply them alongside the repo-specific rules below. They bias toward caution over speed, and for truly trivial tasks you may use judgment.

### Think before coding

- Do not assume.
- Do not hide confusion.
- Surface tradeoffs.
- State assumptions explicitly when they matter to the implementation.
- If multiple reasonable interpretations exist, present them instead of silently picking one.
- If a simpler approach exists, say so.
- Push back when warranted.
- If something material is unclear or risky, stop, name what is confusing, and ask instead of guessing.

### Simplicity first

- Solve the requested problem with the minimum code necessary.
- No features beyond what was asked.
- No abstractions for single-use code.
- No flexibility or configurability that was not requested.
- No error handling for scenarios that are effectively impossible in context.
- If a solution feels overbuilt for the task, simplify it before considering it done.
- If you write 200 lines and the same result could be achieved in 50, rewrite it.
- Ask: would a senior engineer say this is overcomplicated? If yes, simplify.

### Surgical changes

- Touch only what is needed for the request.
- Do not "clean up" adjacent code, comments, formatting, or structure unless the change requires it.
- Match the existing style and patterns of the codebase unless the user asks for a broader refactor.
- If you notice unrelated dead code or issues nearby, mention them instead of fixing them opportunistically.
- Remove imports, variables, functions, or other artifacts that your change makes unused.
- Do not delete unrelated pre-existing dead code unless asked.
- Every changed line should trace directly to the user's request.

### Prefer built-in tools over shell commands

Use `Read`, `Grep`, `Glob`, `Edit`, and `Write` for file operations. Reserve
`Bash` for things that genuinely require shell execution: `sl` (Sapling) commands,
deleting files, or `nox` / `pytest` / `python` for tests, linting, and other
repo tooling.

### Goal-driven execution

- Translate requests into concrete success criteria that can be verified.
- For bug fixes, prefer reproducing the issue with a test or other reliable check before fixing it.
- For refactors, prefer checks that demonstrate behavior is preserved before and after.
- For multi-step tasks, keep a brief plan in mind and verify each step before calling the work complete.
- Favor specific goals over vague ones:
  - "Add validation" -> write tests for invalid inputs, then make them pass.
  - "Fix the bug" -> reproduce it with a test or reliable check, then make it pass.
  - "Refactor X" -> verify behavior before and after the refactor.

## Documentation map

- Sphinx/ReadTheDocs source: [`docs/source/`](./docs/source/)
- Entry point: [`docs/source/index.rst`](./docs/source/index.rst)
- Notebook tutorial: [`docs/notebook/Tutorial.ipynb`](./docs/notebook/Tutorial.ipynb)

## Stop and ask

- If a tracked repo file appears unexpectedly renamed, moved, regenerated, deleted, or otherwise changed, stop and ask before reverting, recreating, reclassifying, or staging over that change.
- Do not change the approved Privacy Policy or Terms of Service text unless the user explicitly asks for those documents to be edited.

## Verification

- For any new or changed functionality, test it in two layers:
  - run relevant unit tests with `pytest path/to/test_file.py`
  - run the broader suite with `nox` or `pytest` to ensure no regressions
- If the broader suite disagrees with the focused tests, trust the broader result and do not call the change verified.
- If live verification is blocked by the current environment, request escalation if that would unblock it. If not, stop and ask for guidance.

## Linting and formatting

This project uses several linting and formatting tools. Run them via `nox -s lint` or individually:

- `black .` / `black --check .` — code formatting
- `flake8` — style and error checks (may need `--jobs=1` on some Python versions)
- `isort . --check` — import sorting
- `pyrefly check` — static type checking

All four must pass before a change is considered clean.

## Environment and hooks

- When validating contributor setup, shell initialization, or hook behavior, verify it from the same environment a developer would actually use, such as a normal shell session or `sl commit`, not only from a temporary sandbox-only environment.
- Prefer hooks that do not depend on nontrivial user-environment tooling.
- If an environment override is required for one command, explain why it must be part of that same process invocation.
- If a small system tool would materially simplify the workflow, it is fine to suggest it or ask the user to install it.

## Sapling and escalation

This repo uses Sapling (`sl`) for source control, not `git` directly. Use `sl` for all VCS operations (status, log, commit, amend, etc.).

- Keep escalated `sl` commands minimal and single-purpose.
- Do not bundle staging, environment bootstrapping, dependency installation, and commit creation into one escalated shell command unless there is no practical alternative.
- If an `sl` operation requires escalation, ask only for the specific action that needs it.

## Release and fragments

- Do not commit, push, merge, publish, or otherwise send changes outside the local working tree unless the user explicitly asks for that outward action.
- If a change alters release automation, workflow triggers, deployment behavior, or other externally visible project mechanics, require an explicit user review checkpoint before any commit, push, merge, publish, or deployment action.
- Only product-user-visible changes should have a release fragment under `news/`. Developer-only tooling, repo maintenance, and other internal workflow changes do not count unless they change the shipped product experience.
- Fragment filenames follow the pattern `<issue_number>.<category>`. Supported categories are `feature`, `bugfix`, `api_change`, `docs`, and `misc`. Fragment text must be concise and user-facing.
- The user handles releases. Do not edit version numbers, create release files, assemble release notes, or otherwise perform release-cut steps unless explicitly asked.
- The release process is driven by GitHub Actions (`.github/workflows/publish.yml`). Do not improvise a manual release flow or treat GitHub Release text as the source of truth.

## Reviews

- When asked to review a commit, pull request, or diff, cover correctness, completeness, documentation, and internal consistency.
- Verify that each product-user-visible change includes an appropriate `news/` fragment and that the fragment matches the implementation and docs.
