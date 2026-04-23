# Provenance Tracking Design Note

This is an interesting feature request, but it is much larger than adding
line/column information to YAML-loaded configs.

The request starts from a YAML-centric example like `conf.foo.lc`, but the real
feature is broader: OmegaConf would need a general per-node provenance model
that can survive creation, mutation, merging, copying, resolution, and
potentially Hydra-driven loading through non-filesystem config sources.

## What users want

Users want to map an OmegaConf node back to where it came from so tools can
support navigation, diagnostics, and IDE features.

Examples:

- go to definition for a config key
- show source file and line for a selected node
- keep track of which merged source "won"
- potentially support Hydra config sources, not just local YAML files

## Why this is large

Today, OmegaConf mostly preserves runtime structure and typing, not source
provenance.

A full provenance feature would need to define behavior for:

- `OmegaConf.load()` from YAML
- `OmegaConf.create()` from Python values
- Hydra config loading through config source plugins
- merge operations
- direct Python mutation
- copying / deepcopy / pickling
- interpolation and resolution
- serialization back to YAML or conversion to Python objects

So the problem is not "store `line` and `column`". The problem is "define a
coherent provenance model for mutable config trees."

## Core design question

The key question is whether the feature should be:

1. YAML source locations only
2. General source provenance

A YAML-only API like `.lc` is attractive, but it likely does not scale well to
Hydra or programmatically created configs.

A more future-proof approach is to represent provenance abstractly.

## Suggested provenance model

Each node could optionally carry provenance metadata with fields like:

- `kind`: `file`, `hydra_source`, `python`, `merge`, `synthetic`, etc.
- `source`: path, package resource, provider name, URI-like id, etc.
- `line`: optional line number
- `column`: optional column number
- `span`: optional start/end range
- `origin`: optional richer record, if needed later

This supports YAML line/column while still allowing Hydra and Python-created
nodes to participate.

## Important semantics to define

The main challenge is defining semantics, especially because OmegaConf objects
are mutable.

For a first-class feature, behavior should be specified for at least:

- Load from YAML:
  - nodes should receive file-backed provenance
- Create from Python:
  - nodes should receive `python` provenance with no line/column
- Assignment:
  - assigning a Python value should replace provenance on that node
- Merge:
  - the winning node should probably keep the provenance of the winning input
- Replacement of subtrees:
  - new subtree provenance should replace old subtree provenance
- Synthetic nodes:
  - nodes introduced by operations may need synthetic provenance
- Interpolations:
  - unclear whether provenance should point to the interpolation expression, the
    resolved target, or both

These are policy decisions, not implementation details.

## Hydra considerations

Hydra makes this more valuable and more complicated.

Hydra abstracts loading behind config sources and plugins, so provenance cannot
assume "this always came from a local YAML file on disk." A useful design should
allow Hydra to attach provenance from arbitrary providers, such as:

- filesystem configs
- packaged configs
- plugin-backed sources
- composed configs assembled from multiple origins

That argues strongly against exposing only a YAML-specific `.lc` concept as the
primary abstraction.

## Privacy / information exposure

Provenance metadata may expose information that users do not currently expect to
be embedded in config objects.

Examples:

- absolute filesystem paths from the originating machine
- package layout or internal repository structure
- provider-specific identifiers
- environment-dependent locations that may be sensitive in logs, exceptions,
  pickles, or debug output

This matters especially if configs are:

- serialized
- logged
- transferred between systems
- inspected in notebooks, IDEs, or remote services

So the design should decide explicitly:

- whether provenance stores absolute paths, relative paths, or opaque source
  identifiers
- whether provenance is excluded from normal serialization/output by default
- whether provenance should be opt-in for tooling scenarios

## Current vs historical provenance

Another major design question is what provenance is intended to mean.

Possible interpretations:

- current effective source of this node
- original source of this node
- full history of how this node was produced

For example, if a node:

1. was loaded from `a.yaml`
2. got overridden by `b.yaml`
3. was later assigned from Python

possible meanings include:

- current provenance: `python`
- original provenance: `a.yaml`
- history: `a.yaml -> b.yaml -> python`

Tracking full history could be useful for debugging and tooling, but it greatly
increases complexity:

- higher memory overhead
- more expensive merge and mutation bookkeeping
- harder-to-design APIs
- greater privacy exposure

A more realistic first design would likely track only the current effective
provenance of each node, not full historical lineage.

## Implementation shape

A plausible phased implementation would be:

1. Introduce optional provenance metadata on OmegaConf nodes.
2. Add a small public API for reading provenance.
3. Teach YAML loading to attach provenance.
4. Define merge and mutation semantics.
5. Add provider hooks for Hydra/config sources later.

For API shape, a method is probably safer than a direct attribute at first, for
example:

- `OmegaConf.get_provenance(node_or_cfg, key=None)`

This keeps the initial feature flexible and avoids overcommitting to a YAML-only
interface.

## Why load-time support is easier than full support

Attaching provenance during YAML load is relatively contained.

The larger cost comes from keeping provenance correct after:

- mutation
- merges
- copy/deepcopy
- pickling
- future feature interactions

That is why a minimal "load-time only" implementation may be a reasonable first
milestone, but it should be explicitly documented as partial support.

## Backward compatibility risks

This feature is compatibility-sensitive.

Areas to evaluate:

- pickled OmegaConf objects
- `__getstate__` / `__setstate__`
- deep copy behavior
- memory overhead
- public/private metadata assumptions in downstream code
- whether provenance should survive serialization or be intentionally omitted

If provenance is stored as optional metadata and excluded from YAML output,
normal runtime compatibility is likely manageable. Still, serialized object
compatibility needs explicit review.

## Performance / footprint concerns

Per-node provenance will add overhead:

- extra memory per node
- extra work during load
- extra maintenance cost during merge/mutation

This may be acceptable, but it is worth considering whether provenance should
be:

- always on
- opt-in
- only enabled by specific loaders or providers

An opt-in mode may be attractive if the feature is primarily for tooling.

## Recommended scope

Recommended initial scope:

- define a general provenance model, not only YAML `lc`
- support provenance attachment during load
- expose read-only provenance access
- document that merge/mutation semantics are partial or preliminary unless fully
  specified

Recommended non-goals for a first pass:

- full provenance history
- complete interpolation provenance
- perfect Hydra integration on day one
- provenance-preserving round-trip serialization

## Bottom line

This is a promising feature, especially for IDE/tooling use cases, but it is
not a small change. It likely needs design work before implementation so the
project does not end up with a narrow YAML-only API that later clashes with
Hydra, mutation semantics, privacy concerns, or backward compatibility.
