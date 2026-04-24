# Container Union Support Design Note

OmegaConf currently supports unions of primitive value types, for example
`Union[int, str]`, but rejects unions that include containers:

```python
Union[int, List[str]]
Union[int, Dict[str, int]]
Union[List[int], List[str]]
Union[Dict[str, int], Dict[str, str]]
```

The current error is:

```text
Unions of containers are not supported
```

This design note evaluates adding support for `List[...]` and `Dict[...]`
members in union annotations.

## Goals

Support union-typed structured config fields where one or more union members are
typed list or dict containers.

Examples that should become valid:

```python
@dataclass
class Config:
    value: Union[int, List[str]]
```

```python
@dataclass
class Config:
    value: Union[Dict[str, int], Dict[str, str]]
```

The implementation should preserve existing OmegaConf typing guarantees after a
union branch has been selected. For example, if a field is selected as
`List[str]`, later appending an `int` should fail validation.

## Non-goals

This proposal does not cover:

- unions of structured configs
- `typing.Literal` support
- arbitrary user class unions
- deferred branch selection for unresolved empty containers; union type selection
  must be unambiguous at assignment time

Those features have related implementation points but different semantics and
should be evaluated separately.

## Current behavior

There are two main blockers today.

First, `is_supported_union_annotation()` only allows primitive union members:

```python
def is_supported_union_annotation(obj: Any) -> bool:
    """Currently only primitive types are supported in Unions, e.g. Union[int, str]"""
    if not is_union_annotation(obj):
        return False
    args = obj.__args__
    return all(is_primitive_type_annotation(arg) for arg in args)
```

Second, `UnionNode._set_value_impl()` rejects container values before trying
union candidates:

```python
elif isinstance(value, Container):
    raise ValidationError(
        f"Cannot assign container '$VALUE' of type '$VALUE_TYPE' to {type_str(type_hint)}"
    )
```

Adding support requires changing both annotation validation and assignment
semantics.

## Branch selection

When a value is assigned to a container union, OmegaConf needs to choose exactly
one union member.

For non-empty containers, this can usually be determined by validating the value
against each candidate in union order:

Plain Python containers are supported when their contents make the union branch
unambiguous. No explicit typed-container API is needed in those cases.

```python
Union[List[int], List[str]]
```

```python
[1, 2]      # selects List[int]
["a", "b"]  # selects List[str]
[1, "a"]    # matches neither, raise ValidationError
```

For dicts:

```python
Union[Dict[str, int], Dict[str, str]]
```

```python
{"x": 1}    # selects Dict[str, int]
{"x": "a"}  # selects Dict[str, str]
{"x": []}   # matches neither, raise ValidationError
```

## Ambiguity

Some assignments match more than one union member. Empty containers are the most
common case:

```python
Union[List[int], List[str]]
```

```python
[]  # valid as both List[int] and List[str]
```

Likewise:

```python
Union[Dict[str, int], Dict[str, str]]
```

```python
{}  # valid as both Dict[str, int] and Dict[str, str]
```

Silently choosing the first branch is simple, but it can commit the config to an
unexpected type. For example, if `[]` selects `List[int]`, then a later
`append("x")` fails even if the user intended `List[str]`.

This proposal recommends rejecting ambiguous assignments instead of silently
choosing a branch.

Example error:

```text
ValidationError: Ambiguous assignment to Union[List[int], List[str]].
Value [] matches multiple union members: List[int], List[str].
Use an explicitly typed list config to disambiguate.
```

## Explicit typed containers

If ambiguous assignments are rejected, users need a simple way to indicate the
intended container type at runtime.

A possible public API:

```python
OmegaConf.typed_list(content=None, element_type=Any)
OmegaConf.typed_dict(content=None, key_type=Any, element_type=Any)
```

Usage:

```python
cfg.value = OmegaConf.typed_list([], element_type=str)
cfg.value.append("hello")  # ok
cfg.value.append(123)      # ValidationError
```

```python
cfg.value = OmegaConf.typed_dict({}, key_type=str, element_type=int)
cfg.value["x"] = 10     # ok
cfg.value["y"] = "bad"  # ValidationError
```

