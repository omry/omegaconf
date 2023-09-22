import re
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import attr
from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, Node, OmegaConf, UnionNode, _utils
from omegaconf._utils import (  # _normalize_ref_type,
    Marker,
    NoneType,
    _ensure_container,
    _get_value,
    _is_optional,
    _resolve_forward,
    _resolve_optional,
    get_dict_key_value_types,
    get_list_element_type,
    get_tuple_item_types,
    is_dict_annotation,
    is_list_annotation,
    is_primitive_dict,
    is_primitive_list,
    is_supported_union_annotation,
    is_tuple_annotation,
    is_union_annotation,
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
    PathNode,
    StringNode,
)
from omegaconf.omegaconf import _node_wrap
from tests import (
    Color,
    ConcretePlugin,
    Dataframe,
    DictSubclass,
    IllegalType,
    IllegalTypeGeneric,
    ListSubclass,
    Plugin,
    Shape,
    Str2Int,
    UnionAnnotations,
    User,
)


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
        (Path, Path("hello.txt"), PathNode),
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
        param(Any, Path("hello.txt"), AnyNode(Path("hello.txt")), id="any"),
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
        param(int, Path("hello.txt"), ValidationError, id="int"),
        param(int, True, ValidationError, id="int"),
        param(int, 1, IntegerNode(1), id="int"),
        param(int, 1.0, ValidationError, id="int"),
        param(int, Color.RED, ValidationError, id="int"),
        param(int, b"123", ValidationError, id="int"),
        # float
        param(float, "foo", ValidationError, id="float"),
        param(float, b"binary", ValidationError, id="float"),
        param(float, Path("hello.txt"), ValidationError, id="float"),
        param(float, True, ValidationError, id="float"),
        param(float, 1, FloatNode(1), id="float"),
        param(float, 1.0, FloatNode(1.0), id="float"),
        param(float, Color.RED, ValidationError, id="float"),
        param(float, b"123", ValidationError, id="float"),
        # bool
        param(bool, "foo", ValidationError, id="bool"),
        param(bool, b"binary", ValidationError, id="bool"),
        param(bool, Path("hello.txt"), ValidationError, id="bool"),
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
        param(str, Path("hello.txt"), StringNode("hello.txt"), id="str"),
        param(str, True, StringNode("True"), id="str"),
        param(str, 1, StringNode("1"), id="str"),
        param(str, 1.0, StringNode("1.0"), id="str"),
        param(str, Color.RED, StringNode("Color.RED"), id="str"),
        # bytes
        param(bytes, "foo", ValidationError, id="bytes"),
        param(bytes, b"binary", BytesNode(b"binary"), id="bytes"),
        param(bytes, Path("hello.txt"), ValidationError, id="bytes"),
        param(bytes, True, ValidationError, id="bytes"),
        param(bytes, 1, ValidationError, id="bytes"),
        param(bytes, 1.0, ValidationError, id="bytes"),
        param(bytes, Color.RED, ValidationError, id="bytes"),
        # Path
        param(Path, "foo", PathNode("foo"), id="path"),
        param(Path, b"binary", ValidationError, id="path"),
        param(Path, Path("hello.txt"), PathNode("hello.txt"), id="path"),
        param(Path, True, ValidationError, id="path"),
        param(Path, 1, ValidationError, id="path"),
        param(Path, 1.0, ValidationError, id="path"),
        param(Path, Color.RED, ValidationError, id="path"),
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
        param(Color, Path("hello.txt"), ValidationError, id="Color"),
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
    from omegaconf.omegaconf import _maybe_wrap

    if isinstance(expected, Node):
        res = _node_wrap(
            ref_type=target_type, key="foo", value=value, is_optional=False, parent=None
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
    p: Path = Path("hello.txt")
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
    p: Path = Path("hello.txt")
    d: bytes = b"123"
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = []
    dict1: Dict[str, int] = {}
    init_false: str = attr.field(init=False, default="foo")


@dataclass
class _TestDataclassIllegalValue:
    x: Any = field(default_factory=IllegalType)


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
        (Path, True),
        (Any, True),
        (_TestEnum, True),
        (_TestUserClass, False),
        # Nesting structured configs in contain
        (_TestAttrsClass, True),
        (_TestDataclass, True),
        # container annotations
        (List[int], True),
        (Dict[str, int], True),
        # optional and union
        (Optional[int], True),
        (Union[int, str], True),
        (Union[int, List[str]], False),
        (Union[int, Dict[int, str]], False),
        (Union[int, _TestEnum], True),
        (Union[int, _TestAttrsClass], False),
        (Union[int, _TestDataclass], False),
        (Union[int, _TestUserClass], False),
    ],
)
def test_is_valid_value_annotation(type_: type, expected: bool) -> None:
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
        assert d["p"] == Path("hello.txt")
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
        assert field_names == ["x", "s", "b", "p", "d", "f", "e", "list1", "dict1"]

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
        (Path("hello.txt"), _utils.ValueKind.VALUE),
        (True, _utils.ValueKind.VALUE),
        (False, _utils.ValueKind.VALUE),
        (Color.GREEN, _utils.ValueKind.VALUE),
        (Dataclass, _utils.ValueKind.VALUE),
        (Dataframe(), _utils.ValueKind.VALUE),
        (IntegerNode(123), _utils.ValueKind.VALUE),
        (DictConfig({}), _utils.ValueKind.VALUE),
        (ListConfig([]), _utils.ValueKind.VALUE),
        (AnyNode(123), _utils.ValueKind.VALUE),
        (UnionNode(123, Union[int, str]), _utils.ValueKind.VALUE),
        ("???", _utils.ValueKind.MANDATORY_MISSING),
        (IntegerNode("???"), _utils.ValueKind.MANDATORY_MISSING),
        (DictConfig("???"), _utils.ValueKind.MANDATORY_MISSING),
        (ListConfig("???"), _utils.ValueKind.MANDATORY_MISSING),
        (AnyNode("???"), _utils.ValueKind.MANDATORY_MISSING),
        (UnionNode("???", Union[int, str]), _utils.ValueKind.MANDATORY_MISSING),
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
        param(
            UnionNode("${func:c:\\a\\b}", Union[int, str]),
            _utils.ValueKind.INTERPOLATION,
            id="unionnode-interp",
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
        unode1 = cfg1._get_node("union")
        assert unode1._get_parent() == cfg1  # type: ignore
        assert unode1._value()._get_parent() == unode1  # type: ignore

    cfg = OmegaConf.create({})
    assert isinstance(cfg, DictConfig)
    cfg.str = StringNode("str")
    cfg.list = [1]
    cfg.union = UnionNode(123, Union[int, str])

    validate(cfg)

    cfg._get_node("str")._set_parent(None)  # type: ignore
    cfg._get_node("list")._set_parent(None)  # type: ignore
    cfg.list._get_node(0)._set_parent(None)  # type:ignore
    unode = cfg._get_node("union")
    unode._set_parent(None)  # type: ignore
    unode._value()._set_parent(None)  # type: ignore
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
    dt = Dict[key_type, value_type]
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
        (Path, True),
        (NoneType, True),
        (Color, True),
        (list, False),
        (ListConfig, False),
        (dict, False),
        (DictConfig, False),
    ],
)
def test_is_primitive_type_annotation(type_: Any, is_primitive: bool) -> None:
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
        (Path, False, "Path"),
        (Path, True, "pathlib.Path"),
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
        (dict, False, "dict"),
        (dict, True, "dict"),
        (List[str], False, "List[str]"),
        (List[str], True, "List[str]"),
        (List[Color], False, "List[Color]"),
        (List[Color], True, "List[tests.Color]"),
        (List[Dict[str, Color]], False, "List[Dict[str, Color]]"),
        (List[Dict[str, Color]], True, "List[Dict[str, tests.Color]]"),
        (list, False, "list"),
        (list, True, "list"),
        (Tuple[str], False, "Tuple[str]"),
        (Tuple[str], True, "Tuple[str]"),
        (Tuple[str, int], False, "Tuple[str, int]"),
        (Tuple[str, int], True, "Tuple[str, int]"),
        (Tuple[float, ...], False, "Tuple[float, ...]"),
        (Tuple[float, ...], True, "Tuple[float, ...]"),
        (tuple, False, "tuple"),
        (tuple, True, "tuple"),
        (Union[str, int, Color], False, "Union[str, int, Color]"),
        (Union[str, int, Color], True, "Union[str, int, tests.Color]"),
        (Union[int], False, "int"),
        (Union[int], True, "int"),
        (IllegalType, False, "IllegalType"),
        (IllegalType, True, "tests.IllegalType"),
        (IllegalTypeGeneric, False, "IllegalTypeGeneric"),
        (IllegalTypeGeneric, True, "tests.IllegalTypeGeneric"),
        (IllegalTypeGeneric[int], False, "IllegalTypeGeneric[int]"),
        (IllegalTypeGeneric[int], True, "tests.IllegalTypeGeneric[int]"),
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


