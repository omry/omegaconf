---
status: Active
updated: 2026-07-20
summary: Runtime validation and staged enforcement of custom-resolver annotations.
---

# Resolver Annotation Validation

Tracking issue: [issue #612](https://github.com/omry/omegaconf/issues/612)

## Summary

OmegaConf will optionally validate custom-resolver arguments and return values
against the resolver's parameter and return annotations. Validation defaults to
advisory in 2.4 and enforced in 2.5; both modes remain available explicitly.

Validation observes the actual values passed to and returned by the resolver.
It never coerces values and remains separate from validation and conversion of
resolver results by the interpolation's target node.

## Problem

`OmegaConf.register_resolver()` already inspects resolver signatures to detect
the special `_parent_`, `_node_`, and `_root_` parameters, but ordinary
annotations have no runtime effect. For example, a parameter annotated as
`int` may currently receive a quoted string, a boolean, or a list, and a
resolver annotated to return `int` may return another type unchecked.

Type checkers can detect many return mismatches in statically analyzable
resolver implementations. Runtime validation also covers dynamically registered
or untyped callables and resolver composition expressed in configuration, such
as `${outer:${inner:}}`. Because mismatches can originate in either composed
configuration or resolver Python code, advisory validation remains useful
beyond the default transition.

The proposal follows Hydra's typed grammar-function registry, with a staged
rollout because OmegaConf resolvers are a public extension point.

## Public interface and rollout

Add a keyword-only
`annotation_validation: Literal["off", "warn", "error"]` parameter to
`OmegaConf.register_resolver()`. `"off"` disables validation, `"warn"` emits
`UserWarning` on a mismatch and continues with the original argument or result,
and `"error"` raises `TypeError`. Registration errors expose that `TypeError`
directly. A mismatch during interpolation resolution is exposed to callers as
an `InterpolationResolutionError` caused by the `TypeError`. The default is
`"warn"` in 2.4 and `"error"` in 2.5; explicit modes behave identically in
both releases. Other values are invalid.

## Validation model

Unannotated parameters, an absent return annotation, and `Any` are skipped.
`_parent_`, `_node_`, and `_root_` are supplied by OmegaConf and excluded from
parameter validation.

At resolution time:

1. Evaluate argument interpolations through the existing grammar machinery,
   producing the values passed to the resolver.
2. Bind them to the signature, apply omitted parameter defaults, and validate
   annotated ordinary and variadic parameters.
3. Apply the configured policy to an argument mismatch.
4. Consult the resolver cache, then invoke the resolver on a cache miss.
5. Validate the cached or newly computed result against the return annotation.
6. Apply the configured policy to a return mismatch, cache a newly computed
   result, and return it unchanged.

Argument validation precedes cache lookup. Return validation applies to both
newly computed and cached results, so a cache populated before resolver
replacement cannot bypass the current resolver's annotation. A cached-result
mismatch explicitly identifies the cache as the value's source. In `"error"`
mode, the resolver is not invoked and the cache remains unchanged. The caller
can clear the config's entire resolver cache with `OmegaConf.clear_cache(cfg)`;
there is no dedicated public operation for clearing one resolver or cache
entry. In `"error"` mode, a mismatched new result is not cached. Validation
never converts values. Primitive matching is strict (`bool` does not satisfy
`int`). Initial container validation is shallow: parameterized containers check
their outer runtime kind without traversing or resolving elements. Abstract
collection annotations follow their runtime ABC relationships.

In `"error"` mode, an uninspectable callable or unresolvable parameter or
return annotation is a registration error because validation cannot be
guaranteed. `"warn"` emits `UserWarning` at registration and permits the
callable; `"off"` permits it without inspection.

## Interpolation interactions

Parameter validation applies to the actual value the resolver receives after
argument interpolations have been evaluated. Existing distinctions remain
observable:

| Resolver argument expression | Runtime value presented for validation |
| --- | --- |
| `${resolver:${integer}}` | `int` |
| `${resolver:"${integer}"}` | `str` |
| `${resolver:value-${integer}}` | `str` |
| `${resolver:[1, 2]}` | native `list` |
| `${resolver:${list_node}}` | `ListConfig` |
| `${resolver:${tuple_node}}` | `TupleConfig` |
| `${resolver:${returns_list:}}` | the inner resolver's native `list` |

Nested resolvers validate independently from the inside out. The inner
resolver's arguments are validated first, followed by its return value; only
then is the result presented for validation as an argument to the outer
resolver. This covers resolver composition embedded in configuration, which
type checkers cannot analyze.

OmegaConf containers remain distinct from native containers, and validation
uses the actual runtime type without treating the paired types as
interchangeable. Resolver authors should annotate the precise representation
they expect. A resolver that intentionally supports both can declare that with
`DictConfig | dict`, `ListConfig | list`, `TupleConfig | tuple`, or an
appropriate abstract collection annotation. Quoting or concatenating an
interpolation produces a string before validation. Failed argument
interpolation prevents validation and resolver invocation.

Resolver results still pass through the target node's existing validation and
conversion after return-annotation validation. Return validation enforces the
resolver's declared contract without converting its result; it neither uses nor
replaces the target type. For a nested resolver, this check occurs before the
result is passed to the outer resolver, independently of whether the outer
parameter is annotated.

Missing arguments currently fail before the resolver is called. Any future
resolver opt-in for receiving missing values must run its missing-value policy
before ordinary annotation validation and define how the missing sentinel can
be accepted. This remains coordinated with
[issue #1301](https://github.com/omry/omegaconf/issues/1301) and
[issue #1302](https://github.com/omry/omegaconf/issues/1302).

## Diagnostics

Warnings and `TypeError` messages identify the resolver, parameter (and
variadic index), expected annotation, actual type, and full key. Return
diagnostics identify the resolver, return annotation, actual result type, and
full key. When a return value came from the resolver cache, the diagnostic says
so explicitly and directs the caller to `OmegaConf.clear_cache(cfg)` when the
cache is stale. In `"warn"` mode, parameter mismatches still call the resolver
with the original argument and return mismatches expose the original result.

## Test plan

- Cover `"off"`, `"warn"`, `"error"`, omitted, and invalid registration values
  under both release defaults.
- Verify explicit `"warn"` remains advisory in 2.5.
- Cover annotated, unannotated, `Any`, optional, union, variadic, and shallow
  container parameters.
- Verify omitted annotated parameters are validated against their defaults.
- Cover annotated, unannotated, `Any`, optional, union, and shallow container
  return values.
- Verify exact primitive matching, including the `bool`/`int` distinction.
- Verify diagnostics contain resolver, parameter, annotation, actual type, and
  full key.
- Verify return diagnostics contain resolver, return annotation, actual result
  type, and full key.
- Verify bare, quoted, concatenated, node, container, and nested-resolver
  interpolation arguments.
- Verify an inner resolver's return value is validated before outer argument
  validation and invocation, including when the outer parameter is unannotated.
- Verify native containers remain distinct from OmegaConf containers and that
  `DictConfig | dict`, `ListConfig | list`, and `TupleConfig | tuple` accept
  their corresponding representations.
- Verify argument validation happens before resolver cache lookup and return
  validation applies to both cache misses and hits.
- Verify a cache-hit return mismatch identifies the cached source, does not
  invoke the resolver in `"error"` mode, and recommends clearing the config's
  resolver cache.
- Verify a return mismatch in `"error"` mode is not cached.
- Verify target-node validation of resolver outputs remains independent.
- Verify missing argument resolution prevents resolver invocation under the
  current contract.
- Verify uninspectable callables and unresolved parameter and return annotations
  follow the selected registration policy.
