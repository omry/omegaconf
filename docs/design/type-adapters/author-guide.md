# Type Adapter Author Guide

This guide is for people writing an OmegaConf type adapter. For architecture
review, start with [rfc.md](rfc.md). For the full maintainer contract, see
[spec.md](spec.md).

## Minimal Adapter Example

This example adapts `ipaddress.IPv4Network` and `ipaddress.IPv6Network` as
composite values. Normal access returns the OmegaConf representation;
`OmegaConf.to_object()` materializes the `ipaddress` object.

```python
# omegaconf_contrib_ipaddress/__init__.py
import ipaddress
from dataclasses import dataclass
from typing import Any

from omegaconf import MISSING, HandledType, OmegaConf, ValidationError


@dataclass
class IPv4Network:
    network_address: str = MISSING
    prefixlen: int = MISSING


@dataclass
class IPv6Network:
    network_address: str = MISSING
    prefixlen: int = MISSING


class IPNetworkAdapter:
    @property
    def handled_types(self) -> tuple[HandledType, ...]:
        return (
            HandledType(ipaddress.IPv4Network, include_subclasses=False, version=1),
            HandledType(ipaddress.IPv6Network, include_subclasses=False, version=1),
        )

    def convert(self, value: Any) -> ipaddress.IPv4Network | ipaddress.IPv6Network:
        if isinstance(value, (ipaddress.IPv4Network, ipaddress.IPv6Network)):
            return value
        if isinstance(value, str):
            return ipaddress.ip_network(value)
        if isinstance(value, dict) or OmegaConf.is_config(value):
            return ipaddress.ip_network(
                f"{value['network_address']}/{value['prefixlen']}"
            )
        raise ValidationError(f"Cannot convert {value!r} to an IP network")

    def to_node(self, value: ipaddress.IPv4Network | ipaddress.IPv6Network):
        repr_cls = IPv4Network if isinstance(value, ipaddress.IPv4Network) else IPv6Network
        return OmegaConf.structured(
            repr_cls(
                network_address=str(value.network_address),
                prefixlen=value.prefixlen,
            )
        )

    def from_node(self, node):
        # Exact metadata access API is still TBD.
        external_type = node_metadata(node).object_type
        return external_type(f"{node.network_address}/{node.prefixlen}")
```

## Manifest Example

Each adapter package exposes a lightweight manifest through the
`omegaconf.type_adapters` entry point group.

```toml
# pyproject.toml
[project.entry-points."omegaconf.type_adapters"]
omegaconf_contrib_ipaddress = "omegaconf_contrib_ipaddress._manifest:MANIFEST"
```

```python
# omegaconf_contrib_ipaddress/_manifest.py
from omegaconf.type_adapters import (
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

The manifest module must import only lightweight OmegaConf manifest classes and
stdlib modules. It must not import the runtime adapter implementation when that
implementation imports a heavy upstream dependency.

## Package Layout

Official adapters are owned by OmegaConf and use `omegaconf-<library>` as the
distribution name. They are allowlisted for auto-discovery.

Community adapters should use `omegaconf-contrib-<name>` when they want to be
listed by OmegaConf documentation. They are activated explicitly:

```python
OmegaConf.load_type_adapter("omegaconf_contrib_ipaddress")
```

Use the stable adapter id for configuration:

```python
OmegaConf.configure_type_adapter("ipaddress:ip_network", strict=True)
```

## Lazy Import Requirements

Keep the manifest separate from the runtime implementation. The manifest should
declare strings such as `"torch.Tensor"` and
`"omegaconf_torch._adapter:TensorAdapter"`. OmegaConf imports the runtime adapter
only when a concrete value, annotation, or adapter operation needs it.

Official adapters must pass lazy-loading tests: importing OmegaConf, discovering
official manifests, listing adapters, configuring adapters, loading YAML, and
merging unrelated fields must not import heavy upstream modules.

## Scalar Or Composite

Choose a scalar adapter when the value is naturally a leaf and normal access
should return the external value directly. Examples include `np.float32`,
`decimal.Decimal`, and Boost enum values.

Choose a composite adapter when the value has fields, shape, or nested data that
should remain inspectable and overrideable in OmegaConf. Examples include arrays,
tensors, and IP network objects.

Composite adapters should not use string hooks for YAML. They should serialize
through the structured representation returned by `to_node()`.

## Versioning Rules

`HandledType.version` is the representation version for that specific handled
type. Bump it when a `to_node()` representation changes in a way that may make
older stored representations unreadable, such as removing fields, renaming
fields, changing field types, or adding required fields.

Backward-compatible optional fields with defaults do not require a version bump.
Adapters that handle multiple types version each handled type independently.

## Fallback Rules

Fallback is declared per handled type. Use it when a specialized adapter stores a
representation that a more general adapter can safely read.

Declare only tested compatibility. `compatible_versions` is an exact list of
fallback representation versions known to work. `compatible_version_range` is a
policy claim over a range such as `">=3,<5"`. The special range `"*"` accepts
future compatibility risk explicitly.

Fallback is one level deep. Chained fallback is not supported.

## Conformance Suite

Adapter packages run the shared `omegaconf.testing` conformance suite against
their adapter and sample values. The suite covers store/retrieve, assignment,
roundtrip, YAML serialization, deep copy, merge, interpolation, `to_object()`,
pickle, readonly and struct mode, text serialization reversibility, and lazy
dependency loading for official adapters.

Use the `adapter_scope` helper from the test harness to isolate global registry
changes during tests.

## Common Mistakes

- Importing the upstream library from the manifest module.
- Storing adapter id or version fields in YAML.
- Coercing external scalar values to Python builtins during storage.
- Calling `convert()` to select a `Union` branch.
- Treating fallback as a promise to preserve subclass identity or behavior.
- Using an unbounded OmegaConf dependency range for a community adapter.
- Building custom OmegaConf `Node` subclasses instead of using adapter-backed
  node machinery.
