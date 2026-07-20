import inspect
from collections.abc import Sequence
from dataclasses import dataclass
from functools import partial
from typing import Annotated, Any, Literal, Optional, Protocol, TypedDict, TypeVar

from pytest import mark, raises, warns

from omegaconf import DictConfig, ListConfig, OmegaConf, TupleConfig
from omegaconf.errors import InterpolationResolutionError


def test_invalid_annotation_validation_policy(restore_resolvers: Any) -> None:
    with raises(TypeError, match="annotation_validation"):
        OmegaConf.register_resolver(
            "typed",
            lambda: None,
            annotation_validation="invalid",  # type: ignore
        )


def test_annotation_validation_off(restore_resolvers: Any) -> None:
    def resolver(value: int) -> int:
        return value

    OmegaConf.register_resolver("typed", resolver, annotation_validation="off")
    cfg = OmegaConf.create({"value": '${typed:"not an int"}'})
    assert cfg.value == "not an int"


def test_unannotated_callable_object_does_not_warn(restore_resolvers: Any) -> None:
    class CallableResolver:
        __call__ = staticmethod(lambda value: value)

    OmegaConf.register_resolver("typed", CallableResolver())
    cfg = OmegaConf.create({"value": "${typed:10}"})
    assert cfg.value == 10


def test_callable_object_literal_is_not_treated_as_forward_reference(
    restore_resolvers: Any,
) -> None:
    class CallableResolver:
        def __call__(self, value: Literal["expected"]) -> str:
            return value

    OmegaConf.register_resolver("typed", CallableResolver())
    cfg = OmegaConf.create({"value": "${typed:expected}"})
    assert cfg.value == "expected"


def test_callable_object_forward_references_are_resolved(
    restore_resolvers: Any,
) -> None:
    class CallableResolver:
        def __call__(self, value: "int") -> "int":
            return value

    OmegaConf.register_resolver(
        "typed", CallableResolver(), annotation_validation="error"
    )
    cfg = OmegaConf.create({"value": "${typed:10}"})
    assert cfg.value == 10


def test_partial_forward_references_are_resolved(restore_resolvers: Any) -> None:
    def resolver(value: "int") -> "int":
        return value

    OmegaConf.register_resolver(
        "typed", partial(resolver), annotation_validation="error"
    )
    cfg = OmegaConf.create({"valid": "${typed:10}", "invalid": '${typed:"not an int"}'})
    assert cfg.valid == 10
    with raises(InterpolationResolutionError, match=r"expected int.*str"):
        _ = cfg.invalid


@mark.parametrize("policy", ["warn", None])
def test_annotation_validation_warns_and_preserves_argument(
    restore_resolvers: Any, policy: Optional[str]
) -> None:
    received = []

    def resolver(value: int) -> str:
        received.append(value)
        return str(value)

    kwargs = {} if policy is None else {"annotation_validation": policy}
    OmegaConf.register_resolver("typed", resolver, **kwargs)  # type: ignore[arg-type]
    cfg = OmegaConf.create({"nested": {"value": '${typed:"not an int"}'}})

    with warns(
        UserWarning,
        match=r"Resolver 'typed'.*parameter 'value'.*expected int.*str.*nested.value",
    ) as warning_records:
        assert cfg.nested.value == "not an int"
    assert warning_records[0].filename == __file__
    assert received == ["not an int"]


def test_annotation_validation_error_prevents_resolver_call(
    restore_resolvers: Any,
) -> None:
    received = []

    def resolver(value: int) -> int:
        received.append(value)
        return value

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"nested": {"value": '${typed:"not an int"}'}})

    with raises(
        InterpolationResolutionError,
        match=r"Resolver 'typed'.*parameter 'value'.*expected int.*str.*nested.value",
    ):
        _ = cfg.nested.value
    assert received == []


def test_annotation_validation_applies_parameter_defaults(
    restore_resolvers: Any,
) -> None:
    received = []
    default: Any = "not an int"

    def resolver(value: int = default) -> int:
        received.append(value)
        return value

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:}"})

    with raises(
        InterpolationResolutionError,
        match=r"parameter 'value'.*expected int.*str",
    ):
        _ = cfg.value
    assert received == []


def test_primitive_matching_is_exact(restore_resolvers: Any) -> None:
    def resolver(value: int) -> int:
        return value

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:true}"})

    with raises(InterpolationResolutionError, match=r"expected int.*bool"):
        _ = cfg.value


@mark.parametrize(
    ("annotation", "expression", "expected"),
    [
        (Optional[int], "null", None),
        (int | str, "text", "text"),
        (Annotated[int, "metadata"], "10", 10),
        (list[int], "[wrong, element, types]", ["wrong", "element", "types"]),
        (Sequence[int], "[wrong, element, types]", ["wrong", "element", "types"]),
    ],
)
def test_supported_annotations_and_shallow_container_validation(
    restore_resolvers: Any, annotation: Any, expression: str, expected: Any
) -> None:
    def resolver(value: Any) -> Any:
        return value

    resolver.__annotations__["value"] = annotation
    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": f"${{typed:{expression}}}"})
    assert cfg.value == expected


