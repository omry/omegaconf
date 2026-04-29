# Type Adapter System RFC

**Status:** Draft
**Stability:** Experimental for the initial release.

This is the short reviewer-facing version of the type adapter design. Detailed
implementation mechanics live in [spec.md](spec.md). Practical adapter-writing
guidance lives in [author-guide.md](author-guide.md). Security and governance
details live in [security-governance.md](security-governance.md).

## Summary

OmegaConf should support external value types through a dependency-free adapter
extension point instead of expanding the core primitive whitelist. A
`TypeAdapter` converts between an external Python value and an OmegaConf-native
representation, while a lightweight manifest lets OmegaConf discover adapter
metadata without importing heavy libraries such as NumPy or PyTorch.

The core model is:

- Scalar adapters preserve the external scalar value on normal access.
- Composite adapters expose an OmegaConf representation on normal access and
  materialize the external object through `OmegaConf.to_object()`.
- YAML stores only the representation, never adapter identity.
- Descriptors are string-based and dependency-light; runtime adapters use real
  Python types.
- Representation version and fallback policy are per handled type.
- Union branch selection is non-coercive and MRO-based.
- Official auto-discovery is allowlisted and dependency-lazy.

## Terminology

- **Scalar value:** custom leaf value with no sub-fields. Normal access returns
  the external value directly.
- **Composite object:** external value with fields or nesting. Normal access
  returns an OmegaConf representation; `to_object()` materializes the external
  value.
- **Adapter manifest:** lightweight declaration of adapter descriptors, exposed
  through package entry point metadata without importing heavy upstream
  libraries.
- **Adapter id:** stable `package:name` string naming the representation
  contract, used for configuration and node metadata.

## Problem

OmegaConf currently accepts a closed set of value types: `int`, `float`, `bool`,
`str`, `bytes`, `pathlib.Path`, `Enum` subclasses, and structured configs. Users
hit the same boundary with types that naturally appear in configs:

| User type                                | Why it fails today                             |
| ---------------------------------------- | ---------------------------------------------- |
| `numpy.float64`, `numpy.int32`, ...      | type-identity primitive checks                 |
| `numpy.ndarray`                          | not a list/dict/primitive                      |
| `torch.Tensor`                           | not a list/dict/primitive                      |
| `Boost.Python.enum`                      | inherits from `int`, not stdlib `Enum`         |
| `datetime.datetime`                      | needs per-node metadata for field formats      |
| `decimal.Decimal`                        | type-identity primitive checks                 |
| `ipaddress.IPv4Network`                  | not a list/dict/primitive                      |

The pattern is identical in every case: OmegaConf uses closed type whitelists
where an open adapter extension point would serve users better.

Adding these directly to OmegaConf core would create one-off special cases and
unacceptable optional dependency pressure. Unsafe YAML tags such as
`!!python/object` are also not viable because they are Python-specific, require
unsafe loading, and break portability.

Related issues and discussions:

- [#725](https://github.com/omry/omegaconf/issues/725) - numpy float/ndarray assignment
- [#1160](https://github.com/omry/omegaconf/issues/1160) - Boost.Python.enum support
- [#851](https://github.com/omry/omegaconf/issues/851) - datetime.datetime support
- [#97](https://github.com/omry/omegaconf/issues/97), [#873](https://github.com/omry/omegaconf/issues/873) - pathlib.Path support, now integrated into core
- [#844](https://github.com/omry/omegaconf/issues/844), [#872](https://github.com/omry/omegaconf/issues/872) - bytes support, now integrated into core
- [discussion #874](https://github.com/omry/omegaconf/discussions/874) - register custom node type

## Motivation And Alternatives

`pathlib.Path` and `bytes` show the cost of adding special cases directly to
OmegaConf core. Being stdlib types made their inclusion defensible, but each one
added maintenance surface. Third-party types would add both maintenance burden
and unacceptable dependencies.

PyYAML `!!python/object` tags were rejected because they require unsafe loading,
produce Python-specific YAML, require the external package at load time, and make
config data opaque to OmegaConf interpolation and merge behavior.

Loosening scalar conversion through protocols such as `__float__` or `__int__`
would help narrow cases like NumPy scalars, but it would coerce the value to a
nearby builtin and lose the external scalar type. The adapter design requires
exact preservation for adapted scalar values.

## Goals

- Allow external value types to participate in structured configs, assignment,
  merge, interpolation, serialization, cloning, and `to_object()`.
- Keep OmegaConf core dependency-free.
- Keep YAML portable and representation-only.
- Preserve exact scalar types instead of silently coercing them to Python
  builtins.
- Let composite values remain inspectable and overrideable as ordinary
  OmegaConf containers.
- Make adapter discovery safe, explicit for community packages, and lazy for
  heavyweight dependencies.
- Provide an executable conformance suite for official and community adapters.

## Non-goals

- Store large data objects or replace domain-specific serialization formats.
- Auto-load community adapters.
- Store adapter identity in YAML.
- Support arbitrary object pickle semantics through YAML.
- Introduce predicate-based adapter matching in v1.
- Require adapter authors to implement custom OmegaConf node subclasses.

## Core Model

### Scalar Adapters

Scalar adapters handle custom leaf values with no sub-fields. Normal access
returns the external value directly, so `type(cfg.lr) is np.float32` after
assigning `cfg.lr = np.float32(0.01)`.

Adapter lookup runs before native primitive handling so external scalar types
that inherit from builtins, such as Boost enum values or NumPy scalars, are not
silently coerced to `int` or `float`.

### Composite Adapters

Composite adapters handle values with structure, such as arrays, tensors, and
network objects. Normal access returns an OmegaConf representation; materializing
to the external object is explicit through `OmegaConf.to_object()`. This keeps
the representation mergeable, overrideable, and interpolatable.

### Descriptor/Runtime Split

The adapter contract is split into two layers: `TypeAdapterDescriptor`, a
lightweight declaration that stores handled type names as strings, and
`TypeAdapter`, the runtime implementation that uses real Python types only when
a concrete operation requires them. This keeps `import omegaconf` and official
adapter discovery dependency-light.

### YAML Representation-Only Rule

YAML stores the OmegaConf representation only. It does not store adapter id,
handled type, representation version, or fallback metadata. Loading YAML produces
plain OmegaConf data. Assigning or merging that data into a typed config can
restore adapter-backed nodes through the typed destination.

This keeps YAML portable and avoids unsafe Python object tags.

### `to_object()` Materialization Rule

Adapter metadata exists in memory and pickle, not YAML. For adapter-derived
nodes, `to_object()` returns the stored external scalar directly or calls
`adapter.from_node(node)` for composite values. This takes precedence over normal
structured-config instantiation.

## Public API Sketch

The experimental API shape is:

```python
class TypeAdapter(ABC, Generic[T]):
    # Real Python types handled by this runtime adapter.
    @property
    def handled_types(self) -> tuple[HandledType, ...]: ...

    # Validate/coerce an assigned value after node or Union branch selection.
    def convert(self, value: Any) -> T: ...

    # Represent an external value as OmegaConf nodes.
    def to_node(self, value: T) -> Node: ...

    # Materialize an external value from an adapter-backed representation.
    def from_node(self, node: Node) -> T: ...

    # Scalar adapters only: reversible text form for YAML/TOML-style serialization.
    def text_serialize(self, value: T) -> str: ...

    # Scalar adapters only: parse the reversible text form, when supported.
    def text_deserialize(self, s: str) -> T: ...

    # Human-facing string for interpolation into strings.
    def to_str(self, value: T) -> str: ...

    # Developer-facing representation for debug/REPL display.
    def to_repr(self, value: T) -> str: ...

# Lightweight entry point payload: all adapters exposed by a package.
TypeAdapterManifest(adapters: tuple[TypeAdapterDescriptor, ...])

# String-based descriptor used for discovery, listing, and lazy loading.
TypeAdapterDescriptor(id: str, handled_types: tuple[HandledTypeDescriptor, ...], type_adapter: str)

# Dependency-light handled type declaration used before runtime imports.
HandledTypeDescriptor(type: str, include_subclasses: bool = True, version: int = 1, fallback: FallbackSpec | None = None)

# Runtime handled type declaration using real Python type objects.
HandledType(type: type[Any], include_subclasses: bool = True, version: int = 1, fallback: FallbackSpec | None = None)
```

`FallbackSpec` names an optional representation-compatible fallback adapter for
a handled type. Its exact field-level policy is part of the implementor spec.

Registry APIs:

```python
# Activate all adapters exposed by a package or manifest entry point.
OmegaConf.load_type_adapter(package: str) -> None

# Remove descriptors registered by a package; existing nodes keep inert metadata.
OmegaConf.unload_type_adapter(package: str) -> None

# Inspect loaded/discoverable adapter descriptors without importing runtimes.
OmegaConf.list_type_adapters() -> list[TypeAdapterDescriptor]

# Configure a specific adapter by stable adapter id.
OmegaConf.configure_type_adapter(adapter_id: str, **options) -> None
```

`load_type_adapter()` takes an import module or entry point name.
`configure_type_adapter()` targets the stable adapter id because one package may
provide multiple adapters.

## Key Semantics

### Schema Annotation Acceptance

A structured-config annotation is valid when it is a built-in OmegaConf type, a
supported container type, or a type covered by a registered adapter. If the
adapter is missing, schema construction fails clearly, so adapters must be loaded
before schemas that reference their external types are constructed.

### Assignment and Conversion

Adapter-backed nodes use a two-phase model:

- Node creation chooses the adapter from the schema annotation or from the
  assigned value's concrete type for untyped assignment.
- Later assignments call `adapter.convert(value)` on the already selected node.

There is no separate coercive dispatch layer after branch or node selection.

### Union Branch Selection

`Union` remains non-coercive. Adapter-backed branches are selected from declared
handled type coverage, not by calling `convert()`. If multiple branches match,
OmegaConf walks the assigned value's Python MRO and chooses the most specific
declared type. This is deterministic and does not import unrelated adapter
dependencies.

### Serialization and Materialization

In-memory nodes and pickle preserve adapter metadata. YAML does not. A YAML file
containing an adapted representation can be loaded anywhere as plain data, then
merged into a typed config in an environment where the adapter is available.

Representation version mismatch is detected when materialization is attempted,
not when an adapter is loaded.

### Lazy Dependency Loading

Official adapter manifests may be discovered and registered at OmegaConf import
time, but manifest modules must not import the runtime adapter implementation or
the upstream library. Heavy dependencies may be imported only when a concrete
type, annotation, or adapter operation actually needs them.

## Ecosystem Model

Official adapters are maintained by the OmegaConf project and named
`omegaconf-<library>`. They are allowlisted for auto-discovery and must remain
dependency-lazy.

Community adapters are published by their maintainers, normally named
`omegaconf-contrib-<name>`, and are never auto-loaded. Applications activate them
with `OmegaConf.load_type_adapter()`. Listing in OmegaConf documentation requires
passing the conformance suite and declaring bounded OmegaConf compatibility.

## Security Model

OmegaConf's security boundary is the Python environment. The adapter registry is
not a sandbox. Auto-discovery is restricted to an allowlist of official
distribution names before entry point loading, preventing unrelated installed
packages from being imported as trusted adapters. Community adapters require
explicit activation by application code.

Code signing is not part of this design; package integrity belongs to ecosystem
tooling such as lock files, hash pinning, attestations, and trusted publishers.

## Open Questions

- What exact subset of the `Node` API is public for adapter authors?
- Should official adapters track OmegaConf versions or version independently
  with declared compatibility bounds?
- Should OmegaConf introduce a dedicated node-construction helper before the
  first adapter release?
- Which built-in scalar types should migrate to the adapter path after v1?

## Links To Detailed Specs / Appendices

- [Implementor spec](spec.md): full API definitions, manifest
  protocol, metadata layout, fallback rules, serialization paths, pickle and
  cloudpickle behavior, conformance suite, and lazy-loading contract.
- [Adapter author guide](author-guide.md): minimal examples,
  package layout, lazy import rules, scalar/composite decision guide, versioning,
  fallback, conformance tests, and common mistakes.
- [Security and governance appendix](security-governance.md):
  ownership tiers, allowlist behavior, supply-chain boundary, listing
  requirements, release notification policy, and compatibility policy.
