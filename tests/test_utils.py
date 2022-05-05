import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import attr
from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, _utils
from omegaconf._utils import (
    Marker,
    _ensure_container,
    _get_value,
    _is_optional,
    get_dict_key_value_types,
    get_list_element_type,
    is_dict_annotation,
    is_list_annotation,
    is_tuple_annotation,
    nullcontext,
    split_key,
)
from omegaconf.errors import UnsupportedValueType, ValidationError
from omegaconf.nodes import (
    AnyNode,
    BooleanNode,
    BytesNode,
    EnumNode,
    FloatNode,
    IntegerNode,
    StringNode,
)
from omegaconf.omegaconf import _node_wrap
from tests import Color, ConcretePlugin, Dataframe, IllegalType, Plugin, User


class DummyEnum(Enum):
    FOO = 1


@mark.parametrize("is_optional", [True, False])
@mark.parametrize(
    "ref_type, value, expected_type",
    [
        (Any, 10, AnyNode),
        (DummyEnum, DummyEnum.FOO, EnumNode),
        (int, 42, IntegerNode),
        (bytes, b"\xf0\xf1\xf2", BytesNode),
        (float, 3.1415, FloatNode),
        (bool, True, BooleanNode),
        (str, "foo", StringNode),
    ],
)
def test_node_wrap(
    ref_type: type, is_optional: bool, value: Any, expected_type: Any
) -> None:
    from omegaconf.omegaconf import _node_wrap

    ret = _node_wrap(
        ref_type=ref_type,
        value=value,
        is_optional=is_optional,
        parent=None,
        key=None,
    )
    assert ret._metadata.ref_type == ref_type
    assert type(ret) == expected_type
    assert ret == value

    if is_optional:
        ret = _node_wrap(
            ref_type=ref_type,
            value=None,
            is_optional=is_optional,
            parent=None,
            key=None,
        )
        assert type(ret) == expected_type
        # noinspection PyComparisonWithNone
        assert ret == None  # noqa E711


