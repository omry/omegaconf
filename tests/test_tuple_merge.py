from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from pytest import mark, param, raises

from omegaconf import (
    DictConfig,
    ListConfig,
    ListMergeMode,
    OmegaConf,
    TupleConfig,
    ValidationError,
)
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


@mark.parametrize(
    "mode",
    [
        param(ListMergeMode.REPLACE, id="replace"),
        param(ListMergeMode.EXTEND, id="extend"),
        param(ListMergeMode.EXTEND_UNIQUE, id="extend_unique"),
    ],
)
def test_tuple_merge_ignores_list_merge_mode(mode: ListMergeMode) -> None:
    result = OmegaConf.merge((1, 2), (3,), list_merge_mode=mode)

    assert result == (3,)