@mark.parametrize(
    ("expression", "annotation", "expected"),
    [
        ("${integer}", int, 10),
        ('"${integer}"', str, "10"),
        ("value-${integer}", str, "value-10"),
    ],
)
def test_interpolation_argument_forms(
    restore_resolvers: Any, expression: str, annotation: Any, expected: Any
) -> None:
    def resolver(value: Any) -> Any:
        return value

    resolver.__annotations__["value"] = annotation
    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"integer": 10, "value": f"${{typed:{expression}}}"})
    assert cfg.value == expected


def test_variadic_parameter_diagnostic_includes_index(
    restore_resolvers: Any,
) -> None:
    def resolver(*values: int) -> tuple[int, ...]:
        return values

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:1,two}"})

    with raises(InterpolationResolutionError, match=r"parameter 'values\[1\]'"):
        _ = cfg.value


@mark.parametrize(
    ("value", "annotation", "expected_type"),
    [
        ({"key": "value"}, DictConfig | dict, DictConfig),
        ([1, 2], ListConfig | list, ListConfig),
        ((1, 2), TupleConfig | tuple, TupleConfig),
    ],
)
def test_omegaconf_container_unions(
    restore_resolvers: Any, value: Any, annotation: Any, expected_type: type
) -> None:
    def resolver(container: Any) -> str:
        assert isinstance(container, expected_type)
        return type(container).__name__

    resolver.__annotations__["container"] = annotation
    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"container": value, "value": "${typed:${container}}"})
    assert cfg.value == expected_type.__name__


@mark.parametrize(
    ("value", "annotation", "expected_type"),
    [
        ({"key": "value"}, DictConfig | dict, dict),
        ([1, 2], ListConfig | list, list),
        ((1, 2), TupleConfig | tuple, tuple),
    ],
)
def test_native_container_unions(
    restore_resolvers: Any, value: Any, annotation: Any, expected_type: type
) -> None:
    def source() -> Any:
        return value

    def resolver(container: Any) -> str:
        assert type(container) is expected_type
        return type(container).__name__

    resolver.__annotations__["container"] = annotation
    OmegaConf.register_resolver("source", source, annotation_validation="error")
    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:${source:}}"})
    assert cfg.value == expected_type.__name__


def test_native_container_annotation_rejects_omegaconf_container(
    restore_resolvers: Any,
) -> None:
    def resolver(container: list) -> None:
        return None

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"container": [1, 2], "value": "${typed:${container}}"})

    with raises(InterpolationResolutionError, match=r"expected list.*ListConfig"):
        _ = cfg.value


def test_special_parameters_are_excluded(restore_resolvers: Any) -> None:
    def resolver(*, _node_: str) -> str:
        return type(_node_).__name__

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:}"})
    assert cfg.value == "AnyNode"


def test_return_annotation_warns_and_preserves_result(
    restore_resolvers: Any,
) -> None:
    def resolver() -> int:
        return "not an int"  # type: ignore[return-value]

    OmegaConf.register_resolver("typed", resolver, annotation_validation="warn")
    cfg = OmegaConf.create({"value": "${typed:}"})

    with warns(
        UserWarning,
        match=r"Resolver 'typed'.*return value.*expected int.*str.*value",
    ):
        assert cfg.value == "not an int"


@mark.parametrize(
    ("annotation", "result"),
    [
        (Optional[int], None),
        (int | str, "value"),
        (list[int], ["shallow", "validation"]),
    ],
)
def test_supported_return_annotations(
    restore_resolvers: Any, annotation: Any, result: Any
) -> None:
    def resolver() -> Any:
        return result

    resolver.__annotations__["return"] = annotation
    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${typed:}"})
    assert cfg.value == result


def test_nested_return_validation_precedes_outer_call(
    restore_resolvers: Any,
) -> None:
    calls = []

    def inner() -> int:
        calls.append("inner")
        return "not an int"  # type: ignore[return-value]

    def outer(value: Any) -> Any:
        calls.append("outer")
        return value

    OmegaConf.register_resolver("inner", inner, annotation_validation="error")
    OmegaConf.register_resolver("outer", outer, annotation_validation="error")
    cfg = OmegaConf.create({"value": "${outer:${inner:}}"})

    with raises(InterpolationResolutionError, match=r"Resolver 'inner'.*return value"):
        _ = cfg.value
    assert calls == ["inner"]


def test_missing_argument_prevents_resolver_call(restore_resolvers: Any) -> None:
    calls = 0

    def resolver(value: Any) -> Any:
        nonlocal calls
        calls += 1
        return value

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.create({"argument": "???", "value": "${typed:${argument}}"})

    with raises(InterpolationResolutionError):
        _ = cfg.value
    assert calls == 0


