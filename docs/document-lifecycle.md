# Document Lifecycle

OmegaConf uses a lightweight lifecycle for design documentation. The status
header tells readers whether a document describes current guidance, work still
under consideration, or historical context.

## Statuses

- `Draft`: useful work in progress that is not yet the default reference
- `Active`: current design guidance, whether implemented or being implemented
- `Superseded`: replaced by a newer document or decision but retained for context
- `Archived`: historical context only, normally stored under `docs/design/archive/`

Lifecycle status is separate from API stability. An active design may still
describe an experimental API if the document says so explicitly.

## When to write a design document

Use a design document when a change affects architecture, invariants, public
interfaces, compatibility, rollout, or another area where the reasoning should
survive beyond an issue or pull request.

Prefer a shorter issue, pull-request description, or focused documentation
update when no durable design context is needed.

## Metadata

New or materially updated design documents should start with:

```md
---
status: Draft|Active|Superseded|Archived
updated: YYYY-MM-DD
summary: One-line purpose
supersedes: optional path
superseded_by: optional path
---
```

Use only fields that add useful information. The `updated` date records the
most recent substantive design-content change. When adding lifecycle metadata
to an existing document, use the date the document was added unless its design
content changed later. Status-only migration and archival do not change it.

## Lifecycle changes

- Move a draft to `Active` when it becomes current project guidance.
- Mark a document `Superseded` and identify its replacement when the design is
  replaced but remains useful context.
- Mark historical-only material `Archived` and normally move it under
  `docs/design/archive/`.
- Do not treat draft, superseded, or archived documents as current behavior.

## Update expectations

When a change alters architecture, invariants, public interfaces, compatibility,
or rollout, update the relevant design document in the same change. Keep
[`design/README.md`](design/README.md) consistent when adding a document or
changing its lifecycle status.

Implementation and user-facing documentation remain the source of truth for
shipped behavior. Design documents explain the intended model and the reasoning
behind it.