@mark.parametrize(
    "target_type, value, expected",
    [
        # Any
        param(Any, "foo", AnyNode("foo"), id="any"),
        param(Any, b"binary", AnyNode(b"binary"), id="any"),
        param(Any, True, AnyNode(True), id="any"),
        param(Any, 1, AnyNode(1), id="any"),
        param(Any, 1.0, AnyNode(1.0), id="any"),
        param(Any, b"123", AnyNode(b"123"), id="any"),
        param(Any, Color.RED, AnyNode(Color.RED), id="any"),
        param(Any, {}, DictConfig(content={}), id="any_as_dict"),
        param(Any, [], ListConfig(content=[]), id="any_as_list"),
        # int
        param(int, "foo", ValidationError, id="int"),
        param(int, b"binary", ValidationError, id="int"),
        param(int, True, ValidationError, id="int"),
        param(int, 1, IntegerNode(1), id="int"),
        param(int, 1.0, ValidationError, id="int"),
        param(int, Color.RED, ValidationError, id="int"),
        param(int, b"123", ValidationError, id="int"),
        # float
        param(float, "foo", ValidationError, id="float"),
        param(float, b"binary", ValidationError, id="float"),
        param(float, True, ValidationError, id="float"),
        param(float, 1, FloatNode(1), id="float"),
        param(float, 1.0, FloatNode(1.0), id="float"),
        param(float, Color.RED, ValidationError, id="float"),
        param(float, b"123", ValidationError, id="float"),
        # bool
        param(bool, "foo", ValidationError, id="bool"),
        param(bool, b"binary", ValidationError, id="bool"),
        param(bool, True, BooleanNode(True), id="bool"),
        param(bool, 1, BooleanNode(True), id="bool"),
        param(bool, 0, BooleanNode(False), id="bool"),
        param(bool, 1.0, ValidationError, id="bool"),
        param(bool, Color.RED, ValidationError, id="bool"),
        param(bool, "true", BooleanNode(True), id="bool"),
        param(bool, "false", BooleanNode(False), id="bool"),
        param(bool, "on", BooleanNode(True), id="bool"),
        param(bool, "off", BooleanNode(False), id="bool"),
        param(bool, b"123", ValidationError, id="bool"),
        # str
        param(str, "foo", StringNode("foo"), id="str"),
        param(str, b"binary", ValidationError, id="str"),
        param(str, True, StringNode("True"), id="str"),
        param(str, 1, StringNode("1"), id="str"),
        param(str, 1.0, StringNode("1.0"), id="str"),
        param(str, Color.RED, StringNode("Color.RED"), id="str"),
        # bytes
        param(bytes, "foo", ValidationError, id="bytes"),
        param(bytes, b"binary", BytesNode(b"binary"), id="bytes"),
        param(bytes, True, ValidationError, id="bytes"),
        param(bytes, 1, ValidationError, id="bytes"),
        param(bytes, 1.0, ValidationError, id="bytes"),
        param(bytes, Color.RED, ValidationError, id="bytes"),
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
        param(Color, b"123", ValidationError, id="Color"),
        param(
            Color, "Color.RED", EnumNode(enum_type=Color, value=Color.RED), id="Color"
        ),
        # bad type
        param(IllegalType, "nope", ValidationError, id="bad_type"),
        param(IllegalType, [1, 2, 3], ValidationError, id="list_bad_type"),
        param(IllegalType, {"foo": "bar"}, ValidationError, id="dict_bad_type"),
        # DictConfig
        param(
            Dict[Any, Any],
            {"foo": "bar"},
            DictConfig(content={"foo": "bar"}),
            id="DictConfig",
        ),
        param(List[Any], {"foo": "bar"}, ValidationError, id="dict_to_list"),
        param(List[int], {"foo": "bar"}, ValidationError, id="dict_to_list[int]"),
        param(
            Any,
            {"foo": "bar"},
            DictConfig(content={"foo": "bar"}),
            id="dict_to_any",
        ),
        param(Plugin, {"foo": "bar"}, ValidationError, id="dict_to_plugin"),
        # Structured Config
        param(Plugin, Plugin(), DictConfig(content=Plugin()), id="DictConfig[Plugin]"),
        param(Any, Plugin(), DictConfig(content=Plugin()), id="plugin_to_any"),
        param(
            Dict[str, int],
            Plugin(),
            ValidationError,
            id="plugin_to_dict[str, int]",
        ),
        param(List[Any], Plugin(), ValidationError, id="plugin_to_list"),
        param(List[int], Plugin(), ValidationError, id="plugin_to_list[int]"),
        # ListConfig
        param(List[Any], [1, 2, 3], ListConfig(content=[1, 2, 3]), id="ListConfig"),
        param(Dict[Any, Any], [1, 2, 3], ValidationError, id="list_to_dict"),
        param(Dict[str, int], [1, 2, 3], ValidationError, id="list_to_dict[str-int]"),
        param(Any, [1, 2, 3], ListConfig(content=[1, 2, 3]), id="list_to_any"),
    ],
)
def test_node_wrap2(target_type: Any, value: Any, expected: Any) -> None:
    from omegaconf.omegaconf import _node_wrap

    if isinstance(expected, Node):
        res = _node_wrap(
            ref_type=target_type, key="foo", value=value, is_optional=False, parent=None
        )
        assert type(res) == type(expected)
        assert res == expected
        assert res._key() == "foo"
    else:
        with raises(expected):
            _node_wrap(
                ref_type=target_type,
                key=None,
                value=value,
                is_optional=False,
                parent=None,
            )


def test_node_wrap_illegal_type() -> None:
    class UserClass:
        pass

    from omegaconf.omegaconf import _node_wrap

    with raises(ValidationError):
        _node_wrap(
            ref_type=UserClass,
            value=UserClass(),
            is_optional=False,
            parent=None,
            key=None,
        )


class _TestEnum(Enum):
    A = 1
    B = 2


@dataclass
class _TestDataclass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    d: bytes = b"123"
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = field(default_factory=list)
    dict1: Dict[str, int] = field(default_factory=dict)
    init_false: str = field(init=False, default="foo")