@mark.parametrize(
    "type_, expected",
    [
        (object(), r"<object object at 0x[a-fA-F0-9]*>"),
        (IllegalType(), "<tests.IllegalType object at 0x[a-fA-F0-9]*>"),
    ],
)
def test_type_str_regex(type_: Any, expected: str) -> None:
    assert re.match(expected, _utils.type_str(type_))


def test_type_str_ellipsis() -> None:
    assert _utils.type_str(...) == "..."


@mark.parametrize(
    "type_, expected",
    [
        param(None, "NoneType", id="none"),
        param(NoneType, "NoneType", id="nonetype"),
        (Union[float, bool, None], "Optional[Union[float, bool]]"),
        (Union[float, bool, NoneType], "Optional[Union[float, bool]]"),
        (object, "object"),
        (Optional[object], "Optional[object]"),
    ],
)
def test_type_str_nonetype(type_: Any, expected: str) -> None:
    assert _utils.type_str(type_) == expected


@mark.parametrize(
    "obj, expected",
    [
        param([], True, id="list"),
        param([1], True, id="list1"),
        param((), True, id="tuple"),
        param((1,), True, id="tuple1"),
        param({}, False, id="dict"),
        param(ListSubclass(), True, id="list_subclass"),
        param(Shape(10, 2, 3), True, id="namedtuple"),
    ],
)
def test_is_primitive_list(obj: Any, expected: bool) -> None:
    assert is_primitive_list(obj) == expected


