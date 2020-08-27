from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import attr
import pytest

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, _utils
from omegaconf._utils import is_dict_annotation, is_list_annotation
from omegaconf.errors import KeyValidationError, ValidationError
from omegaconf.nodes import (
    AnyNode,
    BooleanNode,
    EnumNode,
    FloatNode,
    IntegerNode,
    StringNode,
)
from omegaconf.omegaconf import _node_wrap

from . import Color, ConcretePlugin, IllegalType, Plugin, does_not_raise


@pytest.mark.parametrize(  # type: ignore
    "target_type, value, expected",
    [
        # Any
        pytest.param(Any, "foo", AnyNode("foo"), id="any"),
        pytest.param(Any, True, AnyNode(True), id="any"),
        pytest.param(Any, 1, AnyNode(1), id="any"),
        pytest.param(Any, 1.0, AnyNode(1.0), id="any"),
        pytest.param(Any, Color.RED, AnyNode(Color.RED), id="any"),
        pytest.param(Any, {}, DictConfig(content={}), id="any_as_dict"),
        pytest.param(Any, [], ListConfig(content=[]), id="any_as_list"),
        # int
        pytest.param(int, "foo", ValidationError, id="int"),
        pytest.param(int, True, ValidationError, id="int"),
        pytest.param(int, 1, IntegerNode(1), id="int"),
        pytest.param(int, 1.0, ValidationError, id="int"),
        pytest.param(int, Color.RED, ValidationError, id="int"),
        # float
        pytest.param(float, "foo", ValidationError, id="float"),
        pytest.param(float, True, ValidationError, id="float"),
        pytest.param(float, 1, FloatNode(1), id="float"),
        pytest.param(float, 1.0, FloatNode(1.0), id="float"),
        pytest.param(float, Color.RED, ValidationError, id="float"),
        # # bool
        pytest.param(bool, "foo", ValidationError, id="bool"),
        pytest.param(bool, True, BooleanNode(True), id="bool"),
        pytest.param(bool, 1, BooleanNode(True), id="bool"),
        pytest.param(bool, 0, BooleanNode(False), id="bool"),
        pytest.param(bool, 1.0, ValidationError, id="bool"),
        pytest.param(bool, Color.RED, ValidationError, id="bool"),
        pytest.param(bool, "true", BooleanNode(True), id="bool"),
        pytest.param(bool, "false", BooleanNode(False), id="bool"),
        pytest.param(bool, "on", BooleanNode(True), id="bool"),
        pytest.param(bool, "off", BooleanNode(False), id="bool"),
        # str
        pytest.param(str, "foo", StringNode("foo"), id="str"),
        pytest.param(str, True, StringNode("True"), id="str"),
        pytest.param(str, 1, StringNode("1"), id="str"),
        pytest.param(str, 1.0, StringNode("1.0"), id="str"),
        pytest.param(str, Color.RED, StringNode("Color.RED"), id="str"),
        # Color
        pytest.param(Color, "foo", ValidationError, id="Color"),
        pytest.param(Color, True, ValidationError, id="Color"),
        pytest.param(Color, 1, EnumNode(enum_type=Color, value=Color.RED), id="Color"),
        pytest.param(Color, 1.0, ValidationError, id="Color"),
        pytest.param(
            Color, Color.RED, EnumNode(enum_type=Color, value=Color.RED), id="Color"
        ),
        pytest.param(
            Color, "RED", EnumNode(enum_type=Color, value=Color.RED), id="Color"
        ),
        pytest.param(
            Color, "Color.RED", EnumNode(enum_type=Color, value=Color.RED), id="Color"
        ),
        # bad type
        pytest.param(IllegalType, "nope", ValidationError, id="bad_type"),
        # DictConfig
        pytest.param(
            dict, {"foo": "bar"}, DictConfig(content={"foo": "bar"}), id="DictConfig"
        ),
        pytest.param(
            Plugin, Plugin(), DictConfig(content=Plugin()), id="DictConfig[Plugin]"
        ),
        # ListConfig
        pytest.param(list, [1, 2, 3], ListConfig(content=[1, 2, 3]), id="ListConfig"),
    ],
)
def test_node_wrap(target_type: Any, value: Any, expected: Any) -> None:
    from omegaconf.omegaconf import _maybe_wrap

    if isinstance(expected, Node):
        res = _node_wrap(
            type_=target_type, key="foo", value=value, is_optional=False, parent=None
        )
        assert type(res) == type(expected)
        assert res == expected
        assert res._key() == "foo"
    else:
        with pytest.raises(expected):
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
        ("${func:foo}", _utils.ValueKind.INTERPOLATION),
        ("${func:a/b}", _utils.ValueKind.INTERPOLATION),
        ("${func:c:\\a\\b}", _utils.ValueKind.INTERPOLATION),
        ("${func:c:\\a\\b}", _utils.ValueKind.INTERPOLATION),
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
    key_type: Any, expected_key_type: Any, value_type: Any, expected_value_type: Any
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


@pytest.mark.parametrize("optional", [False, True])  # type: ignore
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
    ],
)
def test_type_str(type_: Any, expected: str, optional: bool) -> None:
    if optional:
        assert _utils.type_str(Optional[type_]) == f"Optional[{expected}]"
    else:
        assert _utils.type_str(type_) == expected


