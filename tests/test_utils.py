from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import attr
from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, _utils
from omegaconf._utils import (
    SIMPLE_INTERPOLATION_PATTERN,
    _get_value,
    _make_hashable,
    is_dict_annotation,
    is_list_annotation,
)
from omegaconf.errors import UnsupportedValueType, ValidationError
from omegaconf.nodes import (
    AnyNode,
    BooleanNode,
    EnumNode,
    FloatNode,
    IntegerNode,
    StringNode,
)
from omegaconf.omegaconf import _node_wrap
from tests import (
    Color,
    ConcretePlugin,
    Dataframe,
    IllegalType,
    Plugin,
    User,
    does_not_raise,
)


@mark.parametrize(
    "target_type, value, expected",
    [
        # Any
        param(Any, "foo", AnyNode("foo"), id="any"),
        param(Any, True, AnyNode(True), id="any"),
        param(Any, 1, AnyNode(1), id="any"),
        param(Any, 1.0, AnyNode(1.0), id="any"),
        param(Any, Color.RED, AnyNode(Color.RED), id="any"),
        param(Any, {}, DictConfig(content={}), id="any_as_dict"),
        param(Any, [], ListConfig(content=[]), id="any_as_list"),
        # int
        param(int, "foo", ValidationError, id="int"),
        param(int, True, ValidationError, id="int"),
        param(int, 1, IntegerNode(1), id="int"),
        param(int, 1.0, ValidationError, id="int"),
        param(int, Color.RED, ValidationError, id="int"),
        # float
        param(float, "foo", ValidationError, id="float"),
        param(float, True, ValidationError, id="float"),
        param(float, 1, FloatNode(1), id="float"),
        param(float, 1.0, FloatNode(1.0), id="float"),
        param(float, Color.RED, ValidationError, id="float"),
        # # bool
        param(bool, "foo", ValidationError, id="bool"),
        param(bool, True, BooleanNode(True), id="bool"),
        param(bool, 1, BooleanNode(True), id="bool"),
        param(bool, 0, BooleanNode(False), id="bool"),
        param(bool, 1.0, ValidationError, id="bool"),
        param(bool, Color.RED, ValidationError, id="bool"),
        param(bool, "true", BooleanNode(True), id="bool"),
        param(bool, "false", BooleanNode(False), id="bool"),
        param(bool, "on", BooleanNode(True), id="bool"),
        param(bool, "off", BooleanNode(False), id="bool"),
        # str
        param(str, "foo", StringNode("foo"), id="str"),
        param(str, True, StringNode("True"), id="str"),
        param(str, 1, StringNode("1"), id="str"),
        param(str, 1.0, StringNode("1.0"), id="str"),
        param(str, Color.RED, StringNode("Color.RED"), id="str"),
        # Color
        param(Color, "foo", ValidationError, id="Color"),
        param(Color, True, ValidationError, id="Color"),
        param(Color, 1, EnumNode(enum_type=Color, value=Color.RED), id="Color"),
        param(Color, 1.0, ValidationError, id="Color"),
        param(Color, Color.RED, EnumNode(enum_type=Color, value=Color.RED), id="Color"),
        param(Color, "RED", EnumNode(enum_type=Color, value=Color.RED), id="Color"),
        param(
            Color, "Color.RED", EnumNode(enum_type=Color, value=Color.RED), id="Color"
        ),
        # bad type
        param(IllegalType, "nope", ValidationError, id="bad_type"),
        # DictConfig
        param(
            dict, {"foo": "bar"}, DictConfig(content={"foo": "bar"}), id="DictConfig"
        ),
        param(Plugin, Plugin(), DictConfig(content=Plugin()), id="DictConfig[Plugin]"),
        # ListConfig
        param(list, [1, 2, 3], ListConfig(content=[1, 2, 3]), id="ListConfig"),
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
        with raises(expected):
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


@dataclass
class _TestDataclassIllegalValue:
    x: Any = IllegalType()


@attr.s(auto_attribs=True)
class _TestAttrllegalValue:
    x: Any = IllegalType()


class _TestUserClass:
    pass


@mark.parametrize(
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


@mark.parametrize(
    "test_cls_or_obj, expectation",
    [
        (_TestDataclass, does_not_raise()),
        (_TestDataclass(), does_not_raise()),
        (_TestAttrsClass, does_not_raise()),
        (_TestAttrsClass(), does_not_raise()),
        ("invalid", raises(ValueError)),
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


@mark.parametrize(
    "test_cls",
    [
        _TestDataclassIllegalValue,
        _TestAttrllegalValue,
    ],
)
def test_get_structured_config_data_illegal_value(test_cls: Any) -> None:
    with raises(UnsupportedValueType):
        _utils.get_structured_config_data(test_cls, allow_objects=None)

    with raises(UnsupportedValueType):
        _utils.get_structured_config_data(test_cls, allow_objects=False)

    d = _utils.get_structured_config_data(test_cls, allow_objects=True)
    assert d["x"] == IllegalType()


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


@mark.parametrize(
    "value,kind",
    [
        ("foo", _utils.ValueKind.VALUE),
        (1, _utils.ValueKind.VALUE),
        (1.0, _utils.ValueKind.VALUE),
        (True, _utils.ValueKind.VALUE),
        (False, _utils.ValueKind.VALUE),
        (Color.GREEN, _utils.ValueKind.VALUE),
        (Dataclass, _utils.ValueKind.VALUE),
        (Dataframe(), _utils.ValueKind.VALUE),
        ("???", _utils.ValueKind.MANDATORY_MISSING),
        ("${foo.bar}", _utils.ValueKind.INTERPOLATION),
        ("ftp://${host}/path", _utils.ValueKind.INTERPOLATION),
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
        assert cfg1._get_node("str")._get_parent() == cfg1  # type: ignore
        assert cfg1._get_node("list")._get_parent() == cfg1  # type: ignore
        assert cfg1.list._get_node(0)._get_parent() == cfg1.list

    cfg = OmegaConf.create({})
    assert isinstance(cfg, DictConfig)
    cfg.str = StringNode("str")
    cfg.list = [1]

    validate(cfg)

    cfg._get_node("str")._set_parent(None)  # type: ignore
    cfg._get_node("list")._set_parent(None)  # type: ignore
    cfg.list._get_node(0)._set_parent(None)  # type:ignore
    # noinspection PyProtectedMember
    cfg._re_parent()
    validate(cfg)


def test_get_class() -> None:
    name = "tests.examples.test_dataclass_example.SimpleTypes"
    assert _utils._get_class(name).__name__ == "SimpleTypes"
    with raises(ValueError):
        _utils._get_class("not_found")

    with raises(ModuleNotFoundError):
        _utils._get_class("foo.not_found")

    with raises(ImportError):
        _utils._get_class("tests.examples.test_dataclass_example.not_found")


@mark.parametrize(
    "key_type,expected_key_type",
    [
        (str, str),
        (Color, Color),
        (Any, Any),
    ],
)
@mark.parametrize(
    "value_type,expected_value_type",
    [
        (int, int),
        (str, str),
        (Color, Color),
        (Any, Any),
    ],
)
def test_get_key_value_types(
    key_type: Any, expected_key_type: Any, value_type: Any, expected_value_type: Any
) -> None:
    dt = Dict[key_type, value_type]  # type:ignore
    assert _utils.get_dict_key_value_types(dt) == (
        expected_key_type,
        expected_value_type,
    )


@mark.parametrize(
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


@mark.parametrize("optional", [False, True])
@mark.parametrize(
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
        (Tuple[str], "Tuple[str]"),
        (Tuple[str, int], "Tuple[str, int]"),
        (Tuple[float, ...], "Tuple[float, ...]"),
    ],
)
def test_type_str(type_: Any, expected: str, optional: bool) -> None:
    if optional:
        assert _utils.type_str(Optional[type_]) == f"Optional[{expected}]"
    else:
        assert _utils.type_str(type_) == expected


def test_type_str_ellipsis() -> None:
    assert _utils.type_str(...) == "..."


def test_type_str_none() -> None:
    assert _utils.type_str(None) == "NoneType"


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize(
    "obj, expected",
    [
        # Unwrapped values
        param(10, Any, id="int"),
        param(10.0, Any, id="float"),
        param(True, Any, id="bool"),
        param("bar", Any, id="str"),
        param(None, Any, id="NoneType"),
        param({}, Any, id="dict"),
        param([], Any, id="List[Any]"),
        param(tuple(), Any, id="List[Any]"),
        param(ConcretePlugin(), Any, id="ConcretePlugin"),
        param(ConcretePlugin, Any, id="ConcretePlugin"),
        # Optional value nodes
        param(IntegerNode(10), Optional[int], id="IntegerNode"),
        param(FloatNode(10.0), Optional[float], id="FloatNode"),
        param(BooleanNode(True), Optional[bool], id="BooleanNode"),
        param(StringNode("bar"), Optional[str], id="StringNode"),
        param(
            EnumNode(enum_type=Color, value=Color.RED),
            Optional[Color],
            id="EnumNode[Color]",
        ),
        # Non-optional value nodes:
        param(IntegerNode(10, is_optional=False), int, id="IntegerNode"),
        param(FloatNode(10.0, is_optional=False), float, id="FloatNode"),
        param(BooleanNode(True, is_optional=False), bool, id="BooleanNode"),
        param(StringNode("bar", is_optional=False), str, id="StringNode"),
        param(
            EnumNode(enum_type=Color, value=Color.RED, is_optional=False),
            Color,
            id="EnumNode[Color]",
        ),
        # DictConfig
        param(DictConfig(content={}), Any, id="DictConfig"),
        param(
            DictConfig(key_type=str, element_type=Color, content={}),
            Any,
            id="DictConfig[str,Color]",
        ),
        param(
            DictConfig(key_type=Color, element_type=int, content={}),
            Any,
            id="DictConfig[Color,int]",
        ),
        param(
            DictConfig(ref_type=Any, content=ConcretePlugin),
            Any,
            id="DictConfig[ConcretePlugin]_Any_reftype",
        ),
        param(
            DictConfig(content="???"),
            Any,
            id="DictConfig[Union[str, Enum], Any]_missing",
        ),
        param(
            DictConfig(content="???", element_type=int, key_type=str),
            Any,
            id="DictConfig[str, int]_missing",
        ),
        param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin),
            Optional[Plugin],
            id="DictConfig[Plugin]",
        ),
        param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin),
            Optional[Plugin],
            id="Plugin",
        ),
        # Non optional DictConfig
        param(
            DictConfig(ref_type=Plugin, content=ConcretePlugin, is_optional=False),
            Plugin,
            id="Plugin",
        ),
        # ListConfig
        param(ListConfig([]), Any, id="ListConfig[Any]"),
        param(ListConfig([], element_type=int), Any, id="ListConfig[int]"),
        param(ListConfig(content="???"), Any, id="ListConfig_missing"),
        param(
            ListConfig(content="???", element_type=int),
            Any,
            id="ListConfig[int]_missing",
        ),
        param(ListConfig(content=None), Any, id="ListConfig_none"),
        param(
            ListConfig(content=None, element_type=int),
            Any,
            id="ListConfig[int]_none",
        ),
    ],
)
def test_get_ref_type(obj: Any, expected: Any) -> None:
    assert _utils.get_ref_type(obj) == expected


@mark.parametrize(
    "obj, key, expected",
    [
        param({"foo": 10}, "foo", Any, id="dict"),
        param(User, "name", str, id="User.name"),
        param(User, "age", int, id="User.age"),
        param({"user": User}, "user", Any, id="user"),
    ],
)
def test_get_node_ref_type(obj: Any, key: str, expected: Any) -> None:
    cfg = OmegaConf.create(obj)
    assert _utils.get_ref_type(cfg, key) == expected


def test_get_ref_type_error() -> None:
    with raises(ValueError):
        _utils.get_ref_type(AnyNode(), "foo")


@mark.parametrize(
    "value",
    [
        1,
        None,
        {"a": 0},
        [1, 2, 3],
    ],
)
def test_get_value_basic(value: Any) -> None:
    val_node = _node_wrap(
        value=value, type_=Any, parent=None, is_optional=True, key=None
    )
    assert _get_value(val_node) == value


@mark.parametrize(
    "content",
    [{"a": 0, "b": 1}, "???", None, "${bar}"],
)
def test_get_value_container(content: Any) -> None:
    cfg = DictConfig({})
    cfg._set_value(content)
    assert _get_value(cfg) == content


@mark.parametrize(
    "input_1,input_2",
    [
        (0, 0),
        ([0, 1], (0, 1)),
        ([0, (1, 2)], (0, [1, 2])),
        ({0: 1, 1: 2}, {1: 2, 0: 1}),
        ({"": 1, 0: 2}, {0: 2, "": 1}),
        (
            {1: 0, 1.1: 2.0, "1": "0", True: False, None: None},
            {None: None, 1.1: 2.0, True: False, "1": "0", 1: 0},
        ),
    ],
)
def test_make_hashable(input_1: Any, input_2: Any) -> None:
    out_1, out_2 = _make_hashable(input_1), _make_hashable(input_2)
    assert out_1 == out_2
    hash_1, hash_2 = hash(out_1), hash(out_2)
    assert hash_1 == hash_2


def test_make_hashable_type_error() -> None:
    with raises(TypeError):
        _make_hashable({...: 0, None: 0})


@mark.parametrize(
    "expression",
    [
        "${foo}",
        "${foo.bar}",
        "${a_b.c123}",
        "${  foo \t}",
        "x ${ab.cd.ef.gh} y",
        "$ ${foo} ${bar} ${boz} $",
        "${foo:bar}",
        "${foo : bar, baz, boz}",
        "${foo:bar,0,a-b+c*d/$.%@}",
        "\\${foo}",
        "${foo.bar:boz}",
    ],
)
def test_match_simple_interpolation_pattern(expression: str) -> None:
    assert SIMPLE_INTERPOLATION_PATTERN.match(expression) is not None


@mark.parametrize(
    "expression",
    [
        "${foo",
        "${0foo}",
        "${0foo:bar}",
        "${foo.${bar}}",
        "${foo:${bar}}",
        "${foo:'hello'}",
        "\\${foo",
    ],
)
def test_do_not_match_simple_interpolation_pattern(expression: str) -> None:
    assert SIMPLE_INTERPOLATION_PATTERN.match(expression) is None
