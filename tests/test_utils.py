from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Union

import attr
import pytest

from omegaconf import DictConfig, ListConfig, OmegaConf, _utils
from omegaconf.errors import KeyValidationError, ValidationError
from omegaconf.nodes import StringNode

from . import Color, IllegalType, Plugin, does_not_raise


@pytest.mark.parametrize(  # type: ignore
    "target_type, value, expectation",
    [
        # Any
        (Any, "foo", None),
        (Any, True, None),
        (Any, 1, None),
        (Any, 1.0, None),
        (Any, Color.RED, None),
        # int
        (int, "foo", ValidationError),
        (int, True, ValidationError),
        (int, 1, None),
        (int, 1.0, ValidationError),
        (int, Color.RED, ValidationError),
        # float
        (float, "foo", ValidationError),
        (float, True, ValidationError),
        (float, 1, None),
        (float, 1.0, None),
        (float, Color.RED, ValidationError),
        # bool
        (bool, "foo", ValidationError),
        (bool, True, None),
        (bool, 1, None),
        (bool, 0, None),
        (bool, 1.0, ValidationError),
        (bool, Color.RED, ValidationError),
        (bool, "true", None),
        (bool, "false", None),
        (bool, "on", None),
        (bool, "off", None),
        # str
        (str, "foo", None),
        (str, True, None),
        (str, 1, None),
        (str, 1.0, None),
        (str, Color.RED, None),
        # Color
        (Color, "foo", ValidationError),
        (Color, True, ValidationError),
        (Color, 1, None),
        (Color, 1.0, ValidationError),
        (Color, Color.RED, None),
        (Color, "RED", None),
        (Color, "Color.RED", None),
        # bad type
        (IllegalType, "nope", ValidationError),
    ],
)
def test_maybe_wrap(target_type: type, value: Any, expectation: Any) -> None:
    from omegaconf.omegaconf import _maybe_wrap

    if expectation is None:
        _maybe_wrap(
            ref_type=target_type, key=None, value=value, is_optional=False, parent=None,
        )
    else:
        with pytest.raises(expectation):
            _maybe_wrap(
                ref_type=target_type,
                key=None,
                value=value,
                is_optional=False,
                parent=None,
            )


class _TestEnum(Enum):
    A = 1
    B = 2


@dataclass
class _TestDataclass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = field(default_factory=list)
    dict1: Dict[str, int] = field(default_factory=dict)


@attr.s(auto_attribs=True)
class _TestAttrsClass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = []
    dict1: Dict[str, int] = {}


class _TestUserClass:
    pass


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (int, True),
        (float, True),
        (bool, True),
        (str, True),
        (Any, True),
        (_TestEnum, True),
        (_TestUserClass, False),
        # Nesting structured configs in contain
        (_TestAttrsClass, True),
        (_TestDataclass, True),
    ],
)
def test_valid_value_annotation_type(type_: type, expected: bool) -> None:
    from omegaconf._utils import valid_value_annotation_type

    assert valid_value_annotation_type(type_) == expected


@pytest.mark.parametrize(  # type: ignore
    "test_cls_or_obj, expectation",
    [
        (_TestDataclass, does_not_raise()),
        (_TestDataclass(), does_not_raise()),
        (_TestAttrsClass, does_not_raise()),
        (_TestAttrsClass(), does_not_raise()),
        ("invalid", pytest.raises(ValueError)),
    ],
)
def test_get_structured_config_data(test_cls_or_obj: Any, expectation: Any) -> None:
    with expectation:
        d = _utils.get_structured_config_data(test_cls_or_obj)
        assert d["x"] == 10
        assert d["s"] == "foo"
        assert d["b"] == bool(True)
        assert d["f"] == 3.14
        assert d["e"] == _TestEnum.A
        assert d["list1"] == []
        assert d["dict1"] == {}


def test_is_dataclass(mocker: Any) -> None:
    @dataclass
    class Foo:
        pass

    assert _utils.is_dataclass(Foo)
    assert _utils.is_dataclass(Foo())
    assert not _utils.is_dataclass(10)

    mocker.patch("omegaconf._utils.dataclasses", None)
    assert not _utils.is_dataclass(10)


def test_is_attr_class(mocker: Any) -> None:
    @attr.s
    class Foo:
        pass

    assert _utils.is_attr_class(Foo)
    assert _utils.is_attr_class(Foo())

    assert not _utils.is_attr_class(10)
    mocker.patch("omegaconf._utils.attr", None)
    assert not _utils.is_attr_class(10)


