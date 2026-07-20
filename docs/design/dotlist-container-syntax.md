---
status: Suspended
updated: 2026-07-20
summary: Incremental dotlist syntax for dictionaries, lists, and tuples.
---

# Dotlist Container Syntax

Tracking issue: [issue #519](https://github.com/omry/omegaconf/issues/519)

This design is suspended. The feature started from a request for dotlist-style
flattened export, but a reliable `to_dotlist()` / `from_dotlist()` pair implies
round-trip semantics. Supporting that would trend toward a dedicated OmegaConf
serialization format, including container type markers, typed keys, tuple
construction rules, import policy for enum keys, and conflict semantics. That
scope is larger than the original export request and would still fall short of
real serialization formats for cases such as Structured Config identity.

## Summary

Add `OmegaConf.to_dotlist()` and extend dotlist parsing so container type is
preserved. Serialization always emits one entry per item. Deserialization
builds the complete input at once so list and tuple shape can be validated
before the final config is created.

This feature is experimental. In particular, changing `from_dotlist()` from a
dictionary-only constructor to one that may also return a root `ListConfig` or
`TupleConfig` expands the public API and may affect callers that assume a
`DictConfig` result.

## Syntax

Empty root containers are represented by their container literal:

```text
{}                # empty DictConfig root
[]                # empty ListConfig root
()                # empty TupleConfig root
```

An empty input still creates an empty `DictConfig`. An explicit `{}` may also
be used for an empty dictionary root.

Incremental paths identify the traversed container type:

```text
mapping.key       # dictionary key
items[0]          # list index
items(0)          # tuple index
```

Square brackets are used for both list indexing and dictionary key selection.
A bare integer bracket is a sequence index. A typed bracket is a dictionary key:

```text
items[0]=x                  # list index 0
mapping[int(0)]=x           # dictionary key 0
mapping[str(0)]=x           # dictionary key "0"
mapping[bool(true)]=x       # dictionary key True
mapping[bytes("abc")]=x     # dictionary key b"abc"
mapping[enum(pkg.Color, RED)]=x
```

The initial typed key literals are `str(...)`, `bytes(...)`, `int(...)`,
`float(...)`, `bool(...)`, and `enum(module.EnumClass, MEMBER)`. Bytes keys use
a quoted bytes string, with `bytes("")` representing `b""`. Canonical
serialization emits printable ASCII directly and uses byte escapes such as
`\n`, `\r`, `\t`, `\"`, `\\`, and `\xHH` for bytes that cannot be written
directly. Enum keys are expected to be rare; canonical serialization uses the
fully qualified enum type and member name.

Dotlist deserialization assumes container key type `Any`. This is not an
exhaustive serialization format, and the initial design does not include syntax
for declaring a container key type once.

For example, a tuple of dictionaries can be represented as:

```text
records(0).name=Alice
records(0).age=20
records(1).name=Bob
records(1).age=30
```

The equivalent list representation uses `records[0]` and `records[1]`.
Indices must be contiguous and start at zero. Sparse sequences are rejected.

Literal parentheses in dictionary keys use the same backslash escaping model
as other keypath metacharacters. Existing escaping for `.`, `[`, `]`, and `=`
continues to apply.

## Serialization

The proposed interface is:

```python
OmegaConf.to_dotlist(cfg, *, resolve=False) -> list[str]
```

Serialization follows these rules:

- Scalars produce individual `path=value` entries.
- Empty containers are emitted explicitly.
- Non-empty containers are expanded recursively into typed paths.
- Serialization does not collapse non-empty containers into inline values.
- Dictionary keys that cannot be represented by ordinary key syntax use a typed
  bracket key.
- Strings are quoted when an unquoted value would be parsed with a different
  value or type.
- Interpolations remain unresolved unless `resolve=True`.

A root list or tuple is emitted using root index paths:

```text
(0).name=Alice
(0).age=20
(1).name=Bob
(1).age=30
```

Empty root containers use the bare literals `{}`, `[]`, or `()`.

## Deserialization

`OmegaConf.from_dotlist()` accumulates the complete input into mutable
construction state, validates container shape, and then creates the final
`DictConfig`, `ListConfig`, or `TupleConfig`.

Incremental tuple construction does not mutate a `TupleConfig`. The tuple is
created once, after all of its elements and nested values have been collected.
A node cannot be defined both as a scalar value and through child paths in the
same input.

Conflicts are errors. This includes mixed container kinds for the same prefix,
mixed root kinds, and leaf/container conflicts:

```text
a[0]=x
a.key=y          # error: `a` cannot be both list and dict

a(0)=x
a[0]=y           # error: `a` cannot be both tuple and list

a.b=x
a.b.c=y          # error: `a.b` cannot be both leaf and container

[0]=x
a=y              # error: root cannot be both list and dict
```

When incremental tuple syntax is used with `merge_with_dotlist()`, the complete
tuple subtree is constructed and replaces the previous tuple atomically. It is
not a positional merge or a direct tuple-element mutation. Fixed and
homogeneous tuple annotations perform their normal arity and element
validation. Construction and validation errors must be detected before the
target subtree is mutated, so a failed tuple replacement leaves the previous
value unchanged.

## Compatibility and scope

- `to_yaml()` remains unchanged and continues to emit tuples as ordinary YAML
  sequences.
- Direct indexed mutation of an existing `TupleConfig` remains invalid.
- No YAML tuple tag is introduced.
- Hydra-style inline container values are a separate enhancement. If added,
  their merge semantics must be specified explicitly, including whether an
  inline container replaces the target or is recursively overlaid.
- Future value parsing may borrow parts of Hydra's CLI grammar, but must not
  depend on Hydra or inherit Hydra-only override features such as sweeps,
  functions, packages, groups, or CLI operators.
- Parsing `enum(module.EnumClass, MEMBER)` requires resolving the enum type.
  `from_dotlist()` supports enum key parsing only when the call site provides
  a whitelist that permits importing the enum type.
- Hydra will need matching tuple support for parity with this syntax.

## Test plan

- Round-trip incremental dictionaries, lists, and tuples.
- Cover empty, one-element, nested, root, and non-string-key containers.
- Cover typed dictionary keys, including `str`, `bytes`, `int`, `float`,
  `bool`, and enum keys.
- Cover tuples containing dictionaries and other sequences.
- Verify contiguous-index and malformed-container errors.
- Verify typed tuple arity and element validation.
- Verify interpolation preservation and `resolve=True` output.
- Verify key escaping, including literal parentheses.
- Verify atomic tuple replacement and rejection of direct tuple mutation.
