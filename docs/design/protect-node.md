# protect_node Design Note

## What users want

Users want to mark specific keys in a config as immutable so that neither the
value nor the key itself can be changed after the config is set up.

The motivating case from issue #1161 is locking interpolation nodes so they
cannot be accidentally overwritten during config composition or runtime
mutation.

## Current workaround and its limitations

A partial workaround exists using internal API:

```python
def set_readonly_keys(conf, keys):
    for key in keys:
        OmegaConf.set_readonly(conf._get_node(key), True)
```

Setting `readonly` on a child node blocks writes *through* the node but does
not prevent the parent container from replacing or deleting it. The following
operations bypass the child's `readonly` flag entirely:

- `del cfg.a` — deletes the node via the parent
- `cfg.pop("a")` — same
- `cfg.a = new_value` where `a` holds a `Container` — replaces via the parent
- `OmegaConf.unsafe_merge(cfg, {"a": ...})` — overwrites in-place via the parent
- `OmegaConf.merge(cfg, {"a": ...})` — produces a new config, overriding the value (flag is copied but value is not protected)

The workaround also requires accessing private API (`_get_node`), which is not
acceptable as a public interface.

## Proposed design

### Public API

**Flag access** — operates on a container with a key or list of keys:

```python
OmegaConf.set_protected(cfg, "a", True)         # protect a single key
OmegaConf.set_protected(cfg, ["a", "b"], True)  # protect multiple keys
OmegaConf.set_protected(cfg, "a", False)        # clear protection
OmegaConf.set_protected(cfg, "a", None)         # reset to inherit from parent
OmegaConf.is_protected(cfg, "a")               # returns Optional[bool]
```

**Context manager** — temporarily clears `protected` on one or more keys:

```python
with unprotect(cfg, "a"):
    ...
with unprotect(cfg, ["a", "b"]):
    ...
```

### The `protected` flag

`protected=True` on a node:

- prevents writes *through* the node (effectively readonly, see below)
- prevents the parent container from replacing or deleting it

`protected` is fully independent from `readonly`: setting or clearing one does
not affect the other.

### Effective readonly check

`protected` is effectively readonly for write-through operations, but raises a
distinct exception. The check is:

```python
if node._get_node_flag("protected"):
    raise ProtectedNodeError(...)
elif node._get_flag("readonly"):
    raise ReadonlyConfigError(...)
```

`_get_node_flag("protected")` is non-inheriting: only the node with `protected`
set directly is blocked for write-through, not its descendants.
`_get_flag("readonly")` is the existing inheriting check, unchanged.

`ProtectedNodeError` and `ReadonlyConfigError` are fully separate exception
classes — not in a subclass relationship. They require different remedies:
`read_write` for readonly, `unprotect` for protected.

`read_write(cfg)` clears `readonly` on `cfg` and its inheriting children, but
does not touch `protected`. A protected node therefore remains blocked for
write-through even inside `read_write`. Only `unprotect` bypasses `protected`.

### Parent-level protection check

For operations that replace or delete a slot, the parent container checks the
existing child node before acting:

```python
target = self._get_node(key)
if target is not None and target._get_node_flag("protected"):
    raise ProtectedNodeError(...)
```

A distinct `ProtectedNodeError` exception is raised (not `ReadonlyConfigError`)
so callers can distinguish between a readonly violation and an attempt to
replace or delete a protected node.

`_get_node_flag` is non-inheriting: only a node with `protected` set directly
is protected from parent-level mutation. Setting `protected` on a container
does not protect its children from being individually replaced or deleted by
the container itself.

Checks are added in `BaseContainer` at:

- `__setitem__` / `__setattr__`
- `__delitem__` / `__delattr__`
- `pop`
- `merge_with` / `unsafe_merge`

### Protecting a container key

Setting `protected` on a key that holds a container is well-defined and useful:

- the container itself cannot be replaced or deleted by its parent
- writes directly through the container are blocked
- the container's own children are NOT protected (non-inheriting)

This is distinct from `readonly`: `readonly` on a container cascades to all
descendants; `protected` does not.

### Interaction with `merge`

`OmegaConf.merge` builds a new config and copies flags from source nodes to
the result. It does not raise for protected or readonly nodes — the result
simply carries the same flags.

`merge_with` mutates in-place. If the destination node is `readonly`, it raises
`ReadonlyConfigError`. If a destination node is `protected`, it raises
`ProtectedNodeError`.

`unsafe_merge` skips deepcopy and moves source nodes directly into the target
(making the source configs inconsistent afterward). Like `merge`, it does not
raise for `readonly` or `protected` nodes. Both `merge` and `unsafe_merge`
internally suppress readonly and protected checks when calling `merge_with`.

## Semantics summary

| Operation | Blocked by `readonly` | Blocked by `protected` | Bypassed by `read_write` | Bypassed by `unprotect` |
| --------- | --------------------- | ---------------------- | ------------------------ | ----------------------- |
| write through node | `ReadonlyConfigError` | `ProtectedNodeError` | `readonly` only | yes |
| replace via parent | `ReadonlyConfigError` (ValueNode only) | `ProtectedNodeError` | no | yes |
| `del` via parent | no | `ProtectedNodeError` | no | yes |
| `pop` via parent | no | `ProtectedNodeError` | no | yes |
| `merge_with` | `ReadonlyConfigError` | `ProtectedNodeError` | no | yes |
| `merge` / `unsafe_merge` | no error, flags copied | no error, flags copied | n/a | n/a |

## Implementation shape

1. Add `ProtectedNodeError` exception class.
2. Replace bare `readonly` checks with the two-part check
   (`_get_flag("readonly") or _get_node_flag("protected")`) in
   `ValueNode._set_value` and `BaseContainer.__setitem__`.
3. Add parent-level `_get_node_flag("protected")` checks raising
   `ProtectedNodeError` in `BaseContainer.__setitem__`, `__delitem__`, `pop`,
   and `merge_with`.
4. Add `OmegaConf.set_protected(cfg, key_or_keys, value)` and
   `OmegaConf.is_protected(cfg, key)`.
5. Add `unprotect(cfg, key_or_keys)` context manager temporarily clearing
   `protected` on the named child nodes via `flag_override`.
6. Add a news fragment under `news/1161.feature`.

## Decisions

- Dotlist keys (e.g. `"nested.x"`) are out of scope for `set_protected`. A
  separate API for setting flags via dot path could be added independently.
- `ListConfig` is supported with the same API using integer indices; the
  implementation differs but the interface is identical.
