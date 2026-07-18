import copy
import pickle
from collections.abc import MutableSequence, Sequence
from typing import Any, Optional, Tuple

from pytest import mark, param, raises

from omegaconf import MISSING, DictConfig, ListConfig, Node, OmegaConf, ValidationError
from omegaconf.errors import ConfigTypeError
from omegaconf.tupleconfig import TupleConfig


@mark.parametrize(
    "ref_type,content,expected",
    [
        param(Tuple[int, str], [1, 2], (1, "2"), id="typing_fixed"),
        param(tuple[int, str], (1, 2), (1, "2"), id="builtin_fixed"),
        param(Tuple[int, ...], ["1", 2], (1, 2), id="typing_variadic"),
        param(tuple[int, ...], ("1", 2), (1, 2), id="builtin_variadic"),
        param(tuple, [1, "x"], (1, "x"), id="bare_builtin"),
        param(Tuple, [1, "x"], (1, "x"), id="bare_typing"),
        param(tuple[()], [], (), id="empty_builtin"),
        param(Tuple[()], (), (), id="empty_typing"),
    ],
)
def test_supported_tuple_annotations(
    ref_type: Any, content: Any, expected: Tuple[Any, ...]
) -> None:
    cfg = TupleConfig(content, ref_type=ref_type)
    assert tuple(cfg) == expected


@mark.parametrize(
    "ref_type,content",
    [
        param(Tuple[int, str], [1], id="fixed_too_short"),
        param(Tuple[int, str], [1, "x", 3], id="fixed_too_long"),
        param(tuple[()], [1], id="empty_nonempty_content"),
    ],
)
def test_fixed_tuple_arity_is_validated(ref_type: Any, content: Any) -> None:
    with raises(ValidationError, match="length"):
        TupleConfig(content, ref_type=ref_type)


def test_direct_missing_element_is_rejected() -> None:
    with raises(ValidationError, match="cannot be missing"):
        TupleConfig([MISSING], ref_type=Tuple[int])


def test_nested_missing_is_allowed() -> None:
    cfg = TupleConfig([{"value": MISSING}], ref_type=Tuple[dict])
    child = cfg[0]
    assert isinstance(child, DictConfig)
    value = child._get_node("value")
    assert isinstance(value, Node)
    assert value._is_missing()


def test_whole_tuple_can_be_missing() -> None:
    cfg = TupleConfig(MISSING, ref_type=Tuple[int])
    assert cfg._is_missing()
    assert cfg._metadata.ref_type == Tuple[int]


@mark.parametrize(
    "ref_type,is_optional,content,raises_error",
    [
        param(Tuple[int], True, None, False, id="optional_none"),
        param(Tuple[int], False, None, True, id="required_none"),
    ],
)
def test_optional_tuple(
    ref_type: Any, is_optional: bool, content: Any, raises_error: bool
) -> None:
    if raises_error:
        with raises(ValidationError, match="Non optional"):
            TupleConfig(content, ref_type=ref_type, is_optional=is_optional)
    else:
        cfg = TupleConfig(content, ref_type=ref_type, is_optional=is_optional)
        assert cfg._is_none()


def test_tuple_is_sequence_but_not_mutable_sequence() -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int])
    assert isinstance(cfg, Sequence)
    assert not isinstance(cfg, MutableSequence)


@mark.parametrize(
    "operation",
    [
        param(lambda cfg: cfg.__setitem__(0, 2), id="setitem"),
        param(lambda cfg: cfg.__delitem__(0), id="delitem"),
        param(lambda cfg: cfg.append(2), id="append"),
        param(lambda cfg: cfg.extend([2]), id="extend"),
        param(lambda cfg: cfg.insert(0, 2), id="insert"),
        param(lambda cfg: cfg.pop(), id="pop"),
        param(lambda cfg: cfg.remove(1), id="remove"),
        param(lambda cfg: cfg.clear(), id="clear"),
        param(lambda cfg: cfg.sort(), id="sort"),
        param(lambda cfg: cfg.reverse(), id="reverse"),
    ],
)
def test_structural_mutation_is_rejected(operation: Any) -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int])
    with raises(ConfigTypeError, match="immutable"):
        operation(cfg)


def test_nested_container_remains_mutable() -> None:
    cfg = TupleConfig([[1]], ref_type=Tuple[list[int]])
    cfg[0].append(2)
    assert cfg == ([1, 2],)


def test_tuple_equality_and_hashing() -> None:
    cfg = TupleConfig([1, "x"], ref_type=Tuple[int, str])
    assert cfg == (1, "x")
    assert cfg != [1, "x"]
    with raises(TypeError, match="unhashable"):
        hash(cfg)


def test_tuple_repr_uses_tuple_syntax() -> None:
    cfg = OmegaConf.create({"value": (1, 2, 3)})

    assert repr(cfg.value) == "(1, 2, 3)"
    assert repr(cfg) == "{'value': (1, 2, 3)}"


