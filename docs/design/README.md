# Design Notes

This directory contains durable design context for OmegaConf architecture,
invariants, interfaces, and compatibility decisions. It is maintainer-facing;
user documentation remains under [`docs/source/`](../source/).

For lifecycle statuses and metadata conventions, see
[`../document-lifecycle.md`](../document-lifecycle.md). Start new design
documents from [`TEMPLATE.md`](TEMPLATE.md).

## Active design guidance

- [TupleConfig](tuple-config.md)

## Draft and planned design work

- [Protected nodes](protect-node.md)
- [Provenance tracking](provenance-tracking.md)
- [Type adapter system](type-adapters/index.md)

## Historical design documents

- [Container union support](archive/container-union-support.md)
- [Key escaping in keypaths](archive/keypath-escaping.md)

## Reading design documents

- `Active` documents are current design guidance, but may describe an
  experimental API when stated explicitly.
- `Draft` documents capture work under consideration and are not commitments.
- `Superseded` and `Archived` documents provide context only; follow the named
  replacement when one exists.
- For shipped behavior, verify the implementation and user documentation. A
  design document explains intent and constraints but does not override them.

When adding a design document or changing its lifecycle status, update this
index in the same change.