@attr.s(auto_attribs=True)
class _TestAttrsClass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    d: bytes = b"123"
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = []
    dict1: Dict[str, int] = {}
    init_false: str = attr.field(init=False, default="foo")


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
        (bytes, True),
        (Any, True),
        (_TestEnum, True),
        (_TestUserClass, False),
        # Nesting structured configs in contain
        (_TestAttrsClass, True),
        (_TestDataclass, True),
    ],
)
def test_valid_value_annotation_type(type_: type, expected: bool) -> None:
    from omegaconf._utils import is_valid_value_annotation

    assert is_valid_value_annotation(type_) == expected


class TestGetStructuredConfigInfo:
    @mark.parametrize(
        "test_cls_or_obj",
        [_TestDataclass, _TestDataclass(), _TestAttrsClass, _TestAttrsClass()],
    )
    def test_get_structured_config_data(self, test_cls_or_obj: Any) -> None:
        d = _utils.get_structured_config_data(test_cls_or_obj)
        assert d["x"] == 10
        assert d["s"] == "foo"
        assert d["b"] == bool(True)
        assert d["d"] == b"123"
        assert d["f"] == 3.14
        assert d["e"] == _TestEnum.A
        assert d["list1"] == []
        assert d["dict1"] == {}

    def test_get_structured_config_data_throws_ValueError(self) -> None:
        with raises(ValueError):
            _utils.get_structured_config_data("invalid")

    @mark.parametrize(
        "test_cls_or_obj",
        [_TestDataclass, _TestDataclass(), _TestAttrsClass, _TestAttrsClass()],
    )
    def test_get_structured_config_field_names(self, test_cls_or_obj: Any) -> None:
        field_names = _utils.get_structured_config_init_field_names(test_cls_or_obj)
        assert field_names == ["x", "s", "b", "d", "f", "e", "list1", "dict1"]

    def test_get_structured_config_field_names_throws_ValueError(self) -> None:
        with raises(ValueError):
            _utils.get_structured_config_init_field_names("invalid")


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
        (b"123", _utils.ValueKind.VALUE),
        (True, _utils.ValueKind.VALUE),
        (False, _utils.ValueKind.VALUE),
        (Color.GREEN, _utils.ValueKind.VALUE),
        (Dataclass, _utils.ValueKind.VALUE),
        (Dataframe(), _utils.ValueKind.VALUE),
        (IntegerNode(123), _utils.ValueKind.VALUE),
        (DictConfig({}), _utils.ValueKind.VALUE),
        (ListConfig([]), _utils.ValueKind.VALUE),
        (AnyNode(123), _utils.ValueKind.VALUE),
        ("???", _utils.ValueKind.MANDATORY_MISSING),
        (IntegerNode("???"), _utils.ValueKind.MANDATORY_MISSING),
        (DictConfig("???"), _utils.ValueKind.MANDATORY_MISSING),
        (ListConfig("???"), _utils.ValueKind.MANDATORY_MISSING),
        (AnyNode("???"), _utils.ValueKind.MANDATORY_MISSING),
        ("${foo.bar}", _utils.ValueKind.INTERPOLATION),
        ("ftp://${host}/path", _utils.ValueKind.INTERPOLATION),
        ("${func:foo}", _utils.ValueKind.INTERPOLATION),
        ("${func:a/b}", _utils.ValueKind.INTERPOLATION),
        ("${func:c:\\a\\b}", _utils.ValueKind.INTERPOLATION),
        ("${func:c:\\a\\b}", _utils.ValueKind.INTERPOLATION),
        param(
            IntegerNode("${func:c:\\a\\b}"),
            _utils.ValueKind.INTERPOLATION,
            id="integernode-interp",
        ),
        param(
            DictConfig("${func:c:\\a\\b}"),
            _utils.ValueKind.INTERPOLATION,
            id="dictconfig-interp",
        ),
        param(
            ListConfig("${func:c:\\a\\b}"),
            _utils.ValueKind.INTERPOLATION,
            id="listconfig-interp",
        ),
        param(
            AnyNode("${func:c:\\a\\b}"),
            _utils.ValueKind.INTERPOLATION,
            id="anynode-interp",
        ),
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
        (bytes, True),
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
    assert _utils.is_primitive_type_annotation(type_) == is_primitive


