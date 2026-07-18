from dataclasses import dataclass, field
from types import GenericAlias
from typing import Any, List, NamedTuple, Optional, Tuple

import attr
from pytest import mark, param, raises
from typing_extensions import TypeVarTuple, Unpack

from omegaconf import MISSING, ListConfig, OmegaConf, TupleConfig, ValidationError


@dataclass
class TupleFields:
    fixed: Tuple[int, str] = (1, "x")
    variadic: Tuple[int, ...] = (1, 2)
    empty: Tuple[()] = ()
    bare: tuple = ()
    optional: Optional[Tuple[int, ...]] = None
    missing: Tuple[int, str] = MISSING
    numbers: List[int] = field(default_factory=list)


@attr.s(auto_attribs=True)
class AttrTupleFields:
    fixed: Tuple[int, str] = (1, "x")
    variadic: tuple[int, ...] = (1, 2)
    optional: Optional[Tuple[int, ...]] = None


class Point(NamedTuple):
    x: int
    y: int


def test_create_native_tuple_returns_tupleconfig() -> None:
    cfg = OmegaConf.create((1, "x"))
    assert isinstance(cfg, TupleConfig)
    assert cfg == (1, "x")
    assert cfg._metadata.ref_type == Tuple[Any, ...]
    assert OmegaConf.get_type(cfg) is tuple


def test_create_native_list_still_returns_listconfig() -> None:
    cfg = OmegaConf.create([1, "x"])
    assert isinstance(cfg, ListConfig)
    assert OmegaConf.get_type(cfg) is list


def test_namedtuple_keeps_existing_non_tupleconfig_behavior() -> None:
    cfg = OmegaConf.create(Point(1, 2))

    assert isinstance(cfg, ListConfig)
    assert not isinstance(cfg, TupleConfig)


def test_nested_native_tuple_preserves_identity() -> None:
    cfg = OmegaConf.create({"value": (1, 2)})
    assert isinstance(cfg.value, TupleConfig)
    assert cfg.value == (1, 2)


def test_public_predicates() -> None:
    tuple_cfg = OmegaConf.create((1,))
    list_cfg = OmegaConf.create([1])
    assert OmegaConf.is_tuple(tuple_cfg)
    assert not OmegaConf.is_list(tuple_cfg)
    assert OmegaConf.is_config(tuple_cfg)
    assert OmegaConf.is_sequence(tuple_cfg)
    assert OmegaConf.is_sequence(list_cfg)
    assert not OmegaConf.is_sequence((1,))
    assert not OmegaConf.is_sequence([1])


def test_typed_tuple_requires_content() -> None:
    with raises(TypeError, match="content"):
        OmegaConf.typed_tuple()  # type: ignore[call-arg]


def test_typed_tuple_rejects_none() -> None:
    with raises(ValidationError, match="Non optional"):
        OmegaConf.typed_tuple(None, Tuple[int])


@mark.parametrize(
    "tuple_type,content,expected",
    [
        param(Tuple[int, str], [1, 2], (1, "2"), id="typing_fixed_list"),
        param(tuple[int, str], (1, 2), (1, "2"), id="builtin_fixed_tuple"),
        param(Tuple[int, ...], ["1", 2], (1, 2), id="typing_variadic"),
        param(tuple[()], [], (), id="empty"),
    ],
)
def test_typed_tuple(tuple_type: Any, content: Any, expected: Any) -> None:
    cfg = OmegaConf.typed_tuple(content, tuple_type=tuple_type)
    assert isinstance(cfg, TupleConfig)
    assert cfg == expected
    assert cfg._metadata.ref_type == tuple_type


def test_typed_tuple_does_not_infer_positional_types() -> None:
    cfg = OmegaConf.typed_tuple([1, "x"])
    assert cfg._metadata.ref_type == Tuple[Any, ...]


def test_typed_tuple_rejects_non_tuple_annotation() -> None:
    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([1], tuple_type=List[int])


def test_typed_tuple_rejects_pep646_unpack() -> None:
    types = TypeVarTuple("types")

    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([], tuple_type=tuple[Unpack[types]])


def test_typed_tuple_rejects_misplaced_ellipsis() -> None:
    tuple_type = GenericAlias(tuple, (int, ..., str))

    with raises(ValidationError, match="Unsupported tuple type"):
        OmegaConf.typed_tuple([], tuple_type=tuple_type)


def test_dataclass_tuple_fields() -> None:
    cfg = OmegaConf.structured(TupleFields)
    assert isinstance(cfg.fixed, TupleConfig)
    assert isinstance(cfg.variadic, TupleConfig)
    assert isinstance(cfg.empty, TupleConfig)
    assert isinstance(cfg.bare, TupleConfig)
    assert cfg.fixed == (1, "x")
    assert cfg.variadic == (1, 2)
    assert cfg.empty == ()
    assert cfg.optional is None


def test_attrs_tuple_fields() -> None:
    cfg = OmegaConf.structured(AttrTupleFields)
    assert isinstance(cfg.fixed, TupleConfig)
    assert isinstance(cfg.variadic, TupleConfig)
    assert cfg.fixed == (1, "x")
    assert cfg.variadic == (1, 2)
    assert cfg.optional is None


def test_tuple_field_accepts_list_and_coerces_scalars() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.fixed = [2, 3]
    assert isinstance(cfg.fixed, TupleConfig)
    assert cfg.fixed == (2, "3")


def test_tuple_field_accepts_listconfig() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.fixed = OmegaConf.typed_list([2, 3], element_type=Any)
    assert isinstance(cfg.fixed, TupleConfig)
    assert cfg.fixed == (2, "3")


def test_list_field_accepts_tupleconfig() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.numbers = OmegaConf.typed_tuple([1, 2], Tuple[int, ...])
    assert isinstance(cfg.numbers, ListConfig)
    assert cfg.numbers == [1, 2]


def test_list_field_accepts_native_tuple() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.numbers = (1, 2)  # type: ignore[assignment]
    assert isinstance(cfg.numbers, ListConfig)
    assert cfg.numbers == [1, 2]


def test_tuple_field_rejects_wrong_arity_on_replacement() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="length"):
        cfg.fixed = [1]


def test_tuple_field_rejects_direct_missing_element() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="cannot be missing"):
        cfg.fixed = [1, MISSING]


def test_missing_whole_tuple_accepts_complete_replacement() -> None:
    cfg = OmegaConf.structured(TupleFields)
    assert OmegaConf.is_missing(cfg, "missing")
    cfg.missing = [2, 3]
    assert isinstance(cfg.missing, TupleConfig)
    assert cfg.missing == (2, "3")


def test_optional_tuple_accepts_complete_replacement_and_none() -> None:
    cfg = OmegaConf.structured(TupleFields)
    cfg.optional = [1, 2]
    assert isinstance(cfg.optional, TupleConfig)
    assert cfg.optional == (1, 2)
    cfg.optional = None
    assert cfg.optional is None


def test_non_optional_tuple_rejects_none() -> None:
    cfg = OmegaConf.structured(TupleFields)
    with raises(ValidationError, match="not Optional"):
        cfg.fixed = None  # type: ignore[assignment]
