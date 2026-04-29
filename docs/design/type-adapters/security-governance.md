# Type Adapter Security And Governance

This appendix contains the detailed ownership, discovery, security, and
compatibility policy for the type adapter system. The short architecture summary
lives in [rfc.md](rfc.md).

## Adapter Ownership Tiers

Three tiers of adapters are supported.

**Tier 1 - OmegaConf first-party adapters.** These are adapters motivated by
broad community need, such as `omegaconf-torch`, `omegaconf-numpy`, and
`omegaconf-boost`. They are owned and maintained by the OmegaConf project.
Sponsorship is welcomed but is not a condition of acceptance.

**Tier 2 - OmegaConf-owned, sponsor-backed adapters.** A company or organization
may request that OmegaConf officially own and maintain an adapter for its
library's types. OmegaConf accepts ownership only with a long-term sponsorship
commitment that reflects the ongoing maintenance cost. These packages are named
`omegaconf-<library>` and are indistinguishable from Tier 1 to users.

**Tier 3 - Community-contributed adapters.** Anyone may publish an adapter. To be
listed in OmegaConf documentation, community adapters must:

- Follow the naming convention `omegaconf-contrib-<name>`.
- Pass the OmegaConf conformance test suite.
- Declare a bounded OmegaConf version range, such as `omegaconf>=2.6,<3.0`.

Community maintainers publish to PyPI themselves. OmegaConf provides listing
only and makes no maintenance commitment for Tier 3 adapters.

## Discovery And Initialization

Official adapters are auto-discovered. Installing `omegaconf-torch` is enough to
make it available. `import omegaconf` may import allowlisted lightweight manifest
modules, but it must not import runtime adapter implementation modules or heavy
upstream dependencies such as `torch`, `numpy`, or `boost`.

Auto-discovery:

1. OmegaConf asks `importlib.metadata.entry_points(group="omegaconf.type_adapters")`
   for installed adapter manifest declarations.
2. For each entry point, OmegaConf reads `entry_point.dist.name`, normalizes it,
   and ignores the entry unless the declaring distribution is on the official
   allowlist.
3. Only after the allowlist check passes, OmegaConf calls `entry_point.load()` to
   obtain the `TypeAdapterManifest` instance.
4. OmegaConf validates that the object is an instance of the core manifest
   dataclass and registers lightweight `TypeAdapterDescriptor` objects from it.
5. The entry point target must be a lightweight manifest module. It must not
   import the heavy upstream library or runtime adapter implementation.

There is no top-level `omegaconf.plugins` namespace package and no plugin
registry module to import. Distribution metadata is the discovery index.

Community adapters are never auto-discovered. They become active only when
application code explicitly calls:

```python
OmegaConf.load_type_adapter("omegaconf_contrib_foo")
```

## Security Boundary

OmegaConf's security boundary is the Python environment, not the adapter
registry. If arbitrary code can run in the interpreter, it can monkey-patch
modules, replace functions, and bypass any check OmegaConf performs.

The allowlist protects only auto-discovery. Without it, any installed package
could declare an `omegaconf.type_adapters` entry point and be imported during
OmegaConf startup. OmegaConf checks the declaring distribution name before
calling `entry_point.load()`, so unrelated installed packages cannot register
themselves as trusted official adapters.

This check is meaningful because PyPI enforces distribution name uniqueness. A
package named `requests` cannot make its declaring distribution appear to be
`omegaconf-torch`.

The allowlist does not protect against:

- A compromised private index serving a package named `omegaconf-torch`.
- A local `pip install .` claiming an official package name.
- Direct modification of `site-packages`.
- Any scenario where the attacker can already execute code in the Python
  environment.

For those threats, standard ecosystem defenses are the right layer: lock files,
hash pinning with `--require-hashes`, Sigstore or PEP 740 attestations, PyPI
Trusted Publishers, and controlled package indexes.

## Why No Code Signing

Code signing was considered and rejected. PKI infrastructure is maintenance
heavy, the public key would need to be bundled inside OmegaConf, and that bundled
key is subject to the same supply-chain risks as the code enforcing it. It also
does not protect once code is already running in the interpreter.

The allowlist is the appropriate control for the specific risk it addresses:
preventing unrestricted adapter auto-discovery from importing unrelated packages.

## Compatibility Policy

Official adapters introduce a three-way compatibility constraint:

```text
OmegaConf version x adapter version x upstream library version
```

These constraints must be explicit through packaging metadata such as
`python_requires`, dependency bounds, or extras. Whether official adapters track
OmegaConf versions directly or version independently with declared bounds remains
an open design question.

Before each major OmegaConf release, the project will make a best-effort
notification to listed Tier 3 maintainers. Tier 3 maintainers are not release
blockers; OmegaConf ships on its own schedule regardless of adapter update
status.

## Runtime Version Enforcement

No warning is emitted at `load_type_adapter()` for version-boundary conditions.
Silent load is intentional because application developers often cannot control
all installed adapter versions.

Instead, OmegaConf enriches materialization failures with context from the
stored node metadata: adapter id, handled type, representation version, fallback
id, fallback type, exact compatible versions, and compatible version range.

Example failure shape:

```text
ConfigTypeError: failed to materialize node; stored representation requires
adapter torch:tensor, type torch.Tensor, representation version 1, but the loaded
adapter does not support that version. Update the adapter or regenerate the config.
```

The mismatch is surfaced only when it causes an actual failure, with enough
context for the user to act.
