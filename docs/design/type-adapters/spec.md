# Type Adapter System Implementor Spec

This is the detailed implementor and maintainer specification for the type
adapter system. Most reviewers should start with
[rfc.md](rfc.md), which summarizes the architecture,
public API shape, and open decisions.

**Status:** Draft
**Stability:** The initial release will be marked experimental, allowing the public-facing adapter API (`TypeAdapter`, `TypeAdapterDescriptor`, `load_type_adapter`, etc.) to evolve without backward-compatibility constraints.
**Related issues (partial list):**
- [#725](https://github.com/omry/omegaconf/issues/725) - numpy float/ndarray assignment
- [#1160](https://github.com/omry/omegaconf/issues/1160) - Boost.Python.enum support
- [#851](https://github.com/omry/omegaconf/issues/851) - datetime.datetime support
- [#97](https://github.com/omry/omegaconf/issues/97), [#873](https://github.com/omry/omegaconf/issues/873) - pathlib.Path support (integrated into core)
- [#844](https://github.com/omry/omegaconf/issues/844), [#872](https://github.com/omry/omegaconf/issues/872) - bytes support (integrated into core)
- [discussion #874](https://github.com/omry/omegaconf/discussions/874) - register custom node type (Jasha)

---

## Terminology

| Term | Definition |
| ---- | ---------- |
| **Scalar value** | A custom value with no sub-fields. Normal access returns the external value directly. (e.g. `np.float32`, `decimal.Decimal`; historically integrated: `pathlib.Path`, `bytes`). |
| **Composite object** | An object with fields or nesting. Normal access returns an OmegaConf representation (`DictConfig`, `ListConfig`, or structured config); `to_object()` materializes the external value. (e.g. `torch.Tensor`, `ipaddress.IPv4Network`). |
| **Distribution name** | The PyPI package name, e.g. `omegaconf-torch`. Used in the auto-discovery allowlist and package metadata lookup. |
| **Import module name** | The Python importable name, e.g. `omegaconf_torch`. Used in `load_type_adapter()`. |
| **Adapter manifest** | A lightweight dataclass instance, defined by OmegaConf core and exposed through package entry point metadata, that declares adapter descriptors without importing heavy upstream libraries. |
| **Adapter id** | A stable `package:name` string, e.g. `torch:tensor`. Names the representation contract. Used in `configure_type_adapter()` and stored in node metadata. |

---

## Problem

OmegaConf supports a fixed set of primitive value types: `int`, `float`, `bool`, `str`, `bytes`, `pathlib.Path`, `Enum` subclasses, and structured configs (dataclasses / attrs classes). This set is closed: any value whose type falls outside it is rejected with a `ValidationError`.

Users regularly encounter this wall with types from the scientific Python ecosystem:

| User type                                | Why it fails today                                                                                          |
| ---------------------------------------- | ----------------------------------------------------------------------------------------------------------- |
| `numpy.float64`, `numpy.int32`, ...      | `type(v) in (float, str, int)` - type-identity check                                                       |
| `numpy.ndarray` (n-dimensional)          | not a list/dict/primitive - no adapter path exists                                                          |
| `torch.Tensor` (scalar or n-dimensional) | same                                                                                                        |
| `Boost.Python.enum`                      | `issubclass(T, enum.Enum)` - not a stdlib Enum                                                              |
| `datetime.datetime`                      | no adapter path; blocked on per-node metadata support (format string is per-field, not global)              |
| `decimal.Decimal`                        | `type(v) in (float, str, int)` - type-identity check                                                       |
| `ipaddress.IPv4Network`                  | not a list/dict/primitive - no adapter path exists                                                          |

The pattern is identical in every case: OmegaConf uses **closed type whitelists** where **open adapter extension points** would serve users better.

### Why not add direct support?

OmegaConf is intentionally low in the stack. Adding `import numpy`, `import torch`, or `import Boost` as dependencies - even optional ones - would violate that constraint. The solution must be dependency-free at the OmegaConf level.

### Historical precedent

`pathlib.Path` and `bytes` are concrete examples of this pressure playing out — both were added directly to OmegaConf core at the cost of special-casing them throughout the codebase. Being stdlib types made their inclusion defensible, but each one added maintenance surface.

Every user type that does not fit the existing primitives creates the same pressure to bake it in as a one-off. For stdlib types that means maintenance burden alone. For third-party types (`numpy`, `torch`, `Boost`) it also means an unacceptable dependency. The adapter system addresses both.

### Why not use PyYAML `!!python/object` tags?

PyYAML can serialize arbitrary Python objects via `!!python/object/apply:torch.tensor` tags. This was considered and rejected for several reasons:

- Requires `yaml.full_load` / unsafe loader, enabling arbitrary code execution from config files. OmegaConf deliberately uses a safe loader.
- Produces Python-specific YAML that is not portable to non-Python consumers.
- Config files that contain `!!python/object:torch.Tensor` cannot be loaded on a machine without `torch` installed, even if the tensor field is never accessed.
- Opaque blobs break OmegaConf's interpolation machinery.

### Why not loosen scalar conversion (`__float__` / `__int__` protocol)?

Loosening `FloatNode` to accept any object where `float(v)` succeeds would fix the numpy scalar case with minimal code, and may work in narrow cases. However, it converts the value to a nearby Python primitive and loses the external scalar type, making roundtripping complicated — the same problem already visible with `enum_to_str`. It is not nearly enough for the general case.

If external scalar types are supported, the goal should be exact preservation for leaf values, not implicit conversion to `float` or `int`.

---

## Design

### Scope

The adapter system is designed for values that naturally belong in a config file: network addresses, color values, small coordinate arrays, date ranges. It is explicitly **not** designed to store large data objects or replace purpose-built serialization. Some adapters may enforce size limits to guard against accidentally storing large objects in config.

### Core concept: `TypeAdapter`

A `TypeAdapter` is a node-adaptation boundary. It teaches OmegaConf how to represent an external value as OmegaConf nodes, and how to materialize that value again when converting to native objects.

Scalar values are accessed as their native type; composite objects are accessed as an OmegaConf container and materialized to the original type via `to_object()`.

```python
cfg.lr = np.float32(0.01)
type(cfg.lr) is np.float32           # True — scalar, not coerced to float

cfg.weights = np.array([1.0, 2.0, 3.0])
type(cfg.weights) is ListConfig      # True — composite, accessed as OmegaConf container
OmegaConf.to_object(cfg).weights     # np.array([1.0, 2.0, 3.0])  — materialized
```

Storing external values through adapters rather than raw Python objects preserves OmegaConf's core benefits: interpolation (`${lr}` in YAML refers to the scalar directly), config merging across files and command-line overrides, runtime type safety at schema-annotated fields, YAML portability of the stored representation, and correct deep-copy and pickle semantics.

The `TypeAdapter` abstract base class defines the runtime interface that all adapters must implement. The manifest declares the stable adapter id and string-based handled type descriptors used for discovery; the runtime adapter declares the real Python types it handles and implements three core methods: `convert()` to validate and coerce an incoming value into one of the adapter's handled external types, `to_node()` to represent a validated value as OmegaConf nodes, and `from_node()` to materialize it back.

The adapter contract is split across two objects with distinct lifetimes:

- **`TypeAdapter`** — runtime object, instantiated from the descriptor's `type_adapter` dotted path only when a concrete adapter operation actually needs it.
- **`TypeAdapterDescriptor`** — lightweight declaration object used for manifests, discovery, listing, conflict validation, and lazy dispatch. Holds type names as strings; safe to inspect without importing any upstream library.

**`TypeAdapter`** defines the runtime interface (shown first for readability; descriptor types are defined in source before it):

```python
@dataclass(frozen=True)
class FallbackSpec:
    id: str                                     # stable adapter id of the fallback adapter
    type: str                                   # fallback handled type, e.g. "torch.Tensor"
    compatible_versions: tuple[int, ...] = ()   # exact tested fallback representation versions
    compatible_version_range: str | None = None # optional version range policy, e.g. ">=3,<5" or "*"


@dataclass(frozen=True)
class HandledType:
    # Real Python type — only referenced at runtime. String-based names for pre-import
    # inspection live in TypeAdapterDescriptor (HandledTypeDescriptor).
    type: type[Any]
    include_subclasses: bool = True
    # Representation version for this specific type's to_node() output. Bump when a
    # structural change would make existing stored representations unreadable (added
    # required fields, removed or renamed fields, changed field types). Backward-compatible
    # additions (optional fields with defaults) do not require a bump.
    version: int = 1
    # Optional fallback for this handled type's stored representation.
    fallback: FallbackSpec | None = None


class TypeAdapter(ABC, Generic[T]):
    @property
    @abstractmethod
    def handled_types(self) -> tuple[HandledType, ...]: ...
    # Returns real Python type objects — called only at runtime, after the TypeAdapter has been
    # invoked. String-based type names for pre-import inspection are on TypeAdapterDescriptor.

    def convert(self, value: Any) -> T:
        """Coerce an incoming assigned value to T. Called by an adapter-backed node
        when a value is assigned or merged into it.
        Raise ValidationError for incompatible values.
        Not called for Union branch selection — branch selection uses MRO-based dispatch
        over declared handled_types; convert() is called only after the branch is chosen."""
        raise NotImplementedError

    @abstractmethod
    def to_node(self, value: T) -> Node:
        """Represent a validated external value as OmegaConf nodes."""
        ...

    @abstractmethod
    def from_node(self, node: Node) -> T:
        """Materialize an external value from OmegaConf nodes.
        Must verify that the node representation is one this adapter can read.
        OmegaConf checks adapter id, handled type, representation version, and fallback
        dispatch before invoking from_node().
        For adapters that handle multiple external types, read metadata.object_type to
        determine which type to instantiate and apply the appropriate construction call —
        instantiation is not normalized across types. Each handled type carries its own
        version (HandledType.version), so a breaking representation change to one type
        does not invalidate stored objects of other types handled by the same adapter."""
        ...

    def text_serialize(self, value: T) -> str:
        """Canonical string form for text-based config serialization (YAML, TOML, and similar
        formats). Scalar adapters only — composite adapters are always serialized structurally
        via to_node(). Defaults to to_str(). Must pair with text_deserialize() if overridden —
        text_deserialize(text_serialize(v)) == v."""
        return self.to_str(value)

    def text_deserialize(self, s: str) -> T:
        """Parse a value from its text_serialize() form. Scalar adapters only. Optional —
        if not implemented, serialization uses the to_node() path instead of a scalar string."""
        raise NotImplementedError

    def to_str(self, value: T) -> str:
        """Human-facing string for embedded string interpolation (e.g. "lr=${lr}").
        No reversibility contract. Defaults to str(value)."""
        return str(value)

    def to_repr(self, value: T) -> str:
        """Developer-facing repr for debuggers and REPLs. Defaults to repr(value)."""
        return repr(value)
```

**`TypeAdapterDescriptor`** and its supporting types define the manifest and registration contract (string-based, no upstream imports required). `FallbackSpec` is shared with runtime `HandledType` and is shown above.

```python
@dataclass(frozen=True)
class HandledTypeDescriptor:
    # Fully qualified type name, e.g. "torch.Tensor". String, not a type object —
    # avoids importing the upstream library at registration time.
    type: str
    include_subclasses: bool = True
    # Representation version for this specific type. Mirrors HandledType.version.
    version: int = 1
    fallback: FallbackSpec | None = None


@dataclass(frozen=True)
class TypeAdapterDescriptor:
    id: str                                        # stable adapter id, e.g. "torch:tensor"
    handled_types: tuple[HandledTypeDescriptor, ...]
    type_adapter: str                              # "module.path:ClassName"; imported lazily


@dataclass(frozen=True)
class TypeAdapterManifest:
    adapters: tuple[TypeAdapterDescriptor, ...]
```

`Node` is not currently a normal public API. The minimal subset of the `Node` API that adapters may rely on is deliberately unspecified at this point. Adapter packages expose `TypeAdapterDescriptor` objects through the adapter manifest entry point.

### Adapter mechanics

**Storage.** Adapted values are stored as OmegaConf nodes with extra metadata — adapter id, selected handled type, and that handled type's representation version — so OmegaConf can distinguish them from ordinary config data. Adapter authors are discouraged from contributing custom Node subclasses (see design decision §4). OmegaConf provides the appropriate node machinery; adapters implement the conversion and materialization hooks. Storage semantics differ by kind:

- **Composite adapters** (tensors, arrays, IP networks, etc.) are stored as `DictConfig`, `ListConfig`, or structured configs with adapter metadata attached. Normal access returns the container; `to_object()` materializes the external object.
- **Scalar adapters** (`np.float32`, Boost enum, etc.) are stored in value nodes. The invariant is: normal access returns the external scalar value directly and its type must be preserved — `type(cfg.lr) is np.float32` must hold, not `type(cfg.lr) is float`. The value must not be silently coerced to a Python builtin primitive at storage time.

How this invariant is achieved is an implementation concern. Some scalar types may fit naturally into an existing node kind with minimal adaptation (e.g. a `str` subclass that only needs a custom `to_str` representation may store cleanly in a `StringNode`). Others will require a dedicated adapter-backed scalar node to prevent coercion. The design does not mandate one approach; it mandates the type-preservation invariant.

**Schema annotation acceptance.** A field annotation in a structured config is valid if:

1. it is a built-in OmegaConf-supported type (`int`, `float`, `bool`, `str`, `bytes`, `Path`, `Enum` subclass, dataclass/attrs class), or
2. it is a supported container type (`List`, `Dict`, `Optional`, `Union`), or
3. *(new — adapter system)* the annotated type is covered by a registered `TypeAdapter`.

If none of these conditions hold, OmegaConf rejects the annotation at structured config construction time with a clear error naming the unregistered type. This means adapters must be loaded before any structured config that uses their types is constructed — consistent with the requirement to register resolvers before use.

Today, OmegaConf `Union` fields are restricted to supported primitive-like members, including `Literal`; general structured-config/dataclass `Union` branches are follow-up work. Within that supported `Union` surface, `Optional[AdaptedType]` follows OmegaConf's existing `Optional` semantics. `Union[AdaptedType, ...]` follows OmegaConf's existing `Union` semantics: conversion is disabled to avoid ambiguous branch selection. The `Union` node selects a branch using the adapter's declared `handled_types` coverage rules, not by calling `adapter.convert()`. Adapter conversion is used only after the `Union` node has selected an adapter-backed branch.

For example, with `x: Union[np.float32, float]`, an incoming `np.float32` value can match the adapted branch and an incoming Python `float` can match the built-in branch. A string such as `"1.0"` is not automatically converted into either branch unless OmegaConf intentionally changes its general `Union` behavior.

If multiple `Union` branches match through declared adapter coverage (for example one branch covers a base type and another covers a subclass), OmegaConf uses the same MRO-based rule as value-driven dispatch: the branch whose declared type appears earliest in the assigned value's MRO wins. This is always deterministic and never forces new imports — see **Conflict resolution** below for details. Conformance tests for this resolution order will be added when general Union support for dataclasses and attrs classes is implemented (see §Follow-up work).

```python
OmegaConf.load_type_adapter("omegaconf_numpy")

@dataclass
class TrainConfig:
    lr: np.float32 = np.float32(0.001)   # valid — np adapter registered
    weights: np.ndarray = MISSING         # valid — np adapter registered

cfg = OmegaConf.structured(TrainConfig)  # succeeds
```

```python
# Without loading the adapter first:
@dataclass
class TrainConfig:
    lr: np.float32 = np.float32(0.001)

cfg = OmegaConf.structured(TrainConfig)
# ValidationError: Unsupported type 'numpy.float32'.
# To support external types, install the appropriate TypeAdapter plugin
# (e.g. omegaconf-numpy). Official plugins are auto-discovered on install;
# community plugins require an explicit load_type_adapter() call.
```

**Two-phase model.** Adapter-backed nodes follow OmegaConf's normal typed-node architecture in two distinct phases:

- **Node creation (schema definition time).** When a structured config is built, OmegaConf validates the annotation (see above) and creates an adapter-backed node for the field. For untyped assignment (`cfg.x = np.float32(1.0)`), node creation is value-driven: OmegaConf walks `type(value).__mro__` to find a registered adapter and creates the node from that.
- **Value assignment (any time thereafter).** All subsequent values arriving at the node are passed to `adapter.convert(value)`. The adapter accepts or rejects the value and coerces accepted values for its type; the node stores the adapter-backed representation. No separate dispatch layer exists.

The roles are clean: `ref_type` records the schema intent; the node invokes the adapter and stores the adapter-backed representation; the adapter implements assignment acceptance, coercion, representation, and materialization through `convert()`, `to_node()`, and `from_node()`.

**Handled type coverage.** Adapter maintainers declare whether each handled type covers only that exact runtime type or also its subclasses:

```python
HandledType(np.float32, include_subclasses=False)  # exact np.float32 values only
HandledType(torch.Tensor, include_subclasses=True) # torch.Tensor and subclasses
```

This coverage declaration is used by both value-driven adapter dispatch and `Union` branch selection.

**Value-driven dispatch.** Adapter selection by value type uses the registered `HandledType` coverage rules. For subclass-inclusive entries, OmegaConf considers the matching class's MRO position so the most specific registered adapter wins:

```python
for cls in type(value).__mro__:
    if cls is registered exactly or cls is covered by a subclass-inclusive entry:
        return matching_adapter
```

`__mro__` is precomputed by Python's C3 linearization when the class is defined, so dispatch is a tuple walk + registry lookup — no MRO computation at runtime. Subtype checks are driven only by a concrete runtime type or annotation that is already loaded; OmegaConf must not import unrelated adapter dependencies to search for possible subtype relationships. The most specific type in the loaded hierarchy wins. For type families without a shared base class (e.g. numpy's ~14 scalar types), enumerate each type explicitly in `handled_types`. Predicate matching is out of scope for v1.

**Conflict resolution.** Registration validates adapter id conflicts and exact handled type-name conflicts without importing upstream libraries. Subclass-overlap checks are lazy and local: they run only when a concrete loaded type or annotation triggers adapter resolution. Overlapping types via inheritance are not a conflict: the concrete type's MRO resolves them deterministically and is an intentional extensibility point — a `MyTensor(torch.Tensor)` adapter takes precedence over the Tier 1 `torch.Tensor` adapter automatically. The same MRO rule applies to `Union` branch selection, and it is always lazy: the registry stores type names as strings, so matching compares those strings against the qualified names of classes already in `type(value).__mro__`. You cannot have an instance of a type whose base classes are not imported, so no new imports are ever triggered. Under v1 rules (concrete classes, exact matching, `include_subclasses=True`) a true tie is not producible — Python's C3 linearization gives every concrete class a unique MRO, including multiple-inheritance cases (`Union[A, B]` assigned `C(A, B)` resolves to whichever of `A` or `B` appears first in `C.__mro__`). The ambiguous-assignment error path is reserved for future matching mechanisms.

**Families.** One adapter may cover a family of related types. Value-driven dispatch remains unambiguous because the adapter id names a shared representation contract, not a single class — `torch:tensor` can cover FloatTensor, IntTensor, etc.

**Priority.** Adapter selection runs before native primitive handling. This ensures external types that inherit from native types — Boost enum from `int`, numpy scalars from `float` — are caught by the adapter rather than silently coerced.

**Node construction in `to_node()`.** The node returned by `to_node()` is inserted into the tree as-is — OmegaConf does not re-dispatch adapters on it. This means `to_node()` may freely call `DictConfig`, `ListConfig`, or `OmegaConf.structured()` without risk of recursion. A dedicated node-construction API for adapter authors (cleaner and more type-safe than the raw `DictConfig`/`ListConfig` constructors) may be introduced before the first release.

### Loading and configuration API

```python
OmegaConf.load_type_adapter(package: str) -> None                      # package/module name
OmegaConf.unload_type_adapter(package: str) -> None                    # package/module name
OmegaConf.list_type_adapters() -> list[TypeAdapterDescriptor]
OmegaConf.configure_type_adapter(adapter_id: str, **options) -> None   # stable adapter id
```

**Thread safety:** `load_type_adapter`, `unload_type_adapter`, and `configure_type_adapter` operate on a global registry and are not thread-safe. They are startup-only operations, consistent with OmegaConf's general thread-safety stance and how resolver registration works today.


`load_type_adapter` activates an adapter and registers it globally. At registration, OmegaConf validates lightweight descriptor conflicts: adapter id conflicts and exact handled type-name conflicts. Checks that require real Python classes, such as subclass-overlap checks from `include_subclasses`, are deferred until adapter resolution is triggered by a concrete loaded type or annotation. Loading an already-loaded adapter is a no-op if the same adapter is already registered; an error is raised only if a descriptor-level or runtime conflict is detected. Official adapters (Tier 1 and 2) are auto-discovered and do not require an explicit `load_type_adapter` call — see §Ecosystem and Governance.

`load_type_adapter` takes an **import module name** (e.g. `"omegaconf_contrib_foo"`). OmegaConf finds the `omegaconf.type_adapters` entry point with that name, loads the lightweight manifest object it points to, obtains one or more `TypeAdapterDescriptor` objects from it, and registers them globally. The manifest module must not import upstream libraries at registration time. `unload_type_adapter` is symmetric: it removes all descriptors registered by that package. Existing adapter-derived nodes are unaffected — they remain valid `DictConfig`/`ListConfig` with inert metadata; only subsequent `to_object()` calls will fail if the adapter is no longer registered.

`configure_type_adapter` takes a **stable adapter id** (e.g. `"np:ndarray"`), not a package name. This is intentional: a single package may expose multiple adapters with different configuration options, and the adapter id is the unambiguous target. It requires the adapter to be loaded first and affects future adapter-mediated operations — `convert()`, `to_node()`, `from_node()`, and text/string hooks — on both existing and future nodes. The adapter id is looked up at operation time, so existing nodes pick up the new configuration immediately. Plain structural reads and writes on composite adapter representations (e.g. reading or setting fields of a `DictConfig`-backed tensor representation) are ordinary OmegaConf container operations and do not involve the adapter.

```python
OmegaConf.load_type_adapter("omegaconf_numpy")                       # load all adapters in package
OmegaConf.configure_type_adapter("np:ndarray", max_elements=1024)    # configure by adapter id
OmegaConf.configure_type_adapter("np:scalar", allow_precision_loss=False)
```

**Adapter-level configuration** covers global defaults that apply uniformly across all nodes of that adapter (e.g. `max_elements` for arrays). **Per-node concerns** that vary across instances of the same type (e.g. `datetime` format) belong in node metadata, not adapter configuration.



### What a companion library looks like

OmegaConf provides official adapters as separate maintained packages, and users can also implement their own. See §Ecosystem and Governance for the full model.

```python
# omegaconf_contrib_ipaddress/__init__.py  - illustrative sketch only
# Showcases a single adapter handling a family of related types.
import ipaddress
from dataclasses import dataclass
from typing import Any
from omegaconf import MISSING, HandledType, OmegaConf, ValidationError

@dataclass
class IPv4Network:
    network_address: str = MISSING
    prefixlen: int = MISSING   # 0–32

@dataclass
class IPv6Network:
    network_address: str = MISSING
    prefixlen: int = MISSING   # 0–128


class IPNetworkAdapter:
    @property
    def handled_types(self) -> tuple[HandledType, ...]:
        return (
            HandledType(ipaddress.IPv4Network, include_subclasses=False, version=1),
            HandledType(ipaddress.IPv6Network, include_subclasses=False, version=1),
        )


    def convert(
        self, value: Any
    ) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            return value
        if isinstance(value, str):
            return ipaddress.ip_network(value)
        if isinstance(value, dict) or OmegaConf.is_config(value):
            return ipaddress.ip_network(
                f"{value['network_address']}/{value['prefixlen']}"
            )
        raise ValidationError(f"Cannot convert {value!r} to an IP network")

    def to_node(self, value: ipaddress.IPv4Network | ipaddress.IPv6Network) -> Node:
        repr_cls = IPv4Network if isinstance(value, ipaddress.IPv4Network) else IPv6Network
        return OmegaConf.structured(repr_cls(
            network_address=str(value.network_address),
            prefixlen=value.prefixlen,
        ))

    def from_node(self, node: Node) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        # Exact metadata access API TBD. Adapter authors will receive a supported
        # way to inspect adapter metadata and metadata.object_type before release.
        external_type = node_metadata(node).object_type  # illustrative pseudocode
        return external_type(f"{node.network_address}/{node.prefixlen}")


# Adapter is activated by the user via: OmegaConf.load_type_adapter("omegaconf_contrib_ipaddress")
```

Each adapter package exposes a lightweight manifest object through package entry point metadata. The manifest object is an instance of OmegaConf's core manifest dataclass, so there is no YAML file to parse and no adapter-specific schema to invent:

```toml
# pyproject.toml
[project.entry-points."omegaconf.type_adapters"]
omegaconf_contrib_ipaddress = "omegaconf_contrib_ipaddress._manifest:MANIFEST"
```

```python
# omegaconf_contrib_ipaddress/_manifest.py
from omegaconf.type_adapters import (
    FallbackSpec,
    HandledTypeDescriptor,
    TypeAdapterDescriptor,
    TypeAdapterManifest,
)

MANIFEST = TypeAdapterManifest(
    adapters=(
        TypeAdapterDescriptor(
            id="ipaddress:ip_network",
            handled_types=(
                HandledTypeDescriptor(
                    type="ipaddress.IPv4Network",
                    include_subclasses=False,
                    version=1,
                ),
                HandledTypeDescriptor(
                    type="ipaddress.IPv6Network",
                    include_subclasses=False,
                    version=1,
                ),
            ),
            type_adapter="omegaconf_contrib_ipaddress:IPNetworkAdapter",
        ),
    ),
)
```

The `type_adapter` field is a `module.path:ClassName` string naming the concrete `TypeAdapter` implementation. OmegaConf imports that class lazily — only when a concrete adapter operation requires it. The entry point target is the manifest object itself, not the runtime adapter implementation.

OmegaConf uses `importlib.metadata.entry_points()` to find manifest entry points. For auto-discovery, OmegaConf checks the declaring distribution against the official allowlist before calling `entry_point.load()`, so non-allowlisted packages are never imported merely because they declared an entry point. There is no top-level `omegaconf.plugins` namespace package and no plugin registry module to import.

> **Note:** This example's manifest imports only OmegaConf schema classes. Official adapters for heavy libraries (`torch`, `numpy`, etc.) keep the manifest module separate from the adapter implementation and never import the upstream library in `_manifest.py`; the manifest's `type_adapter` dotted path points into the implementation module, which is imported only on demand.

The lifecycle is: incoming external object, string, or plain representation -> `convert()` -> `to_node()` -> stored OmegaConf representation -> `from_node()` during materialization.

### Adapter manifest protocol

Every adapter package declares its adapters through an `omegaconf.type_adapters` entry point. The entry point name is the manifest identity accepted by `load_type_adapter()` (normally the import module name, for example `omegaconf_contrib_ipaddress`), and the value is an ordinary Python object reference to a `TypeAdapterManifest` instance (for example `omegaconf_contrib_ipaddress._manifest:MANIFEST`). The manifest and descriptor dataclasses are defined in OmegaConf core, likely in a dedicated type-adapter submodule alongside the rest of the adapter machinery, and are part of the experimental adapter API. The discovery boundary is the manifest module: it may import OmegaConf's manifest schema, but it must not import heavy upstream libraries or the runtime adapter implementation.

**Manifest schema** (defined by OmegaConf core):

```python
@dataclass(frozen=True)
class TypeAdapterManifest:
    adapters: tuple[TypeAdapterDescriptor, ...]
```

The manifest contains the same `TypeAdapterDescriptor`, `HandledTypeDescriptor`, and `FallbackSpec` objects described above. The `type_adapter` string is resolved lazily — only imported when a concrete adapter operation needs it — using the `module.path:ClassName` convention.

For official adapters (Tier 1/2), OmegaConf verifies that the declaring distribution name appears on the trusted allowlist before calling `entry_point.load()` and registering the descriptors (see §Plugin security). Community adapters are loaded only through an explicit `load_type_adapter()` call.

Entry point names are adapter-manifest identities. A single distribution may expose multiple manifests by declaring multiple distinct entry point names, but duplicate names after the relevant filtering step are errors. Official auto-discovery fails if two allowlisted distributions declare the same `omegaconf.type_adapters` entry point name. Explicit `load_type_adapter(name)` fails if no entry point or more than one entry point matches `name`.

### Roundtripping

Roundtripping mirrors how structured configs work today.

Companion libraries represent adapted values using a domain-specific structured config:

**Full-fidelity path** - companion library's domain-specific structured config:

```python
# omegaconf_torch defines its own structured config to represent tensor metadata
@dataclass
class TensorRepr:
    data: List[float]        # or nested List[List[...]]
    dtype: str
    shape: List[int]
    stride: List[int]
```

```text
Write:  tensor([1., 2.], dtype=float16)
            --to_node()-->  DictConfig[TensorRepr]{data: [1.0, 2.0], dtype: "torch.float16", ...}
                            (adapter id, handled type, and representation version recorded in metadata)
Read:   TensorRepr-backed DictConfig  --from_node()-->  torch.tensor([1., 2.], dtype=torch.float16)  ✓ full fidelity
```

If the companion library goes with the full-fidelity path, the object **must** materialize to its original type (`torch.Tensor`, `numpy.ndarray`), not to a `TensorRepr` dataclass. The adapter-derived metadata ensures `to_object()` calls `adapter.from_node()` rather than treating the representation as an ordinary structured config.

YAML serialization uses the portable form of the node representation. For the full-fidelity path this is still plain, human-readable YAML:

```yaml
weights:
  data: [1.0, 2.0]
  dtype: torch.float16
  shape: [2]
  stride: [1]
```

This is portable representation-only YAML. Loading it produces plain OmegaConf data; merging or assigning that data into a typed config restores adapter-backed nodes through the normal destination-node conversion path.

### Interpolation

Because the stored representation is a native OmegaConf node, interpolation works without any changes to the interpolation engine. When using the full-fidelity path (domain-specific structured config), the encoded metadata fields like `dtype` and `device` are themselves plain OmegaConf scalars - and therefore interpolatable.

Adapters add no new interpolation semantics: scalar adapter nodes behave like typed scalar nodes, and composite adapter nodes behave like their underlying `DictConfig`/`ListConfig` representation.

Note: neural network weights are heavy and are serialized using native means, such as PyTorch `.pt` files. The examples below use realistic **config-scale** tensors: small arrays that naturally belong in a config file.

**Example 1 - Global dtype: change precision of all config tensors in one place**

```yaml
dtype: float32        # change to float16 for mixed-precision experiments

# Normalization statistics for image preprocessing
normalize:
  mean:
    data: [0.485, 0.456, 0.406]
    dtype: ${dtype}
  std:
    data: [0.229, 0.224, 0.225]
    dtype: ${dtype}

# Class weights for imbalanced loss
loss:
  class_weights:
    data: [0.1, 0.9]
    dtype: ${dtype}
```

**Example 2 - Global device: run preprocessing tensors on GPU or CPU in one place**

```yaml
device: cpu           # override to 'cuda:0' to run preprocessing on GPU

normalize:
  mean:
    data: [0.485, 0.456, 0.406]
    device: ${device}
  std:
    data: [0.229, 0.224, 0.225]
    device: ${device}
```

**Scope boundary:** The interpolation benefit applies to config-scale metadata (device, dtype, shape). Using OmegaConf resolvers to perform numerical computation on large tensors is outside the intended scope. OmegaConf is not a numerical computation engine.

### String conversion and display

Adapter authors control how adapted values appear in string contexts via optional hooks on `TypeAdapter`:

- **`to_str(value) -> str`** — human-facing string for embedded string interpolation (e.g. `"lr=${lr}"`). Defaults to `str(value)`. No reversibility contract.
- **`text_serialize(value) -> str`** — canonical string form for text-based config serialization (YAML, TOML, and similar formats). **Scalar adapters only** — composite adapters are always serialized structurally via `to_node()`. Defaults to `to_str()`. Must be reversible when paired with `text_deserialize()`: `text_deserialize(text_serialize(v)) == v`. The conformance suite enforces this contract when `text_deserialize` is implemented.
- **`text_deserialize(s: str) -> T`** — parse a value from its `text_serialize()` form. **Scalar adapters only.** Optional — if not implemented, serialization uses the `to_node()` path instead of a scalar string.
- **`to_repr(value) -> str`** — developer-facing representation for IDE debuggers and REPLs. Defaults to `repr(value)`. Adapter authors can return a concise structural summary (e.g. `Tensor([100, 2], dtype=float32)`) rather than dumping the full underlying `DictConfig`.

**String interpolation** (`${node}` embedded in a string value):

- *Adapted scalars*: OmegaConf delegates to `to_str()`.
- *Adapted composite objects*: embedding a composite in a string is not well-defined; OmegaConf raises an interpolation error.

**Scalar serialization (YAML and other text formats):**

- If the adapter implements `text_deserialize`: the field is written as a plain scalar string (`text_serialize()` output). When that string is assigned or merged into an adapter-backed scalar node, `adapter.convert()` may use `text_deserialize()` to reconstruct the value.
- If `text_deserialize` is not implemented: serialization traverses the node representation from `to_node()` structurally. When that representation is assigned or merged into an adapter-backed destination node, `adapter.convert()` validates/coerces it into the node representation.

**Composite serialization:** string hooks are never used. The underlying `DictConfig`/`ListConfig` is always traversed structurally.

**Future:** existing OmegaConf built-in scalars (`pathlib.Path`, `bytes`, etc.) will be migrated to the `text_serialize`/`text_deserialize` adapter path in a subsequent cleanup pass — see §Follow-up work.

### Untyped assignment

When a value is assigned without a schema (e.g. `cfg = OmegaConf.create({}); cfg.x = np.array([1.0])`), OmegaConf may still adapt it by exact value type. In memory and in pickle, the node can retain adapter metadata and therefore materialize through `to_object()`.

Portable YAML stores representation only. If the config is saved to YAML and loaded back, the result is ordinary OmegaConf data, not the original external object. Merging or assigning that data into an existing typed config can restore the adapted node and enable materialization.

### Boost enum values

`Boost.Python.enum` inherits from `int`, not from `enum.Enum`. Adapter lookup must therefore happen before native integer handling.

For Boost enum values, normal access should preserve the adapted scalar exactly. The risk is silently converting the value to `int` or to a stdlib `Enum` and losing the original type.

Portable string conversion is provided by `text_serialize`/`text_deserialize`. The Boost enum adapter implements these to expose a stable symbolic form (e.g. the enum member name) rather than the raw integer from `int.__str__`. `to_str` may return the same form or a more qualified human-readable variant — they need not be identical.

---

## Conformance Test Suite

OmegaConf ships a shared conformance test suite (`omegaconf.testing`) that defines the full behavioral contract for `TypeAdapter` implementations. Every companion library runs this suite against its own adapter and sample values.

The suite covers the full lifecycle of an adapted value: store/retrieve, roundtripping, YAML serialization, deep copy, merge, interpolation, `to_object`, pickle, and correct behavior in struct and readonly modes. For adapters that implement `text_deserialize`, the suite enforces reversibility: `text_deserialize(text_serialize(v)) == v` for all sample values. It also enforces lazy dependency loading for official adapters: operations that do not need the upstream type must not import heavy upstream libraries such as `torch`, `numpy`, or `boost`. This includes importing OmegaConf, official adapter discovery/registration, listing/configuring adapters, YAML loading of plain data, cloning, merging unrelated fields, and other metadata-only operations. Heavy libraries may appear in `sys.modules` only when a concrete type, annotation, or adapter operation actually needs them. The suite should use fake heavy dependency modules to verify this invariant, including `include_subclasses` declarations. The suite may include cloudpickle coverage for metadata-preserving serialization paths, verifying that adapter-derived configs survive serialization when the required adapter implementation and upstream runtime dependencies are available, or when the test intentionally serializes sufficient definitions for a self-contained fake adapter. Cloudpickle helps with representation classes and test fixtures, but it is not a substitute for installing the external library required to materialize an adapted value.

`omegaconf.testing` also provides a registry isolation helper (`adapter_scope`) for use in tests. It snapshots the current global registry on enter and restores it on exit, allowing the conformance suite and companion-library tests to load an adapter, run contract tests, and tear down cleanly without leaking registrations across tests. This helper is part of the test harness and is not part of the `OmegaConf` public API.

This makes the contract executable rather than just documented. Passing the conformance suite establishes that the adapter satisfies OmegaConf's adapter contract for the tested adapter version, OmegaConf version, upstream library version, and sample values. It does not prove compatibility across all future OmegaConf versions, all upstream library versions, or all possible values of the adapted type.

OmegaConf's own test suite includes a reference adapter backed by a simple `FakeExternalType` with no third-party dependencies, ensuring the suite infrastructure is verified independently of any companion library.

---

## Serialization and Cloning

Adapted values are ordinary OmegaConf nodes with additional metadata marking them as adapter-derived. Existing serialization, cloning, merging, and interpolation machinery should operate on the node representation as much as possible. The adapter-specific behavior is limited to metadata preservation and explicit materialization.

**Representation paths.** Adapter metadata — the signal that routes materialization to `adapter.from_node()` — exists in some paths but not others:

```text
In-memory:
  adapted nodes carry adapter metadata;
  normal access and materialization use the adapter.

Pickle:
  node metadata is preserved in the serialized form;
  materialization still requires the adapter to be registered in the target process.

YAML load:
  produces plain OmegaConf data (DictConfig / ListConfig / scalars);
  no adapter metadata exists; no adapter is required;
  to_object() does not reconstruct the external type.

Assignment/merge into typed config:
  the typed destination tells OmegaConf which fields are adapter-backed;
  OmegaConf requires a registered adapter for each adapted annotation;
  incoming plain values are converted by the adapter-backed node;
  to_object() can materialize the external type.
```

The core rule is: **YAML stores the adapter representation, not the adapter identity. Adapter identity comes from in-memory metadata or from the typed destination used during assignment/merge.** This keeps YAML portable — no `!!python/object`-style tags, no OmegaConf-specific markers.

**`to_object()` and adapter-derived nodes.** Adapter derivation takes precedence over the normal `SCMode.INSTANTIATE` path. Adapter metadata on the node is the signal:

- *Scalar adapter node:* return the stored value directly — it is already the external type.
- *Composite adapter node:* call `adapter.from_node(node)` — returns the external object, never the internal representation dataclass.

Non-adapted nodes follow the existing `to_object()` behavior unchanged.

**Node metadata.** OmegaConf's existing `Metadata` dataclass carries an `object_type` field for all nodes. For adapter-derived nodes, `object_type` records the selected handled type (`torch.Tensor`, `my_project.SpecialTensor`, etc.). Adapter-derived nodes also carry adapter-specific metadata: `type_adapter_id` and the selected handled type's representation `version`. OmegaConf is responsible for populating these fields — the adapter does not set them. At write time, OmegaConf uses the concrete type of the value being assigned (`type(value)` from the MRO walk for direct assignment, or the typed destination's schema annotation when plain data is assigned or merged into an existing typed config). Adapter metadata and `metadata.object_type` are set on the node before it is inserted into the tree, ensuring `to_object()` routes to `adapter.from_node()` rather than the normal structured config path.

OmegaConf resolves adapter metadata before invoking `from_node()`. On the normal path, the stored adapter id, selected handled type, and representation version must match a loaded adapter descriptor. On the fallback path, OmegaConf first verifies that the node declares a fallback for the selected handled type, that the loaded fallback adapter handles the declared fallback type, and that the fallback handled type version is accepted by either `compatible_versions` or `compatible_version_range`; if those checks succeed, OmegaConf may call the fallback adapter's `from_node()` even though the stored primary adapter id is different.

`from_node()` must verify that the node representation is one this adapter can read, then read `metadata.object_type` to determine the concrete external type to reconstruct. Because object instantiation is not normalized across types — different types have different constructor signatures and construction patterns — `from_node()` applies the appropriate instantiation call for each type it handles. Exact adapter-id matching is OmegaConf's dispatch responsibility, not always `from_node()`'s responsibility.

The adapter metadata is stored on the node metadata, not in YAML (see §YAML above):

```
# in-memory node metadata only
object_type: my_project.SpecialTensor     # selected handled type
type_adapter_id: "my_project:special_tensor"
type_adapter_version: 1                   # selected handled type representation version
type_adapter_fallback:                    # optional — declared for this handled type/version
  id: "torch:tensor"
  type: "torch.Tensor"
  compatible_versions: [1, 2]             # exact fallback representation versions tested as compatible
  compatible_version_range: ">=4,<6"      # optional policy range; either field can pass
```

This makes the adapter id, selected handled type, and selected handled type representation version accessible to `from_node()` via the Node API without requiring extra arguments. `type_adapter_id` is absent on ordinary (non-adapted) nodes, serving as the adapter-derived marker.

`type_adapter_fallback` is optional and declared on the selected handled type to name a more general adapter that can handle that specific stored representation. If a fallback is provided, at least one of `compatible_versions` or `compatible_version_range` must be non-empty. At read time, if the primary adapter id/type/version is not available, OmegaConf checks the fallback: if the fallback adapter is registered and handles the declared fallback type, the fallback is used when either the loaded fallback handled type version is listed in `compatible_versions` or it satisfies `compatible_version_range`. If the fallback adapter is missing or its handled type version does not satisfy either policy, the node remains accessible through its stored OmegaConf representation — a `DictConfig`/`ListConfig` or structured config for composite adapters, or the scalar node's stored value for scalar adapters. Adapter-mediated operations such as `to_object()` fail with a clear error naming the primary id/type/version, fallback id/type, exact compatible versions, and compatible version range. One level of fallback is the supported depth; chaining is not supported.

The fallback is the specialized adapter author's responsibility. A version listed in `compatible_versions` is an explicit tested claim that the fallback adapter at the declared handled type/version can operate on this handled type's stored representation. `compatible_version_range` is a policy claim over a range of versions; it uses comma-separated constraints with AND semantics, such as `">=3,<5"`. Runtime verification passes if either the exact-version list or the range policy accepts the loaded fallback handled type version. The special range `"*"` accepts any fallback representation version and is an explicit opt-in to future compatibility risk. Compatibility means the fallback adapter can materialize the stored representation with `from_node()`, write future values with `to_node()`, accept assignments compatible with that representation through `convert()`, and, when scalar text serialization is part of the representation contract, preserve the `text_serialize()` / `text_deserialize()` roundtrip. Display-only hooks (`to_str()`, `to_repr()`) are outside the compatibility contract. Compatibility is representation-level; it does not imply preservation of specialized subclass identity, methods, or behavior.

Any structural change to a `to_node()` representation requires a handled type representation version bump. Downstream adapters relying on the old representation for fallback must update their `compatible_versions` after testing exact new versions, or intentionally widen `compatible_version_range` if they accept that maintenance risk.

Persistence compatibility matters. A config may be saved today and loaded years later with a newer adapter and a newer version of the upstream library. Recording the selected handled type and representation version allows the future adapter to recognize older stored representations and special-case them when needed, or fail with a clear compatibility error if the old representation is no longer supported.

### YAML

YAML always loads as ordinary OmegaConf data, equivalent to the same data constructed from Python containers with `OmegaConf.create()`. Adapter behavior enters only when that data is assigned or merged into an existing typed config:

```yaml
weights:
  data: [1.0, 2.0]
  dtype: float32
  shape: [2]
```

Loaded from YAML, this is a plain `DictConfig` with three keys. The result is equivalent to `OmegaConf.create({"weights": {"data": [1.0, 2.0], "dtype": "float32", "shape": [2]}})`. No adapter is involved; `to_object()` produces a plain `dict`.

Merged **into an existing typed config** where `weights: torch.Tensor` with the `torch:tensor` adapter registered, the destination adapter-backed node receives the plain `weights` value. The node delegates conversion to `adapter.convert()`. Later, `to_object()` calls `adapter.from_node()` and returns a `torch.Tensor`.

The YAML file itself is identical in both cases. The adapter representation is stored in YAML; adapter identity is not.

**Missing adapter at schema construction time.** If a typed schema references an adapted field but no registered `TypeAdapter` handles that type, schema construction fails with a clear `ValidationError`. OmegaConf cannot safely construct the intended typed node without the adapter named by the annotation.

**Untyped YAML loading.** Untyped YAML loading always succeeds as plain OmegaConf data because there is no adapter identity in YAML and no typed annotation requiring an adapter. No companion library or adapter code is required for this path.

**Typed schema construction and merge.** Constructing the typed schema requires enough of the external type and adapter environment to create adapter-backed nodes. If the schema references an adapted type and no adapter is registered, schema construction fails. If the schema itself imports classes from the companion package and that package is absent, Python import/schema construction fails before OmegaConf can recover. After the schema exists, `OmegaConf.merge(Schema, UntypedConfigObject)` assigns the plain loaded data into the adapter-backed destination nodes.

For distributed workflows where the environment may lack the companion library (e.g. sending configurations to remote worker nodes), standard pickle is insufficient — Python's pickle stores only the class module path, not the definition, so unpickling raises `ModuleNotFoundError` on the remote. Users must rely on `cloudpickle` (or equivalent) to serialize the actual class bytecode in these scenarios.

### Cloning, merge, and pickle

Cloning, merging, and pickling all work normally — adapted nodes are plain OmegaConf nodes with extra metadata, so existing machinery handles them without adapter-specific code. The one exception: merging nodes with conflicting adapter ids raises `ConfigTypeError`. For pickle, the adapter instance is not stored; it must be re-registered in the new process before materialization is called, following the same contract as resolver registration. If the adapter is not registered when a pickled adapted node is accessed (but not materialized), access proceeds normally on the underlying OmegaConf node; only `to_object()` and similar materialization calls require the adapter to be present.

---

## Ecosystem and Governance

### Adapter ownership tiers

Three tiers of adapters are supported:

**Tier 1 - OmegaConf first-party adapters** The adapters motivating this design: `omegaconf-torch`, `omegaconf-numpy`, `omegaconf-boost`. Owned and maintained by the OmegaConf project. Driven by broad community need rather than any single requester. Sponsorship is welcomed and encouraged but not a condition of acceptance. Named `omegaconf-<library>`.

**Tier 2 - OmegaConf-owned, sponsor-backed adapters** A company or organization requests that OmegaConf officially own and maintain an adapter for their library's types. OmegaConf will accept ownership only with a long-term sponsorship commitment from the requesting party, reflecting the ongoing maintenance cost the project absorbs. Named `omegaconf-<library>`, indistinguishable from Tier 1 from a user perspective.

**Tier 3 - Community-contributed adapters** Anyone may write and publish an adapter. To be listed on the OmegaConf website and documentation, community adapters must:

- Follow the naming convention `omegaconf-contrib-<name>` (e.g. `omegaconf-contrib-docker`, `omegaconf-contrib-jax`)
- Pass the OmegaConf conformance test suite
- Declare a **bounded** OmegaConf version range (e.g. `omegaconf>=2.6,<3.0`). Open-ended ranges (e.g. `omegaconf>=2.0`) are not accepted - they make no testable compatibility claim and mislead users after breaking changes.

Community maintainers publish to PyPI themselves; OmegaConf only provides the listing. The OmegaConf project makes no maintenance commitment for Tier 3.

### Plugin discovery and initialization

Discovery behavior differs by tier:

**Official adapters (Tier 1 and 2)** are auto-discovered. Installing `omegaconf-torch` is enough to make it available — no user import or registration call required. `import omegaconf` may import allowlisted lightweight adapter manifest modules, but it must not import runtime adapter implementation modules or upstream dependencies such as `torch`, `numpy`, or `boost`.

Auto-discovery starts from package metadata and imports only allowlisted manifest modules:

1. OmegaConf asks `importlib.metadata.entry_points(group="omegaconf.type_adapters")` for installed adapter manifest declarations.
2. For each entry point, OmegaConf reads `entry_point.dist.name`, normalizes it, and ignores the entry unless the declaring distribution is on the trusted official-adapter allowlist (`omegaconf-torch`, `omegaconf-numpy`, `omegaconf-boost`, etc.).
3. Only after the allowlist check passes, OmegaConf calls `entry_point.load()` to obtain the `TypeAdapterManifest` instance.
4. OmegaConf validates that the loaded object is an instance of the core manifest dataclass and registers lightweight `TypeAdapterDescriptor` objects from it.
5. The entry point target must be a lightweight manifest module. It must not import the heavy upstream library or the runtime adapter implementation.

There is no top-level `omegaconf.plugins` namespace package and no plugin registry module to import. The installed distribution metadata is the discovery index. This is not a free-for-all: the standardized contract is the `omegaconf.type_adapters` entry point group plus the core `TypeAdapterManifest` schema, and only allowlisted official distributions are auto-activated. Community distributions may publish the same metadata, but OmegaConf ignores it during auto-discovery unless application code explicitly loads that adapter package.

Official adapter registration is lazy. It may declare adapter ids, handled type names (e.g. `"torch.Tensor"`), coverage rules, and `type_adapter` implementation paths, but it must not import `torch`, `numpy`, `boost`, or similar heavy upstream libraries. The conformance suite enforces that importing OmegaConf, discovering official adapter manifests, registering descriptors, listing/configuring adapters, and other metadata-only operations do not import upstream libraries or runtime adapter implementation modules. The upstream library is imported only when actually needed: a value of that external type is assigned, a structured config annotation uses that external type, or an adapter operation such as `convert()`, `to_node()`, `from_node()`, `text_serialize()`, or `text_deserialize()` needs the library. Subtype overlap checks follow the same rule: they are driven by the concrete loaded type involved in the operation, never by registry-wide eager imports.

**Community adapters (Tier 3)** are never auto-discovered. They become active only when explicitly loaded by application code via `OmegaConf.load_type_adapter()`:

```python
OmegaConf.load_type_adapter("omegaconf_contrib_foo")
```

To configure a specific adapter after loading, use its stable adapter id:

```python
OmegaConf.configure_type_adapter("foo:bar", max_elements=4096)
```

This keeps activation explicit, is linter-safe, and gives OmegaConf a consistent loading boundary across all tiers.

### Plugin security

**Security boundary:** OmegaConf's security boundary is the Python environment, not the adapter registry. If arbitrary code can run in the interpreter, it can monkey-patch any module, replace any function, and bypass any check OmegaConf performs — this is true of every language/runtime that executes plugin code and is not a Python-specific weakness. Standard ecosystem tools (pip hash pinning with `--require-hashes`, Sigstore/PEP 740 attestations, PyPI Trusted Publishers, lock files) are the right defenses at the right layer; OmegaConf adds nothing on top of them.

**Allowlist for auto-discovery:** Without any guard, unrestricted auto-discovery would allow any installed package to register an entry point in the `omegaconf.type_adapters` group and have it auto-loaded as a trusted adapter. To prevent this, OmegaConf checks `entry_point.dist.name` — the distribution name of the package that declared the entry point — against an allowlist of known official names before calling `entry_point.load()`.

This check is meaningful because PyPI enforces distribution name uniqueness: a package named `requests` cannot register an entry point whose declaring distribution appears to be `omegaconf-torch`. A supply chain attack on an unrelated PyPI package therefore cannot inject a fake entry point that passes the allowlist check.

The allowlist does **not** protect against: a compromised private index serving a package named `omegaconf-torch`, a local `pip install .` claiming the same name, direct modification of `site-packages`, or any scenario where the attacker can already execute code in the Python environment. For those threats, the environment itself is compromised and no library-level check is meaningful.

Code signing was considered and rejected. PKI infrastructure is maintenance-heavy, the public key would need to be bundled inside OmegaConf (itself subject to the same supply chain attacks), and it provides no protection once code is already running in the interpreter. The allowlist is the appropriate and sufficient control for what it can actually defend against.

### Versioning and compatibility

Official adapters introduce a three-way compatibility constraint: OmegaConf version x adapter version x upstream library version (torch, numpy, ...). The versioning scheme must make these constraints explicit (e.g. via `python_requires` / extras in `pyproject.toml`). Whether adapters should track OmegaConf versions (e.g. `omegaconf-torch 2.6.x` for OmegaConf 2.6.x) or version independently with declared compatibility bounds is an open decision.

### Release notifications and runtime enforcement

Before each major OmegaConf release, the project will make a best-effort notification to all listed Tier 3 maintainers (e.g. via GitHub issue or mailing list). Tier 3 maintainers are not release blockers - OmegaConf ships on its own schedule regardless of adapter update status.

One runtime enforcement mechanism is defined:

**Version mismatch detection at materialization time.** No warning or log is emitted at `load_type_adapter()` — silent load is intentional, to avoid console noise for version boundary conditions the application developer often cannot control. Instead, when a materialization call (`from_node()`, `to_object()`) fails, OmegaConf enriches the exception with version mismatch context derived from the node's stored adapter id, handled type, representation version, and any fallback declaration:

> *`ConfigTypeError: failed to materialize node; stored representation requires`*\
> *`adapter torch:tensor, type torch.Tensor, representation version 1, but the loaded`*\
> *`adapter does not support that version. Update the adapter or regenerate the config.`*

This surfaces the mismatch only when it actually causes a failure, with enough context to act on it.

---

## Design decisions and remaining notes

1. **Logical type**: The logical type remains the user type (`torch.Tensor`, `np.float32`, `Boost.Python.enum`, etc.). The adapter is the storage/materialization mechanism, not the field type.

2. **Adapter metadata**: There may not be a need for a dedicated wrapper node. Adapter-derived nodes are ordinary OmegaConf nodes whose metadata includes `object_type` plus adapter-specific fields such as `type_adapter_id` and representation version. `type_adapter_id` is the marker that distinguishes adapter-derived nodes from ordinary nodes.

3. **Adapter identity**: The adapter id is a stable `package:type` identifier naming the representation and materialization contract, not the adapter implementation class and not necessarily one exact runtime class. Examples: `boost:enum`, `torch:tensor`, `np:ndarray`, `np:scalar`.

4. **Node integration:** Adapters should not contribute custom `Node` subclasses. OmegaConf provides the adapter-backed node machinery required for scalar and composite adapters; adapters implement `convert()`, `to_node()`, `from_node()`, and optional text/string hooks. Custom `Node` subclasses are strongly discouraged: they increase coupling to OmegaConf internals and may complicate the planned node hierarchy simplification (see §5).

5. **Node hierarchy simplification (future — evaluate post-v1):** The adapter system supersedes much of what typed `Node` subclasses provide today by making the important type-specific behavior of a node polymorphic through adapter metadata and adapter dispatch. This opens a path to collapsing OmegaConf's current typed-node subclasses (`IntegerNode`, `FloatNode`, `EnumNode`, etc.) into a single `ScalarNode` kind, with built-in types migrated to first-class adapters. This would leave a two-kind node hierarchy: `ScalarNode` and Container (`DictConfig`/`ListConfig`). The flags cleanup (readonly/convert/struct owned by caller, not by nodes) is a prerequisite refactor in the same window. Requires a concrete backward-compatibility plan for pickled objects that contain typed-node class references by name — should be tracked as a dedicated follow-up issue once the adapter system ships.

6. **Cross-adapter dependencies (future)**: Adapters in v1 are self-contained — each adapter converts its input entirely to OmegaConf-native types and does not depend on other adapters being registered. If a future use case requires one adapter to declare a dependency on another (e.g. a composite adapter whose input handling delegates to a scalar adapter), that can be added with an explicit `requires` declaration and fail-at-load-time enforcement. Core OmegaConf adapters that ship bundled with OmegaConf are unlikely to need this mechanism; it is most relevant for community adapters that want to compose.

---

## Open design questions

The following must be discussed and resolved before this design is published.

- **Node API for adapter authors.** The subset of the `Node` API that adapters may rely on in `to_node()` and `from_node()` is currently unspecified. This includes whether a dedicated, type-safe node-construction API for adapter authors replaces direct use of `DictConfig`/`ListConfig` constructors. Must be defined before release — it forms the public contract between OmegaConf and adapter authors.

- **Adapter versioning scheme.** Whether official adapters track OmegaConf versions (e.g. `omegaconf-torch 2.6.x`) or version independently with declared compatibility bounds is an open decision.

---

## Follow-up work

The following items are out of scope for v1 but should be tracked as follow-up issues once the adapter system ships.

- **`allow_objects` evaluation.** `allow_objects` is an internal, undocumented flag that bypasses OmegaConf's type system to store arbitrary Python objects (e.g. large tensors) with no serialization contract. The adapter system is the right path for types with a defined serialization contract, but `allow_objects` may remain the correct escape hatch for intentionally non-serializable, store-by-reference objects that are explicitly out of scope for adapters. Once the adapter system lands, evaluate: formalize `allow_objects` as a supported but limited API (in-memory only, no YAML/pickle guarantees) with tight documentation, or deprecate it if the adapter system covers all legitimate use cases.

- **Node hierarchy simplification.** See design decision §5.

- **Built-in scalar migration.** `pathlib.Path`, `bytes`, and other built-in OmegaConf scalars are currently special-cased throughout the codebase. Once the adapter system is stable, migrate them to the `text_serialize`/`text_deserialize` adapter path, replacing the ad-hoc handling with a uniform, reversible serialization contract enforced by the conformance suite.

- **Structured-config `Union` support.** General `Union` support for dataclasses and attrs classes should build on the adapter system's non-coercive branch-selection model. The dependency is intentional: structured-config branch selection should reuse the same declared coverage, exact-vs-subclass policy, and ambiguous-assignment behavior defined here rather than inventing a parallel rule set.

- **`datetime.datetime` support.** Requires per-node metadata (format string) that is not yet supported — two `datetime` fields in the same config may legitimately use different formats (e.g. ISO 8601 vs. locale-specific). Full adapter support is deferred until the node metadata design matures to the point where per-node configuration can be associated with a field at schema time and accessed by the adapter during rendering.

- **Cross-adapter dependencies.** See design decision §6.