@mark.parametrize("optional", [False, True])
@mark.parametrize(
    "type_, include_module_name, expected",
    [
        (int, False, "int"),
        (int, True, "int"),
        (bool, False, "bool"),
        (bool, True, "bool"),
        (bytes, False, "bytes"),
        (bytes, True, "bytes"),
        (float, False, "float"),
        (float, True, "float"),
        (str, False, "str"),
        (str, True, "str"),
        (Color, False, "Color"),
        (Color, True, "tests.Color"),
        (DictConfig, False, "DictConfig"),
        (DictConfig, True, "DictConfig"),
        (ListConfig, False, "ListConfig"),
        (ListConfig, True, "ListConfig"),
        (Dict[str, str], False, "Dict[str, str]"),
        (Dict[str, str], True, "Dict[str, str]"),
        (Dict[Color, int], False, "Dict[Color, int]"),
        (Dict[Color, int], True, "Dict[tests.Color, int]"),
        (Dict[str, Plugin], False, "Dict[str, Plugin]"),
        (Dict[str, Plugin], True, "Dict[str, tests.Plugin]"),
        (Dict[str, List[Plugin]], False, "Dict[str, List[Plugin]]"),
        (Dict[str, List[Plugin]], True, "Dict[str, List[tests.Plugin]]"),
        (List[str], False, "List[str]"),
        (List[str], True, "List[str]"),
        (List[Color], False, "List[Color]"),
        (List[Color], True, "List[tests.Color]"),
        (List[Dict[str, Color]], False, "List[Dict[str, Color]]"),
        (List[Dict[str, Color]], True, "List[Dict[str, tests.Color]]"),
        (Tuple[str], False, "Tuple[str]"),
        (Tuple[str], True, "Tuple[str]"),
        (Tuple[str, int], False, "Tuple[str, int]"),
        (Tuple[str, int], True, "Tuple[str, int]"),
        (Tuple[float, ...], False, "Tuple[float, ...]"),
        (Tuple[float, ...], True, "Tuple[float, ...]"),
    ],
)
def test_type_str(
    type_: Any, include_module_name: bool, expected: str, optional: bool
) -> None:
    if optional:
        assert (
            _utils.type_str(Optional[type_], include_module_name=include_module_name)
            == f"Optional[{expected}]"
        )
    else:
        assert (
            _utils.type_str(type_, include_module_name=include_module_name) == expected
        )


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
        (Dict[bytes, bytes], True),
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
        (List[bytes], True),
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
    "type_, expected",
    [
        (Tuple[int], True),
        (Tuple[float], True),
        (Tuple[bool], True),
        (Tuple[str], True),
        (Tuple[Color], True),
        (Tuple[Plugin], True),
        (Tuple[IllegalType], True),
        (Dict, False),
        (List, False),
        (Tuple, True),
        (Tuple, True),
        (list, False),
        (dict, False),
        (tuple, False),
    ],
)
def test_is_tuple_annotation(type_: Any, expected: Any) -> Any:
    assert is_tuple_annotation(type_=type_) == expected