def test_missing_and_none_tupleconfig_equality() -> None:
    assert TupleConfig(MISSING, ref_type=Tuple[int]) == TupleConfig(
        MISSING, ref_type=Tuple[int]
    )
    assert TupleConfig(None, ref_type=Tuple[int]) == TupleConfig(
        None, ref_type=Tuple[int]
    )


def test_index_matches_python_negative_bounds() -> None:
    cfg = TupleConfig([1, 2, 1], ref_type=Tuple[int, ...])

    assert cfg.index(1, -2) == 2
    assert cfg.index(1, 0, -1) == 0


def test_slice_preserves_fixed_annotation_and_copies_nodes() -> None:
    cfg = TupleConfig([1, "x", 2.5], ref_type=Tuple[int, str, float])
    result = cfg[1:]
    assert isinstance(result, TupleConfig)
    assert result == ("x", 2.5)
    assert result._metadata.ref_type == Tuple[str, float]
    result_node = result._get_node(0)
    source_node = cfg._get_node(1)
    assert isinstance(result_node, Node)
    assert isinstance(source_node, Node)
    assert result_node._get_parent() is result
    assert source_node._get_parent() is cfg


def test_slice_preserves_variadic_annotation() -> None:
    cfg = TupleConfig([1, 2, 3], ref_type=Tuple[int, ...])
    result = cfg[1:]
    assert result == (2, 3)
    assert result._metadata.ref_type == Tuple[int, ...]


def test_concatenation_derives_fixed_annotation_and_copies_nodes() -> None:
    left = TupleConfig([1, "x"], ref_type=Tuple[int, str])
    right = TupleConfig([2.5, 3.5], ref_type=Tuple[float, ...])

    result = left + right

    assert result == (1, "x", 2.5, 3.5)
    assert result._metadata.ref_type == Tuple[int, str, float, float]
    assert result._get_node(0) is not left._get_node(0)
    assert result._get_node(2) is not right._get_node(0)


def test_concatenation_with_native_tuple_uses_any_positional_types() -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int])

    right = cfg + ("x", 2.5)
    left = ("x", 2.5) + cfg

    assert right == (1, "x", 2.5)
    assert right._metadata.ref_type == Tuple[int, Any, Any]
    assert left == ("x", 2.5, 1)
    assert left._metadata.ref_type == Tuple[Any, Any, int]


@mark.parametrize(
    "other",
    [param([2], id="list"), param(ListConfig([2]), id="listconfig")],
)
def test_concatenation_rejects_lists(other: Any) -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int])

    with raises(TypeError, match="concatenate tuple"):
        cfg + other


def test_repetition_preserves_or_derives_annotation() -> None:
    fixed = TupleConfig([1, "x"], ref_type=Tuple[int, str])
    variadic = TupleConfig([1, 2], ref_type=Tuple[int, ...])

    fixed_result = fixed * 2
    variadic_result = 2 * variadic

    assert fixed_result == (1, "x", 1, "x")
    assert fixed_result._metadata.ref_type == Tuple[int, str, int, str]
    assert variadic_result == (1, 2, 1, 2)
    assert variadic_result._metadata.ref_type == Tuple[int, ...]


@mark.parametrize("count", [0, -1])
def test_nonpositive_repetition_returns_typed_empty_tuple(count: int) -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int, ...])

    result = cfg * count

    assert result == ()
    assert result._metadata.ref_type == Tuple[()]


def test_tuple_operators_keep_interpolations_lazy_and_reparented() -> None:
    parent = OmegaConf.create({"value": 10})
    cfg = TupleConfig(["${value}"], parent=parent, ref_type=Tuple[int])

    result = cfg + cfg

    first = result._get_node(0)
    assert isinstance(first, Node)
    assert first._is_interpolation()
    assert first._get_parent() is result
    assert result == (10, 10)
    assert first._is_interpolation()


def test_repetition_rejects_non_integer() -> None:
    cfg = TupleConfig([1], ref_type=Tuple[int])

    with raises(TypeError, match="non-int"):
        cfg * 1.5


def test_copy_deepcopy_and_pickle_preserve_type_and_metadata() -> None:
    cfg = TupleConfig([1, "x"], ref_type=Tuple[int, str])
    for result in (copy.copy(cfg), copy.deepcopy(cfg), pickle.loads(pickle.dumps(cfg))):
        assert isinstance(result, TupleConfig)
        assert result == (1, "x")
        assert result._metadata.ref_type == Tuple[int, str]


def test_optional_annotation_is_represented_by_metadata() -> None:
    cfg = TupleConfig(None, ref_type=Tuple[int], is_optional=True)
    assert cfg._metadata.type_hint == Optional[Tuple[int]]