def test_is_structured_config_frozen_with_invalid_obj() -> None:
    assert not _utils.is_structured_config_frozen(10)


@dataclass
class Dataclass:
    pass


@pytest.mark.parametrize(  # type: ignore
    "value,kind",
    [
        ("foo", _utils.ValueKind.VALUE),
        (1, _utils.ValueKind.VALUE),
        (1.0, _utils.ValueKind.VALUE),
        (True, _utils.ValueKind.VALUE),
        (False, _utils.ValueKind.VALUE),
        (Color.GREEN, _utils.ValueKind.VALUE),
        (Dataclass, _utils.ValueKind.VALUE),
        ("???", _utils.ValueKind.MANDATORY_MISSING),
        ("${foo.bar}", _utils.ValueKind.INTERPOLATION),
        ("ftp://${host}/path", _utils.ValueKind.STR_INTERPOLATION),
    ],
)
def test_value_kind(value: Any, kind: _utils.ValueKind) -> None:
    assert _utils.get_value_kind(value) == kind


def test_re_parent() -> None:
    def validate(cfg1: DictConfig) -> None:
        assert cfg1._get_parent() is None
        assert cfg1._get_node("str")._get_parent() == cfg1  # type:ignore
        assert cfg1._get_node("list")._get_parent() == cfg1  # type:ignore
        assert cfg1.list._get_node(0)._get_parent() == cfg1.list

    cfg = OmegaConf.create({})
    assert isinstance(cfg, DictConfig)
    cfg.str = StringNode("str")
    cfg.list = [1]

    validate(cfg)

    cfg._get_node("str")._set_parent(None)  # type:ignore
    cfg._get_node("list")._set_parent(None)  # type:ignore
    cfg.list._get_node(0)._set_parent(None)  # type: ignore
    # noinspection PyProtectedMember
    cfg._re_parent()
    validate(cfg)


def test_get_class() -> None:
    name = "tests.examples.test_dataclass_example.SimpleTypes"
    assert _utils._get_class(name).__name__ == "SimpleTypes"
    with pytest.raises(ValueError):
        _utils._get_class("not_found")

    with pytest.raises(ModuleNotFoundError):
        _utils._get_class("foo.not_found")

    with pytest.raises(ImportError):
        _utils._get_class("tests.examples.test_dataclass_example.not_found")


@pytest.mark.parametrize(  # type: ignore
    "key_type,expected_key_type",
    [
        (int, KeyValidationError),
        (str, str),
        (Color, Color),
        (Any, None),
        (None, KeyValidationError),
    ],
)
@pytest.mark.parametrize(  # type: ignore
    "value_type,expected_value_type",
    [(int, int), (str, str), (Color, Color), (Any, None), (None, type(None))],
)
def test_get_key_value_types(
    key_type: Any, expected_key_type: Any, value_type: Any, expected_value_type: Any,
) -> None:
    dt = Dict[key_type, value_type]  # type: ignore
    if expected_key_type is not None and issubclass(expected_key_type, Exception):
        with pytest.raises(expected_key_type):
            _utils.get_dict_key_value_types(dt)

    else:
        assert _utils.get_dict_key_value_types(dt) == (
            expected_key_type,
            expected_value_type,
        )


@pytest.mark.parametrize(  # type: ignore
    "type_, is_primitive",
    [
        (int, True),
        (float, True),
        (bool, True),
        (str, True),
        (type(None), True),
        (Color, True),
        (list, False),
        (ListConfig, False),
        (dict, False),
        (DictConfig, False),
    ],
)
def test_is_primitive_type(type_: Any, is_primitive: bool) -> None:
    assert _utils.is_primitive_type(type_) == is_primitive


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (int, "int"),
        (bool, "bool"),
        (float, "float"),
        (str, "str"),
        (Color, "Color"),
        (DictConfig, "DictConfig"),
        (ListConfig, "ListConfig"),
        (Dict[str, str], "Dict[str, str]"),
        (Dict[Color, int], "Dict[Color, int]"),
        (Dict[str, Plugin], "Dict[str, Plugin]"),
        (Dict[str, List[Plugin]], "Dict[str, List[Plugin]]"),
        (List[str], "List[str]"),
        (List[Color], "List[Color]"),
        (List[Dict[str, Color]], "List[Dict[str, Color]]"),
        (Union[str, int, Color], "Union[str, int, Color]"),
    ],
)
def test_type_str(type_: Any, expected: str) -> None:
    assert _utils.type_str(type_) == expected
