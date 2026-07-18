---
status: Active
updated: 2026-07-18
summary: Current experimental TupleConfig semantics for immutable and positionally typed tuple values.
---

# TupleConfig Design

Tracking issue: [issue #392](https://github.com/omry/omegaconf/issues/392)

## Settled direction

- Add a public `TupleConfig`; tuples will not be represented by `ListConfig`.
- Preserve tuple identity and structural immutability.
- Support both `typing.Tuple[...]` and `tuple[...]` annotations.
- Support bare `tuple` / `typing.Tuple` and the empty-tuple annotation `tuple[()]`.
- Support heterogeneous fixed-length tuple annotations such as `Tuple[int, bool, float]`.
- Support homogeneous variadic tuple annotations such as `Tuple[int, ...]`.
- Treat tuples passed to `OmegaConf.create()` as `TupleConfig` values with reference type `Tuple[Any, ...]`.
- Keep `NamedTuple` and PEP 646 forms such as `tuple[*Ts]` out of scope for 2.4.
- Add `OmegaConf.typed_tuple(content, tuple_type=Tuple[Any, ...])`, with content required because a tuple cannot be populated later. Accept both `typing.Tuple[...]` and `tuple[...]` annotations and both list and tuple content; validate the resulting `TupleConfig` immediately without inferring positional types from values.
- Let the declared destination type control conversion: list or tuple input becomes `TupleConfig` for tuple-typed fields and `ListConfig` for list-typed fields.
- Require fixed-length tuple annotations to have exactly the declared arity.
- Validate tuple elements using the existing OmegaConf scalar conversion rules.
- Lazy whole-container interpolation access follows existing list and dictionary behavior and does not eagerly convert the result. Explicit ``OmegaConf.resolve()`` materializes and validates the result as a ``TupleConfig``.
- Reject all direct structural mutation of a `TupleConfig`; reading a slice is supported and returns a new `TupleConfig`.
- Raise `ConfigTypeError` for intrinsic tuple immutability violations.
- Keep nested containers mutable, matching Python tuple behavior.
- Keep tuple structure immutable independently of the `readonly` flag; `read_write()` and flag changes cannot unlock it.
- Reject indexed `OmegaConf.update()` into a tuple; it does not rebuild the tuple as a workaround around tuple type policy.
- Implement `collections.abc.Sequence`, but not `MutableSequence`.
- Add `OmegaConf.is_tuple()` and `OmegaConf.is_sequence()`. A `TupleConfig` is a config and a sequence but not a list; `is_sequence()` is true only for `ListConfig` and `TupleConfig`, not native Python lists or tuples.
- Follow Python tuple equality: compare equal to an equivalent tuple, but not to a list or `ListConfig`.
- Support indexing, iteration, slicing, concatenation, repetition, `count()`, and `index()`; operations that produce a sequence return a new `TupleConfig`.
- Keep `TupleConfig` unhashable as part of the general policy that live OmegaConf containers should not be dictionary keys or set members.
- Merge tuple values by complete replacement rather than positionally; list or tuple sources are converted according to the destination type.
- Reject public in-place merging of a root `TupleConfig`, including `TupleConfig.merge_with()` and `OmegaConf.unsafe_merge(tuple_cfg, ...)`, while preserving the internal path needed by normal merges and allowing mutable parents to replace tuple children.
- Replace tuples containing nested configs atomically rather than recursively merging their existing elements.
- Convert `TupleConfig` to Python tuples recursively in `OmegaConf.to_container()`, `OmegaConf.to_object()`, and structured-config instantiation.
- Serialize tuples as ordinary YAML sequences without a custom tuple tag; untyped YAML loading produces lists, while tuple-typed destinations restore tuple semantics.
- Preserve `TupleConfig` type and positional metadata through copy, deepcopy, pickle, and resolver caching.
- For the initial implementation, make custom resolver results follow existing dictionary/list behavior: lazy access returns the resolver's native container, while explicit `OmegaConf.resolve()` materializes it according to the destination type.
- Document `TupleConfig` semantics as experimental in 2.4 and explicitly invite user feedback; the semantics may evolve based on that feedback.
- Treat the change from `OmegaConf.create(tuple)` producing a mutable `ListConfig` to producing an immutable `TupleConfig` as an intentional 2.4 API change with no compatibility flag.
- Support tuple annotations in both dataclasses and attrs in the initial implementation.
- Defer `NamedTuple`, PEP 646 variadic generics, and custom YAML tuple tags from the initial implementation. Do not support direct per-element Hydra overrides: tuple fields are immutable by design, and users who need positional mutation should use lists unless a compelling tuple-specific use case emerges.
- Support tuple members in container unions. Prefer union branches matching the native list/tuple input kind, report ambiguity among multiple matching same-kind branches, and use typed container metadata to narrow candidates before content validation.
- Preserve tuple typing through sequence-producing operations: slices of values with homogeneous variadic annotations retain that annotation, slices of values with fixed-length heterogeneous annotations derive the selected positional types, and repetition repeats fixed positional type patterns while preserving homogeneous variadic annotations.
- Match Python tuple operands for concatenation and repetition, and preserve interpolation nodes lazily in the resulting `TupleConfig` rather than resolving them into value snapshots.
- Require explicit tuple-factory content, reject missing direct tuple elements, allow a missing whole tuple, and allow `None` only for an optional tuple type.

## 1. Supported tuple forms

1. Decision: the following annotations are in scope for 2.4:
   - `typing.Tuple[T1, T2]`
   - `tuple[T1, T2]`
   - `typing.Tuple[T, ...]` and `tuple[T, ...]`
   - bare `tuple` / `typing.Tuple`
   - the empty-tuple annotation `tuple[()]`

2. Decision: `NamedTuple` and PEP 646 forms such as `tuple[*Ts]` are explicitly out of scope.

3. Decision: `OmegaConf.create((1, 2))` produces a `TupleConfig` with reference type `Tuple[Any, ...]`, while an annotated tuple retains its positional type information.

4. Decision: add `OmegaConf.typed_tuple(content, tuple_type=Tuple[Any, ...])`. Unlike the mutable typed-container factories, content is required because a tuple cannot be populated later. The complete tuple annotation expresses either a fixed-length or variadic type.

## 2. Input conversion and validation

5. Decision: a tuple-typed field accepts list or tuple input and converts it to `TupleConfig`.

6. Decision: a list-typed field continues to accept list or tuple input and converts it to `ListConfig`.

7. Decision: a fixed-length tuple annotation requires exactly the declared arity at construction and replacement.

8. Decision: each tuple position uses the existing OmegaConf scalar conversion rules.

9. Decision: follow existing typed-container interpolation behavior. Lazy access does not eagerly convert or validate a whole-container result. An interpolation stored in a typed primitive tuple position uses normal scalar coercion. Explicit ``OmegaConf.resolve()`` is covered by decisions 28 and 29 and materializes and validates the complete tuple.

## 3. Immutability

10. Decision: all direct structural mutation fails, including item assignment, slice assignment, deletion, insertion, append, extend, sort, and in-place concatenation. Reading a slice is a read-only operation and returns a new `TupleConfig`.

11. Decision: intrinsic tuple immutability violations raise `ConfigTypeError`.

12. Decision: nested containers remain mutable, matching Python behavior where a tuple may contain a mutable value.

13. Decision: no. Tuple immutability is independent of the `readonly` flag, so `read_write()` and direct flag changes cannot unlock its structure.

14. Decision: reject `OmegaConf.update(cfg, "tuple_field.0", value)` like item assignment. Do not rebuild and replace the enclosing tuple as a workaround around tuple type policy.

## 4. Public API and Python behavior

15. Decision: `TupleConfig` implements `collections.abc.Sequence` but not `MutableSequence`.

16. Decision: add `OmegaConf.is_tuple()`, with `OmegaConf.is_list(tuple_cfg) == False` and `OmegaConf.is_config(tuple_cfg) == True`.

17. Decision: equality follows Python tuple behavior. A `TupleConfig` is equal to an equivalent Python tuple and unequal to an equivalent list or `ListConfig`.

18. Decision: support indexing, iteration, slicing, `+`, `*`, `count()`, and `index()`. Slicing, `+`, and `*` return new `TupleConfig` instances.

19. Decision: `TupleConfig` is unhashable, consistent with the general policy that live OmegaConf containers should not be dictionary keys or set members.

## 5. Merge behavior

20. Decision: the later tuple replaces the earlier tuple as one complete value; values with fixed-length tuple annotations are not merged position by position.

21. Decision: accept list and tuple sources and convert them according to the destination type for both typed and untyped merges.

22. Decision: normal merges support tuple replacement, but reject public in-place merging of a root `TupleConfig` through `TupleConfig.merge_with()` or `OmegaConf.unsafe_merge(tuple_cfg, ...)`. `merge_with` participates in normal merge paths, so the implementation must preserve an internal tuple-replacement path rather than blocking tuple handling generally. Tuples contained by mutable parents are replaced through the parent.

23. Decision: replace the tuple and its complete contents atomically; do not recursively merge its existing nested configs.

## 6. Conversion and serialization

24. Decision: `OmegaConf.to_container(tuple_cfg)` returns a Python tuple, including for nested tuple configs.

25. Decision: `OmegaConf.to_object()` and `SCMode.INSTANTIATE` preserve tuple values.

26. Decision: `to_yaml()` emits a normal sequence without a custom tuple tag. Untyped YAML loading returns a `ListConfig`, so untyped round trips lose tuple identity; tuple semantics are restored when data is loaded into a tuple-typed destination.

27. Decision: copy, deepcopy, pickle, and resolver caching preserve `TupleConfig` type and positional metadata.

## 7. Resolver and object behavior

28. Decision: for the initial implementation, a resolver returning a tuple follows existing dictionary/list behavior. Lazy access returns the native Python tuple rather than a `TupleConfig`; explicit `OmegaConf.resolve()` materializes it as a `TupleConfig`.

29. Decision: for the initial implementation, a resolver returning a list for a tuple-typed node follows existing typed dictionary/list behavior. Lazy access returns the native list without whole-container conversion; explicit `OmegaConf.resolve()` materializes and validates it as a `TupleConfig` according to the destination type.

30. Decision: treat stored `TupleConfig` nodes as first-class OmegaConf sequence containers for selection, indexed traversal, missing checks, resolution, and interpolation targets. Add `OmegaConf.is_sequence()` returning true for `ListConfig` and `TupleConfig` only, while keeping mutation-specific and list-only paths separate.

## 8. Compatibility and release scope

31. Decision: changing `OmegaConf.create((1, 2))` from a mutable `ListConfig` to an immutable `TupleConfig` is an intentional 2.4 API change with no compatibility flag.

32. Decision: existing APIs that explicitly request a list, such as `typed_list(..., content=(1, 2))`, continue converting tuple input to `ListConfig`. Add the corresponding `typed_tuple()` factory.

33. Decision: support tuple annotations in both dataclasses and attrs in the initial implementation.

34. Decision: defer `NamedTuple`, PEP 646 variadic generics, and custom YAML tuple tags. Do not support direct per-element Hydra overrides: tuple fields are immutable by design, and users who need positional mutation should use a list. Reconsider this only if a compelling use case specifically requires tuple identity. Tuple arithmetic remains in scope, and `TupleConfig` remains unhashable as previously decided.

## 9. Typed tuple factory

35. Decision: `typed_tuple()` accepts the complete tuple annotation through `tuple_type`, including both `typing.Tuple[int, str]` and `tuple[int, str]`, as well as variadic annotations such as `Tuple[int, ...]`.

36. Decision: accept both list and tuple content; the explicitly requested factory determines that the result is a `TupleConfig`.

37. Decision: when `tuple_type` is omitted, default to `Tuple[Any, ...]`; do not infer fixed positional types from the current values.

38. Decision: initialization always validates the resulting `TupleConfig`. Fixed-length tuple annotations enforce exact arity and positional types, while variadic tuple annotations validate every element against their element type.

## 10. Union behavior

39. Decision: support tuple annotations as union members, including unions of multiple tuple types and unions mixing list and tuple types.

40. Decision: when list and tuple branches are both compatible, prefer the branch matching the native input kind: a list prefers a list branch and a tuple prefers a tuple branch. If matching-kind branches fail validation, other compatible sequence branches may still be considered.

41. Decision: if multiple branches of the same kind match, raise an ambiguity error rather than selecting by union order. Use `typed_tuple()`, `typed_list()`, or other explicitly typed containers to disambiguate.

42. Decision: use an existing typed `TupleConfig`'s tuple-type metadata to narrow union candidates before content validation, following `typed_list()` and `typed_dict()`. This must disambiguate empty tuples when the metadata identifies a unique branch.

## 11. Slicing and tuple operators

43. Decision: preserve or derive the tuple annotation when slicing. A slice of a value annotated with a homogeneous variadic type such as `Tuple[int, ...]` remains `Tuple[int, ...]`. A slice of a value annotated with a fixed-length heterogeneous type such as `Tuple[int, str, float]` derives the corresponding fixed-length annotation; for example, `[1:]` produces `Tuple[str, float]`. An untyped `Tuple[Any, ...]` remains untyped.

44. Decision: concatenation matches Python operand rules. Accept native tuples and `TupleConfig` operands, and reject lists and `ListConfig` operands with `TypeError`. The result is a new `TupleConfig` with a fixed-length annotation formed by concatenating the operands' element annotations at their concrete lengths. Expand a variadic annotation's element type once per actual element; use `Any` for each position contributed by an untyped or native tuple operand.

45. Decision: repetition matches Python value behavior and preserves derived typing. A homogeneous variadic tuple annotation keeps its element type. A fixed-length heterogeneous tuple annotation repeats its positional type pattern the requested number of times. Zero or negative repetition produces the empty tuple type `Tuple[()]`.

46. Decision: slicing, concatenation, and repetition copy tuple nodes into a new `TupleConfig` without resolving interpolations. Interpolations remain lazy and are reparented into the resulting tuple.

## 12. Missing and optional values

47. Decision: `OmegaConf.typed_tuple()` requires an explicit `content` argument for every tuple annotation, including empty and variadic annotations. Omission is an API error; it does not create an empty or missing tuple.

48. Decision: reject `MISSING` as a direct tuple element during construction or replacement. An immutable tuple cannot later fill that position. This does not prohibit a present nested object from containing its own missing fields.

49. Decision: allow the complete tuple node to be `MISSING` while retaining its tuple annotation for validation of a later complete assignment.

50. Decision: allow the complete tuple node to be `None` only when its declared tuple type is optional; reject `None` for a non-optional tuple type.