The names are intentionally explicit. They avoid looking like replacements for
Python's built-in `list` and `dict` while making it clear that the returned
config carries runtime type metadata.

## Rejected alternative: first match wins

Do not select the first matching union member for ambiguous values, including
empty containers.

This would be simple and deterministic, and it would be consistent with trying
union candidates in annotation order. However, it would also make branch
selection depend on annotation order rather than value content.

For example:

```python
Union[List[int], List[str]]
```

```python
[]  # would silently select List[int]
```

The user may only discover the selected branch after a later mutation fails.
This is too implicit for OmegaConf's runtime validation model.

## Rejected alternative: deferred selection

Do not keep an empty container union unresolved until a future mutation provides
enough information:

```python
cfg.value = []
cfg.value.append("x")  # selects List[str]
```

This is attractive from a user-experience perspective, but it would introduce a
new "pending union container" state. List and dict operations would need to
participate in branch selection, and many existing assumptions about
`UnionNode` delegating to a concrete child node would become more complicated.

Union type selection must be unambiguous at assignment time.

## Proposed implementation

High-level implementation steps:

1. Extend `is_supported_union_annotation()` to allow `List[...]` and
   `Dict[...]` annotations as union members.
2. Update `UnionNode._set_value_impl()` so container values are tried against
   candidate union members instead of being rejected immediately.
3. Collect all candidates that successfully wrap and validate the assigned
   value.
4. If no candidate matches, raise `ValidationError`.
5. If exactly one candidate matches, store the wrapped child node.
6. If multiple candidates match, raise an ambiguity error.
7. Add `OmegaConf.typed_list()` and `OmegaConf.typed_dict()` or an equivalent
   explicit typed-container creation API.

The candidate check should use existing `_node_wrap()` behavior wherever
possible so list and dict validation stays centralized.

## Typed OmegaConf input

Assignment from an already typed `ListConfig` or `DictConfig` should be able to
disambiguate a union branch when its metadata matches exactly one candidate.

For example:

```python
typed = OmegaConf.typed_list([], element_type=str)
cfg.value = typed
```

For `Union[List[int], List[str]]`, this should select `List[str]`.

If a typed container still matches multiple candidates, assignment should remain
ambiguous and fail.

## Validation after selection

Once a branch is selected, the selected child node should behave like a normal
typed container.

Example:

```python
@dataclass
class Config:
    value: Union[List[int], List[str]]

cfg = OmegaConf.structured(Config)
cfg.value = [1]
cfg.value.append(2)    # ok
cfg.value.append("x")  # ValidationError
```

This is important because branch selection should not weaken type validation
after assignment.

## Interpolation considerations

Interpolations should continue to be accepted as special values without
immediate branch selection when the value cannot be resolved yet.

When an interpolation resolves, the resolved value should be validated against
the union annotation using the same candidate-selection and ambiguity rules.

Ambiguous resolved containers should fail with the same ambiguity error.

## Compatibility concerns

This is primarily an additive feature, but there are behavior changes to review:

- annotations that currently fail at structured-config creation would become
  valid
- assignments that currently fail immediately may become valid
- ambiguous assignments would fail with a new error message
- pickling/deepcopy behavior should be checked for `UnionNode` containing
  `ListConfig` or `DictConfig`
- `OmegaConf.to_container()` and `OmegaConf.to_object()` should preserve current
  pass-through behavior for selected union children

## Test plan

Focused tests should cover:

- `Union[int, List[str]]`
- `Union[int, Dict[str, int]]`
- `Union[List[int], List[str]]`
- `Union[Dict[str, int], Dict[str, str]]`
- non-empty list/dict branch selection
- empty list/dict ambiguity errors
- assignment from explicitly typed empty containers
- validation after branch selection
- merge behavior
- interpolation resolution into a container union
- `OmegaConf.to_container()` and `OmegaConf.to_object()`
- deepcopy and pickle round trips

## Recommended scope

The first implementation should support only `List[...]` and `Dict[...]` union
members.

Structured config unions and `Literal[...]` support should remain separate
features. They may reuse some lower-level candidate-selection machinery, but
they need their own user-facing semantics.