def test_type_str_none() -> None:
    assert _utils.type_str(None) == "NoneType"


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (Optional[int], "Optional[int]"),
        (Union[str, int, Color], "Union[str, int, Color]"),
        (Optional[Union[int]], "Optional[int]"),
        (Optional[Union[int, str]], "Union[int, str, NoneType]"),
    ],
)
def test_type_str_union(type_: Any, expected: str) -> None:
    assert _utils.type_str(type_) == expected


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (Dict[str, int], True),
        (Dict[str, float], True),
        (Dict[IllegalType, bool], True),
        (Dict[str, IllegalType], True),
        (Dict[int, Color], True),
        (Dict[Plugin, Plugin], True),
        (Dict[IllegalType, int], True),
        (Dict, True),
        (List, False),
        (dict, False),
        (DictConfig, False),
    ],
)
def test_is_dict_annotation(type_: Any, expected: Any) -> Any:
    assert is_dict_annotation(type_=type_) == expected


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (List[int], True),
        (List[float], True),
        (List[bool], True),
        (List[str], True),
        (List[Color], True),
        (List[Plugin], True),
        (List[IllegalType], True),
        (Dict, False),
        (List, True),
        (list, False),
        (tuple, False),
        (ListConfig, False),
    ],
)
def test_is_list_annotation(type_: Any, expected: Any) -> Any:
    assert is_list_annotation(type_=type_) == expected


@pytest.mark.parametrize(  # type: ignore
    "obj, expected",
    [
        # Unwrapped values
        pytest.param(10, Optional[int], id="int"),
        pytest.param(10.0, Optional[float], id="float"),
        pytest.param(True, Optional[bool], id="bool"),
        pytest.param("bar", Optional[str], id="str"),
        pytest.param(None, type(None), id="NoneType"),
        pytest.param({}, Optional[Dict[Union[str, Enum], Any]], id="dict"),
        pytest.param([], Optional[List[Any]], id="List[Any]"),
        pytest.param(tuple(), Optional[List[Any]], id="List[Any]"),
        pytest.param(ConcretePlugin(), Optional[ConcretePlugin], id="ConcretePlugin"),
        pytest.param(ConcretePlugin, Optional[ConcretePlugin], id="ConcretePlugin"),
        # Optional value nodes
        pytest.param(IntegerNode(10), Optional[int], id="IntegerNode"),
        pytest.param(FloatNode(10.0), Optional[float], id="FloatNode"),
        pytest.param(BooleanNode(True), Optional[bool], id="BooleanNode"),
        pytest.param(StringNode("bar"), Optional[str], id="StringNode"),
        pytest.param(
            EnumNode(enum_type=Color, value=Color.RED),
            Optional[Color],
            id="EnumNode[Color]",
        ),
        # Non-optional value nodes:
        pytest.param(IntegerNode(10, is_optional=False), int, id="IntegerNode"),
        pytest.param(FloatNode(10.0, is_optional=False), float, id="FloatNode"),
        pytest.param(BooleanNode(True, is_optional=False), bool, id="BooleanNode"),
        pytest.param(StringNode("bar", is_optional=False), str, id="StringNode"),
        pytest.param(
            EnumNode(enum_type=Color, value=Color.RED, is_optional=False),
            Color,
            id="EnumNode[Color]",
        ),
        # DictConfig
        pytest.param(DictConfig(content={}), Any, id="DictConfig"),
        pytest.param(
            DictConfig(key_type=int, element_type=Color, content={}),
            Optional[Dict[int, Color]],
            id="DictConfig[int,Color]",
        ),
        pytest.param(
            DictConfig(key_type=Color, element_type=int, content={}),
            Optional[Dict[Color, int]],
            id="DictConfig[Color,int]",
        ),
        pytest.param(
            DictConfig(ref_type=Any, content=ConcretePlugin),
            Any,
            id="DictConfig[ConcretePlugin]_Any_reftype",
        ),
        pytest.param(
            DictConfig(content="???"),
            Optional[Dict[Union[str, Enum], Any]],
            id="DictConfig[Union[str, Enum], Any]_missing",
        ),
        pytest.param(
            DictConfig(content="???", element_type=int, key_type=str),
            Optional[Dict[str, int]],
            id="DictConfig[str, int]_missing",
        ),
        pytest.param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin),
            Optional[Plugin],
            id="DictConfig[Plugin]",
        ),
        pytest.param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin),
            Optional[Plugin],
            id="Plugin",
        ),
        # Non optional DictConfig
        pytest.param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin, is_optional=False),
            Plugin,
            id="Plugin",
        ),
        # ListConfig
        pytest.param(ListConfig([]), Optional[List[Any]], id="ListConfig[Any]"),
        pytest.param(
            ListConfig([], element_type=int), Optional[List[int]], id="ListConfig[int]"
        ),
        pytest.param(
            ListConfig(content="???"), Optional[List[Any]], id="ListConfig_missing"
        ),
        pytest.param(
            ListConfig(content="???", element_type=int),
            Optional[List[int]],
            id="ListConfig[int]_missing",
        ),
        pytest.param(
            ListConfig(content=None), Optional[List[Any]], id="ListConfig_none"
        ),
        pytest.param(
            ListConfig(content=None, element_type=int),
            Optional[List[int]],
            id="ListConfig[int]_none",
        ),
    ],
)
def test_get_ref_type(obj: Any, expected: Any) -> None:
    assert _utils.get_ref_type(obj) == expected