@mark.parametrize(
    "obj, expected",
    [
        # Unwrapped values
        param(10, Any, id="int"),
        param(10.0, Any, id="float"),
        param(True, Any, id="bool"),
        param(Color.RED, Any, id="bytes"),
        param(b"binary", Any, id="bytes"),
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
        param(BytesNode(b"binary"), Optional[bytes], id="BooleanNode"),
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
        param(BytesNode(b"binary", is_optional=False), bytes, id="BytesNode"),
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
    assert _utils.get_type_hint(obj) == expected


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
    assert _utils.get_type_hint(cfg, key) == expected


def test_get_ref_type_error() -> None:
    with raises(ValueError):
        _utils.get_type_hint(AnyNode(), "foo")


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
        value=value, ref_type=Any, parent=None, is_optional=True, key=None
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


def test_ensure_container_raises_ValueError() -> None:
    """Some values cannot be converted to a container.
    On these inputs, _ensure_container should raise a ValueError."""
    with raises(
        ValueError,
        match=re.escape(
            "Invalid input. Supports one of "
            + "[dict,list,DictConfig,ListConfig,dataclass,dataclass instance,attr class,attr class instance]"
        ),
    ):
        _ensure_container("abc")


def test_marker_string_representation() -> None:
    marker = Marker("marker")
    assert repr(marker) == "marker"


@mark.parametrize(
    ("key", "expected"),
    [
        ("", [""]),
        ("foo", ["foo"]),
        ("foo.bar", ["foo", "bar"]),
        ("foo[bar]", ["foo", "bar"]),
        (".foo", ["", "foo"]),
        ("..foo", ["", "", "foo"]),
        (".foo[bar]", ["", "foo", "bar"]),
        ("[foo]", ["foo"]),
        ("[foo][bar]", ["foo", "bar"]),
        (".[foo][bar]", ["", "foo", "bar"]),
        ("..[foo][bar]", ["", "", "foo", "bar"]),
        (
            "...a[b][c].d.e[f].g[h]",
            ["", "", "", "a", "b", "c", "d", "e", "f", "g", "h"],
        ),
    ],
)
def test_split_key(key: str, expected: List[str]) -> None:
    assert split_key(key) == expected


def test_nullcontext() -> None:
    with nullcontext() as x:
        assert x is None

    obj = object()
    with nullcontext(obj) as x:
        assert x is obj


@mark.parametrize("is_optional", [True, False])
@mark.parametrize(
    "fac",
    [
        (
            lambda is_optional, missing: StringNode(
                value="foo" if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: IntegerNode(
                value=10 if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: FloatNode(
                value=10.0 if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: BooleanNode(
                value=True if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: BytesNode(
                value=b"binary" if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: EnumNode(
                enum_type=Color,
                value=Color.RED if not missing else "???",
                is_optional=is_optional,
            )
        ),
        (
            lambda is_optional, missing: ListConfig(
                content=[1, 2, 3] if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: DictConfig(
                content={"foo": "bar"} if not missing else "???",
                is_optional=is_optional,
            )
        ),
        (
            lambda is_optional, missing: DictConfig(
                ref_type=ConcretePlugin,
                content=ConcretePlugin() if not missing else "???",
                is_optional=is_optional,
            )
        ),
    ],
)
def test_is_optional(fac: Any, is_optional: bool) -> None:
    obj = fac(is_optional, False)
    assert _is_optional(obj) == is_optional

    cfg = OmegaConf.create({"node": obj})
    assert _is_optional(cfg, "node") == is_optional

    obj = fac(is_optional, True)
    assert _is_optional(obj) == is_optional

    cfg = OmegaConf.create({"node": obj})
    assert _is_optional(cfg, "node") == is_optional


@mark.parametrize(
    "ref_type, expected_key_type, expected_element_type",
    [
        param(Dict, Any, Any, id="any"),
        param(Dict[Any, Any], Any, Any, id="any_explicit"),
        param(Dict[int, float], int, float, id="int_float"),
        param(Dict[Color, User], Color, User, id="color_user"),
        param(Dict[str, List[int]], str, List[int], id="list"),
        param(Dict[str, Dict[int, float]], str, Dict[int, float], id="dict"),
    ],
)
def test_get_dict_key_value_types(
    ref_type: Any, expected_key_type: Any, expected_element_type: Any
) -> None:
    key_type, element_type = get_dict_key_value_types(ref_type)
    assert key_type == expected_key_type
    assert element_type == expected_element_type


@mark.parametrize(
    "ref_type, expected_element_type",
    [
        param(List, Any, id="any"),
        param(List[Any], Any, id="any_explicit"),
        param(List[int], int, id="int"),
        param(List[User], User, id="user"),
        param(List[List[int]], List[int], id="list"),
        param(List[Dict[int, float]], Dict[int, float], id="dict"),
    ],
)
def test_get_list_element_type(ref_type: Any, expected_element_type: Any) -> None:
    assert get_list_element_type(ref_type) == expected_element_type