@mark.parametrize(
    "obj, expected",
    [
        param({}, True, id="dict"),
        param({1: 2}, True, id="dict1"),
        param([], False, id="list"),
        param((), False, id="tuple"),
    ],
)
def test_is_primitive_dict(obj: Any, expected: bool) -> None:
    assert is_primitive_dict(obj) == expected


@mark.parametrize(
    "obj",
    [
        param(DictConfig({}), id="dictconfig"),
        param(ListConfig([]), id="listconfig"),
        param(DictSubclass(), id="dict_subclass"),
        param(Str2Int(), id="dict_subclass_dataclass"),
        param(User, id="user"),
        param(User("bond", 7), id="user"),
    ],
)
class TestIsPrimitiveContainerNegative:
    def test_is_primitive_list(self, obj: Any) -> None:
        assert not is_primitive_list(obj)

    def test_is_primitive_dict(self, obj: Any) -> None:
        assert not is_primitive_dict(obj)


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
        (Str2Int, True),
        (Str2Int(), False),
        (User, False),
        (User(), False),
        (List, False),
        (dict, True),
        (DictConfig, False),
        (Any, False),
        (None, False),
        (NoneType, False),
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
        (list, True),
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
        (list, False),
        (dict, False),
        (tuple, True),
        (Any, False),
        (int, False),
        (User, False),
        (None, False),
        (NoneType, False),
    ],
)
def test_is_tuple_annotation(type_: Any, expected: Any) -> Any:
    assert is_tuple_annotation(type_=type_) == expected