def test_return_mismatch_is_not_cached(restore_resolvers: Any) -> None:
    calls = 0

    def resolver() -> int:
        nonlocal calls
        calls += 1
        return "not an int"  # type: ignore[return-value]

    OmegaConf.register_resolver(
        "typed", resolver, use_cache=True, annotation_validation="error"
    )
    cfg = OmegaConf.create({"value": "${typed:}"})

    for _ in range(2):
        with raises(InterpolationResolutionError, match=r"return value"):
            _ = cfg.value
    assert calls == 2
    assert OmegaConf.get_cache(cfg)["typed"] == {}


def test_argument_validation_precedes_cache_hit(restore_resolvers: Any) -> None:
    calls = 0

    def resolver(value: int) -> int:
        nonlocal calls
        calls += 1
        return value

    OmegaConf.register_resolver(
        "typed", resolver, use_cache=True, annotation_validation="error"
    )
    cfg = OmegaConf.create({"argument": 10, "value": "${typed:${argument}}"})
    assert cfg.value == 10
    cfg.argument = "not an int"

    with raises(InterpolationResolutionError, match=r"parameter 'value'.*str"):
        _ = cfg.value
    assert calls == 1


def test_cached_return_mismatch_identifies_cache(
    restore_resolvers: Any,
) -> None:
    calls = 0

    def old_resolver() -> str:
        return "cached"

    def replacement() -> int:
        nonlocal calls
        calls += 1
        return 10

    OmegaConf.register_resolver(
        "typed", old_resolver, use_cache=True, annotation_validation="error"
    )
    cfg = OmegaConf.create({"value": "${typed:}"})
    assert cfg.value == "cached"

    OmegaConf.register_resolver(
        "typed",
        replacement,
        use_cache=True,
        replace=True,
        annotation_validation="error",
    )
    with raises(
        InterpolationResolutionError,
        match=r"cached return value.*expected int.*str.*OmegaConf.clear_cache",
    ):
        _ = cfg.value
    assert calls == 0

    OmegaConf.clear_cache(cfg)
    assert cfg.value == 10
    assert calls == 1


def test_target_node_validation_remains_independent(restore_resolvers: Any) -> None:
    @dataclass
    class Config:
        value: int = "${typed:}"  # type: ignore[assignment]

    def resolver() -> str:
        return "10"

    OmegaConf.register_resolver("typed", resolver, annotation_validation="error")
    cfg = OmegaConf.structured(Config)
    assert cfg.value == 10


@mark.parametrize("policy", ["warn", "error"])
def test_uninspectable_resolver_follows_policy(
    mocker: Any, restore_resolvers: Any, policy: str
) -> None:
    mocker.patch.object(inspect, "signature", side_effect=ValueError("no signature"))

    if policy == "warn":
        with warns(UserWarning, match=r"Resolver 'typed'.*cannot be inspected"):
            OmegaConf.register_resolver(
                "typed",
                lambda: 10,
                annotation_validation=policy,  # type: ignore[arg-type]
            )
    else:
        with raises(TypeError, match=r"Resolver 'typed'.*cannot be inspected"):
            OmegaConf.register_resolver(
                "typed",
                lambda: 10,
                annotation_validation=policy,  # type: ignore[arg-type]
            )


@mark.parametrize("policy", ["warn", "error"])
def test_unresolvable_annotation_follows_policy(
    restore_resolvers: Any, policy: str
) -> None:
    def resolver(value: "MissingType") -> Any:  # type: ignore[name-defined]  # noqa: F821
        return value

    if policy == "warn":
        with warns(UserWarning, match=r"Resolver 'typed'.*cannot resolve annotations"):
            OmegaConf.register_resolver(
                "typed",
                resolver,
                annotation_validation=policy,  # type: ignore[arg-type]
            )
    else:
        with raises(TypeError, match=r"Resolver 'typed'.*cannot resolve annotations"):
            OmegaConf.register_resolver(
                "typed",
                resolver,
                annotation_validation=policy,  # type: ignore[arg-type]
            )


class ResolverProtocol(Protocol):
    value: int


class ResolverTypedDict(TypedDict):
    value: int


ResolverTypeVar = TypeVar("ResolverTypeVar")


@mark.parametrize("annotation", [ResolverProtocol, ResolverTypedDict, ResolverTypeVar])
@mark.parametrize("policy", ["warn", "error"])
def test_runtime_uncheckable_annotation_follows_policy(
    restore_resolvers: Any, annotation: Any, policy: str
) -> None:
    def resolver(value: Any) -> Any:
        return value

    resolver.__annotations__["value"] = annotation
    if policy == "warn":
        with warns(UserWarning, match=r"cannot be checked at runtime"):
            OmegaConf.register_resolver(
                "typed",
                resolver,
                annotation_validation=policy,  # type: ignore[arg-type]
            )
        cfg = OmegaConf.create({"value": "${typed:10}"})
        assert cfg.value == 10
    else:
        with raises(TypeError, match=r"cannot be checked at runtime"):
            OmegaConf.register_resolver(
                "typed",
                resolver,
                annotation_validation=policy,  # type: ignore[arg-type]
            )
