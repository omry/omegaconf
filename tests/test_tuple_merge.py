from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pytest import mark, raises

from omegaconf import (
    DictConfig,
    ListConfig,
    OmegaConf,
    TupleConfig,
    ValidationError,
)
from omegaconf.basecontainer import _deep_update_type_hint
from omegaconf.errors import ConfigTypeError


@dataclass
class TupleHolder:
    value: Tuple[Dict[str, int], ...] = ({"old": 1},)


@dataclass
class SequenceHolder:
    tuple_value: Tuple[int, str] = (1, "x")
    list_value: List[int] = field(default_factory=list)


@dataclass
class OptionalFixedTupleHolder:
    value: Optional[Tuple[int, str]] = None


def test_merge_root_tuple_replaces_complete_value() -> None:
    result = OmegaConf.merge((1, 2), (3, 4))

    assert isinstance(result, TupleConfig)
    assert result == (3, 4)


def test_merge_typed_root_tuple_accepts_list_and_validates() -> None:
    target = OmegaConf.typed_tuple((1, "x"), Tuple[int, str])

    result = OmegaConf.merge(target, [2, 3])
    assert isinstance(result, TupleConfig)
    assert result == (2, "3")

    with raises(ValidationError, match="length"):
        OmegaConf.merge(target, [1])


def test_public_in_place_root_tuple_merge_is_rejected() -> None:
    cfg = OmegaConf.create((1, 2))
    assert isinstance(cfg, TupleConfig)

    with raises(ConfigTypeError, match="in-place"):
        cfg.merge_with((3, 4))


def test_unsafe_merge_root_tuple_is_rejected() -> None:
    cfg = OmegaConf.create((1, 2))

    with raises(ConfigTypeError, match="unsafe_merge"):
        OmegaConf.unsafe_merge(cfg, (3, 4))


def test_nested_tuple_is_replaced_atomically() -> None:
    target = OmegaConf.structured(TupleHolder)

    result = OmegaConf.merge(target, {"value": ({"new": 2},)})

    assert result.value == ({"new": 2},)
    assert "old" not in result.value[0]


def test_mutable_parent_merge_with_replaces_tuple_child() -> None:
    cfg = OmegaConf.structured(TupleHolder)

    cfg.merge_with({"value": ({"new": 2},)})

    assert cfg.value == ({"new": 2},)


def test_merge_preserves_whole_tuple_interpolation(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver("tuple_value", lambda: (2, "y"))
    target = OmegaConf.structured(SequenceHolder)
    source = OmegaConf.structured(SequenceHolder)
    source.tuple_value = "${tuple_value:}"  # type: ignore[assignment]

    result = OmegaConf.merge(target, source)
    assert isinstance(result, DictConfig)
    node = result._get_node("tuple_value")

    assert isinstance(node, TupleConfig)
    assert node._is_interpolation()
    assert node._value() == "${tuple_value:}"
    assert result.tuple_value == (2, "y")


def test_merge_replaces_optional_fixed_tuple_from_none() -> None:
    cfg = OmegaConf.structured(OptionalFixedTupleHolder)

    result = OmegaConf.merge(cfg, {"value": [2, 3]})

    assert result.value == (2, "3")


def test_merge_source_sequence_converts_to_destination_kind() -> None:
    cfg = OmegaConf.structured(SequenceHolder)

    result = OmegaConf.merge(cfg, {"tuple_value": [2, 3], "list_value": (4, 5)})

    assert isinstance(result.tuple_value, TupleConfig)
    assert result.tuple_value == (2, "3")
    assert isinstance(result.list_value, ListConfig)
    assert result.list_value == [4, 5]


@mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
def test_nested_tuple_merge_rejects_dict_source(merge: Any) -> None:
    with raises(TypeError, match="Cannot merge incompatible container types"):
        merge({"value": (1,)}, {"value": {"key": 1}})


def test_tuple_merge_copies_explicit_source_flags() -> None:
    source = OmegaConf.create((2, 3))
    OmegaConf.set_readonly(source, True)

    result = OmegaConf.merge((1,), source)

    assert result == (2, 3)
    assert OmegaConf.is_readonly(result)


def test_deep_update_tuple_type_hint() -> None:
    cfg = OmegaConf.create((1, "x"))
    assert isinstance(cfg, TupleConfig)

    _deep_update_type_hint(cfg, Tuple[int, str])

    assert cfg._metadata.ref_type == Tuple[int, str]
    assert cfg._get_node(0)._metadata.ref_type is int  # type: ignore[union-attr]
    assert cfg._get_node(1)._metadata.ref_type is str  # type: ignore[union-attr]


def test_deep_update_variadic_tuple_type_hint() -> None:
    cfg = OmegaConf.create((1, 2))
    assert isinstance(cfg, TupleConfig)

    _deep_update_type_hint(cfg, Tuple[int, ...])

    assert cfg._metadata.ref_type == Tuple[int, ...]
    assert cfg._get_node(0)._metadata.ref_type is int  # type: ignore[union-attr]
    assert cfg._get_node(1)._metadata.ref_type is int  # type: ignore[union-attr]


def test_deep_update_fixed_tuple_rejects_wrong_arity() -> None:
    cfg = OmegaConf.create((1,))
    assert isinstance(cfg, TupleConfig)

    with raises(ValidationError, match="length"):
        _deep_update_type_hint(cfg, Tuple[int, str])