@mark.parametrize(
    "input_, expected",
    [
        (Union[int, str], True),
        (Union[int, List[str]], True),
        (Optional[Union[int, str]], True),
        (Union[int, None], True),
        (Optional[int], True),
        (Any, False),
        (int, False),
        (User, False),
        (None, False),
        (NoneType, False),
    ],
)
def test_is_union_annotation(input_: Any, expected: bool) -> None:
    assert is_union_annotation(input_) == expected


@mark.skipif(sys.version_info < (3, 10), reason="requires Python 3.10 or newer")
def test_is_union_annotation_PEP604() -> None:
    if sys.version_info >= (3, 10):  # this if-statement is for mypy's benefit
        assert is_union_annotation(int | str)


@mark.parametrize(
    "input_, expected",
    [
        (Union[int, str], True),
        (Union[int, List[str]], False),
        (Union[int, Dict[str, int]], False),
        (Union[int, User], False),
        (Optional[Union[int, str]], True),
        (Union[int, None], True),
        (Optional[int], True),
        (Any, False),
        (int, False),
        (User, False),
        (None, False),
        (NoneType, False),
    ],
)
def test_is_supported_union_annotation(input_: Any, expected: bool) -> None:
    assert is_supported_union_annotation(input_) == expected


@mark.parametrize(
    "obj, expected",
    [
        # Unwrapped values
        param(10, Any, id="int"),
        param(10.0, Any, id="float"),
        param(True, Any, id="bool"),
        param(Color.RED, Any, id="enum"),
        param(b"binary", Any, id="bytes"),
        param(Path("hello.txt"), Any, id="path"),
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
        param(
            OmegaConf.structured(UnionAnnotations), "ubf", Union[bool, float], id="ubf"
        ),
        param(
            OmegaConf.structured(UnionAnnotations),
            "oubf",
            Optional[Union[bool, float]],
            id="oubf",
        ),
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
    result = _get_value(val_node)
    assert result == value


@mark.parametrize(
    "content",
    [{"a": 0, "b": 1}, "???", None, "${bar}"],
)
def test_get_value_container(content: Any) -> None:
    cfg = DictConfig({})
    cfg._set_value(content)
    assert _get_value(cfg) == content


@mark.parametrize(
    "node, expected",
    [
        param(AnyNode(123), 123, id="anynode"),
        param(IntegerNode(123), 123, id="integernode"),
        param(ListConfig([1, 2, 3]), ListConfig([1, 2, 3]), id="listconfig"),
        param(123, 123, id="int"),
        param("${a}", "${a}", id="raw-interp"),
        param(DictConfig("${a}"), "${a}", id="dict-interp"),
        param(AnyNode("${a}"), "${a}", id="any-interp"),
        param(IntegerNode("${a}"), "${a}", id="int-interp"),
        param(UnionNode("${a}", Union[int, str]), "${a}", id="union-interp"),
        param(DictConfig("???"), "???", id="dict-missing"),
        param(AnyNode("???"), "???", id="any-missing"),
        param(IntegerNode("???"), "???", id="int-missing"),
        param(UnionNode("???", Union[int, str]), "???", id="union-missing"),
        param(DictConfig(None), None, id="dict-none"),
        param(AnyNode(None), None, id="any-none"),
        param(IntegerNode(None), None, id="int-none"),
        param(UnionNode(None, Union[int, str]), None, id="union-none"),
        param(DictConfig({"foo": "bar"}), DictConfig({"foo": "bar"}), id="dictconfig"),
        param(UnionNode(123, Union[int, str]), 123, id="union[int]"),
    ],
)
def test_get_value_of_node_subclass(node: Node, expected: Any) -> None:
    result = _get_value(node)
    assert result == expected
    assert type(result) == type(expected)


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
        (
            lambda is_optional, missing: UnionNode(
                ref_type=Union[int, str],
                content=123 if not missing else "???",
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
    "type_",
    [
        param(lambda val=123: val, id="passthrough"),
        param(lambda val=123: AnyNode(val), id="any_node"),
        param(lambda val=123: IntegerNode(val), id="integer_node"),
        param(lambda val={}: DictConfig(val), id="dict_config"),
        param(lambda val=[]: ListConfig(val), id="list_config"),
        param(lambda val=123: UnionNode(val, Union[int, str]), id="union_node"),
    ],
)
class TestIndicators:
    @mark.parametrize(
        "input_, expected",
        [
            param("???", True, id="missing"),
            param("${interp}", False, id="interp"),
            param(None, False, id="none"),
            param("DEFAULT", False, id="default"),
        ],
    )
    def test_is_missing(
        self, type_: Callable[..., Any], input_: Any, expected: bool
    ) -> None:
        value = type_(input_) if input_ != "DEFAULT" else type_()
        assert _utils._is_missing_value(value) == expected

    @mark.parametrize(
        "input_, expected",
        [
            param("???", False, id="missing"),
            param("${interp}", True, id="interp"),
            param(None, False, id="none"),
            param("DEFAULT", False, id="default"),
        ],
    )
    def test_is_interpolation(
        self, type_: Callable[..., Any], input_: Any, expected: bool
    ) -> None:
        value = type_(input_) if input_ != "DEFAULT" else type_()
        assert _utils._is_interpolation(value) == expected

    @mark.parametrize(
        "input_, expected",
        [
            param("???", False, id="missing"),
            param("${interp}", False, id="interp"),
            param(None, True, id="none"),
            param("DEFAULT", False, id="default"),
        ],
    )
    def test_is_none(
        self, type_: Callable[..., Any], input_: Any, expected: bool
    ) -> None:
        value = type_(input_) if input_ != "DEFAULT" else type_()
        assert _utils._is_none(value) == expected

    @mark.parametrize(
        "input_, expected",
        [
            param("???", True, id="missing"),
            param("${interp}", True, id="interp"),
            param(None, True, id="none"),
            param("DEFAULT", False, id="default"),
        ],
    )
    def test_is_special(
        self, type_: Callable[..., Any], input_: Any, expected: bool
    ) -> None:
        value = type_(input_) if input_ != "DEFAULT" else type_()
        assert _utils._is_special(value) == expected


@mark.parametrize(
    "ref_type, expected_key_type, expected_element_type",
    [
        param(dict, Any, Any, id="Dict_no_subscript"),
        param(Dict, Any, Any, id="dict_no_subscript"),
        param(Dict[Any, Any], Any, Any, id="any_explicit"),
        param(Dict[int, float], int, float, id="Dict_int_float"),
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


@mark.skipif(sys.version_info < (3, 9), reason="requires Python 3.9 or newer")
def test_get_dict_key_value_types_python_3_10() -> None:
    if sys.version_info >= (3, 9):  # this if-statement is for mypy's benefit
        key_type, element_type = get_dict_key_value_types(dict[int, float])
        assert key_type == int
        assert element_type == float


@mark.parametrize(
    "ref_type, expected_element_type",
    [
        param(list, Any, id="list_no_subscript"),
        param(List, Any, id="List_no_subscript"),
        param(List[Any], Any, id="any_explicit"),
        param(List[int], int, id="List_int"),
        param(List[User], User, id="user"),
        param(List[List[int]], List[int], id="list"),
        param(List[Dict[int, float]], Dict[int, float], id="dict"),
    ],
)
def test_get_list_element_type(ref_type: Any, expected_element_type: Any) -> None:
    assert get_list_element_type(ref_type) == expected_element_type


@mark.skipif(sys.version_info < (3, 9), reason="requires Python 3.9 or newer")
def test_get_list_element_type_python_3_10() -> None:
    if sys.version_info >= (3, 9):  # this if-statement is for mypy's benefit
        assert get_list_element_type(list[int]) == int


@mark.parametrize(
    "ref_type, expected_element_type",
    [
        param(tuple, (Any, ...), id="tuple_no_subscript"),
        param(Tuple, (Any, ...), id="Tuple_no_subscript"),
        param(Tuple[Any], (Any,), id="any_explicit"),
        param(Tuple[int], (int,), id="Tuple_int"),
        param(Tuple[int, str], (int, str), id="Tuple[int,str]"),
        param(Tuple[int, ...], (int, ...), id="Tuple[int,...]"),
        param(Tuple[User], (User,), id="user"),
        param(Tuple[Tuple[int]], (Tuple[int],), id="tuple"),
        param(Tuple[Dict[int, float]], (Dict[int, float],), id="dict"),
    ],
)
def test_get_tuple_item_types(ref_type: Any, expected_element_type: Any) -> None:
    assert get_tuple_item_types(ref_type) == expected_element_type


if sys.version_info >= (3, 9):

    @mark.parametrize(
        "ref_type, expected_element_type",
        [
            param(tuple[int], (int,), id="tuple_int"),
            param(tuple[int, str], (int, str), id="tuple[int,str]"),
            param(tuple[int, ...], (int, ...), id="tuple[int,...]"),
        ],
    )
    def test_get_tuple_item_types_python_3_9(
        ref_type: Any, expected_element_type: Any
    ) -> None:
        assert get_tuple_item_types(ref_type) == expected_element_type


@mark.parametrize(
    "type_, expected_optional, expected_type",
    [
        param(int, False, int, id="int"),
        param(Any, True, Any, id="any"),
        param(Color, False, Color, id="color"),
        param(Optional[str], True, str, id="str"),
        param(Optional[Any], True, Any, id="o[any]"),
        param(Union[int, str], False, Union[int, str], id="int-str"),
        param(Union[str, int], False, Union[str, int], id="str-int"),
        param(Dict[str, int], False, Dict[str, int], id="dict[str,int]"),
        param(Dict, False, Dict, id="dict"),
        param(Dict[Any, Any], False, Dict[Any, Any], id="dict[any,any]"),
        param(Optional[Dict[str, int]], True, Dict[str, int], id="o[dict[str,int]]"),
        param(Optional[Dict], True, Dict, id="dict"),
        param(
            Dict[str, Optional[int]],
            False,
            Dict[str, Optional[int]],
            id="dict[str,o[int]]",
        ),
        param(Union[int, None], True, int, id="int-none"),
        param(Union[int, NoneType], True, int, id="int-nonetype"),
        param(Union[Optional[int], None], True, int, id="o[int]-none"),
        param(Union[Any, None], True, Any, id="any-none"),
        param(Union[None, int], True, int, id="none-int"),
        param(Union[None, None], True, NoneType, id="none-none"),
        param(Union[None, NoneType], True, NoneType, id="none-nonetype"),
        param(Union[None, Optional[None]], True, NoneType, id="none-o[none]"),
        param(None, True, NoneType, id="none"),
        param(NoneType, True, NoneType, id="nonetype"),
        param(Union[int, int], False, int, id="int-int"),
        param(Union[int, Optional[int]], True, int, id="int-o[int]"),
        param(Union[int], False, int, id="u[int]"),
        param(Union[Optional[int]], True, int, id="u[o[int]]"),
        param(Optional[Union[int]], True, int, id="o[u[int]]"),
        param(Union[int, Optional[str]], True, Union[int, str], id="int-o[str]"),
        param(Optional[Optional[int]], True, int, id="o[o[int]]"),
        param(Optional[Optional[Any]], True, Any, id="o[o[any]]"),
        param(User, False, User, id="user"),
        param(Optional[User], True, User, id="o[user]"),
        param(Union[User, int], False, Union[User, int], id="user-int"),
        param(Optional[Union[User, int]], True, Union[User, int], id="o[user-int]"),
        param(Union[Optional[User], int], True, Union[User, int], id="o[user]-int"),
        param(Union[User, Optional[int]], True, Union[User, int], id="user-o[int]"),
        param(Optional[Union[int, str]], True, Union[int, str], id="o[u[int-str]]"),
        param(Union[Optional[int], str], True, Union[int, str], id="u[o[int]-str]]"),
        param(
            Optional[Union[Optional[int], str]],
            True,
            Union[int, str],
            id="o[u[o[int]-str]]]",
        ),
        param(
            Union[Optional[int], Optional[str]],
            True,
            Union[int, str],
            id="u[o[int]-o[str]]]",
        ),
        param(Union[int, str, None], True, Union[int, str], id="u[int-str-none]"),
        param(Union[int, str, None], True, Union[int, str], id="u[int-str-nonetype]"),
        param(
            Union[User, Union[int, str]],
            False,
            Union[User, int, str],
            id="user-[int-str]",
        ),
        param(
            Union[User, NoneType, Union[int, str]],
            True,
            Union[User, int, str],
            id="user-nonetype-[int-str]",
        ),
        param(
            Union[User, None, Union[int, str]],
            True,
            Union[User, int, str],
            id="user-none-[int-str]",
        ),
        param(
            Union[User, None, Union[Optional[int], str]],
            True,
            Union[User, int, str],
            id="user-none-[o[int]-str]",
        ),
        param(
            Union[User, Union[Optional[int], str]],
            True,
            Union[User, int, str],
            id="user-none-[o[int]-str]",
        ),
        param(
            Union[float, bool, None], True, Union[float, bool], id="u[float-bool-none]"
        ),
        param(
            Union[float, bool, NoneType],
            True,
            Union[float, bool],
            id="u[float-bool-nonetype]",
        ),
    ],
)
def test_resolve_optional(
    type_: Any, expected_optional: bool, expected_type: Any
) -> None:
    resolved_optional, resolved_type = _resolve_optional(type_)
    assert resolved_optional == expected_optional
    assert resolved_type == expected_type


@mark.skipif(sys.version_info < (3, 10), reason="requires Python 3.10 or newer")
def test_resolve_optional_support_pep_604() -> None:
    if sys.version_info >= (3, 10):  # this if-statement is for mypy's benefit
        assert _resolve_optional(int | str) == (False, Union[int, str])
        assert _resolve_optional(Optional[int | str]) == (True, Union[int, str])
        assert _resolve_optional(int | Optional[str]) == (True, Union[int, str])
        assert _resolve_optional(int | Union[str, float]) == (
            False,
            Union[int, str, float],
        )
        assert _resolve_optional(int | Union[str, Optional[float]]) == (
            True,
            Union[int, str, float],
        )
        assert _resolve_optional(int | str | None) == (True, Union[int, str])
        assert _resolve_optional(int | str | NoneType) == (True, Union[int, str])


@mark.parametrize(
    "type_, expected",
    [
        param(int, int, id="int"),
        param(tuple, Tuple[Any, ...], id="tuple"),
        param(Tuple, Tuple[Any, ...], id="Tuple"),
        param(Tuple[int], Tuple[int], id="Tuple[int]"),
        param(Tuple["int"], Tuple[int], id="Tuple[int]_forward"),
        param(Tuple[int, str], Tuple[int, str], id="Tuple[int,str]"),
        param(Tuple["int", "str"], Tuple[int, str], id="Tuple[int,str]_forward"),
        param(Tuple[int, ...], Tuple[int, ...], id="Tuple[int,...]"),
        param(dict, Dict[Any, Any], id="dict"),
        param(Dict, Dict[Any, Any], id="Dict"),
        param(Dict[int, str], Dict[int, str], id="Dict[int,str]"),
        param(Dict["int", "str"], Dict[int, str], id="Dict[int,str]_forward"),
        param(list, List[Any], id="list"),
        param(List, List[Any], id="List"),
        param(List[int], List[int], id="List[int]"),
        param(List["int"], List[int], id="List[int]_forward"),
    ],
)
def test_resolve_forward(type_: Any, expected: Any) -> None:
    assert _resolve_forward(type_, "builtins") == expected
