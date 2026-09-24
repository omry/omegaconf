import warnings
from dataclasses import dataclass, field
from enum import Enum
from typing import Union

from pytest import raises, warns

from omegaconf import MISSING, OmegaConf, ValidationError


@dataclass
class Child:
    value: int = 1


@dataclass
class Config:
    number: int = 1
    values_list: list[int] = field(default_factory=list)
    values_map: dict[str, int] = field(default_factory=dict)
    child: Child = field(default_factory=Child)


class Color(Enum):
    RED = 1


@dataclass
class OtherValues:
    floating: float = 0.0
    enabled: bool = False
    text: str = ""
    color: Color = Color.RED


@dataclass
class Sequences:
    fixed: tuple[int, str] = (1, "a")
    variable: list[int] = field(default_factory=list)


@dataclass
class UnionDog:
    breed: str = "Lab"


@dataclass
class UnionCat:
    lives: int = 9


@dataclass
class UnionConfig:
    pet: Union[UnionDog, UnionCat] = field(default_factory=UnionDog)


def test_direct_assignment_warns_only_when_value_is_coerced() -> None:
    cfg = OmegaConf.structured(Config)
    with warns(FutureWarning, match="Implicit conversion from str to int") as record:
        cfg.number = "2"
    assert record[0].filename == __file__
    assert cfg.number == 2

    with warns(FutureWarning, match="Implicit conversion from str to int"):
        cfg["number"] = "3"
    assert cfg.number == 3

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        cfg.number = 4
        cfg.child = Child(value="5")  # type: ignore[arg-type]
        cfg.child = Child
    assert cfg.child.value == 1


def test_typed_container_mutations_warn_when_elements_are_coerced() -> None:
    cfg = OmegaConf.structured(Config)
    with warns(FutureWarning, match="values_list\\[0\\]"):
        cfg.values_list.append("1")
    with warns(FutureWarning, match="values_list\\[0\\]"):
        cfg.values_list[0] = "2"
    with warns(FutureWarning, match="values_list\\[0\\]"):
        cfg.values_list.insert(0, "3")
    with warns(FutureWarning, match="values_list\\[2\\]"):
        cfg.values_list.extend(["4"])
    with warns(FutureWarning, match="values_map\\.key"):
        cfg.values_map["key"] = "5"
    assert cfg.values_list == [3, 2, 4]
    assert cfg.values_map.key == 5


def test_typed_container_replacement_warns_for_coerced_elements() -> None:
    cfg = OmegaConf.structured(Config)
    with warns(FutureWarning, match="values_list\\[0\\]"):
        cfg.values_list = ["1"]  # type: ignore[list-item]
    with warns(FutureWarning, match="values_map\\.key"):
        cfg.values_map = {"key": "2"}  # type: ignore[dict-item]
    assert cfg.values_list == [1]
    assert cfg.values_map["key"] == 2


def test_union_mapping_assignment_warns_for_nested_coercion() -> None:
    cfg = OmegaConf.structured(UnionConfig)

    with warns(FutureWarning, match="Implicit conversion from int to str"):
        cfg.pet = {"breed": 123}

    assert cfg.pet["breed"] == "123"


def test_sequence_shape_conversion_warns_on_assignment_only() -> None:
    cfg = OmegaConf.structured(Sequences)
    with warns(FutureWarning, match="Implicit conversion from list to tuple") as record:
        cfg.fixed = [2, "b"]  # type: ignore[assignment]
    assert record[0].filename == __file__
    with warns(FutureWarning, match="Implicit conversion from tuple to list"):
        cfg.variable = (3,)  # type: ignore[assignment]
    assert cfg.fixed == (2, "b")
    assert cfg.variable == [3]

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        OmegaConf.structured(Sequences)
        OmegaConf.update(cfg, "fixed", [4, "c"])
        OmegaConf.update(cfg, "variable", (5,))
        cfg.fixed = (6, "d")
        cfg.variable = [7]

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with raises(FutureWarning):
            cfg.fixed = [8, "e"]  # type: ignore[assignment]
        with raises(FutureWarning):
            cfg.variable = (9,)  # type: ignore[assignment]
    assert cfg.fixed == (6, "d")
    assert cfg.variable == [7]


def test_other_scalar_conversions_warn() -> None:
    cfg = OmegaConf.structured(OtherValues)
    with warns(FutureWarning, match="Implicit conversion from int to float"):
        cfg.floating = 2
    with warns(FutureWarning, match="Implicit conversion from str to bool"):
        cfg.enabled = "true"
    with warns(FutureWarning, match="Implicit conversion from int to str"):
        cfg.text = 3
    with warns(FutureWarning, match="Implicit conversion from str to Color"):
        cfg.color = "RED"
    assert (cfg.floating, cfg.enabled, cfg.text, cfg.color) == (
        2.0,
        True,
        "3",
        Color.RED,
    )


def test_explicit_conversion_and_construction_do_not_warn() -> None:
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        cfg = OmegaConf.structured(Config(number="1"))  # type: ignore[arg-type]
        OmegaConf.update(cfg, "number", "2")
        cfg.merge_with({"number": "3"})
        cfg.values_list.append(4)
        OmegaConf.update(cfg, "values_list[0]", "5")
        cfg.values_map["key"] = 5
        cfg.number = "${values_map.key}"
        assert cfg.number == 5


def test_failed_conversion_does_not_warn() -> None:
    cfg = OmegaConf.structured(Config)
    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with raises(ValidationError):
            cfg.number = "invalid"
    assert cfg.number == 1


def test_warning_as_error_preserves_container_flags() -> None:
    cfg = OmegaConf.structured(Config)
    OmegaConf.set_struct(cfg.values_list, True)
    OmegaConf.set_struct(cfg.values_map, True)

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with raises(FutureWarning):
            cfg.values_list = OmegaConf.typed_tuple((1,), tuple[int, ...])  # type: ignore[assignment]
        with raises(FutureWarning):
            cfg.values_map = OmegaConf.create({"key": "2"})

    assert cfg.values_list == []
    assert cfg.values_map == {}
    assert OmegaConf.is_struct(cfg.values_list) is True
    assert OmegaConf.is_struct(cfg.values_map) is True


def test_warning_as_error_preserves_missing_tuple_type() -> None:
    cfg = OmegaConf.structured(Sequences)
    cfg.fixed = MISSING
    node = cfg._get_node("fixed")
    assert node is not None
    assert node._metadata.object_type is None

    with warnings.catch_warnings():
        warnings.simplefilter("error", FutureWarning)
        with raises(FutureWarning):
            cfg.fixed = [2, "b"]  # type: ignore[assignment]

    assert OmegaConf.is_missing(cfg, "fixed")
    assert node._metadata.object_type is None
