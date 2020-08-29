import copy
from enum import Enum
from typing import Any, Dict, Tuple, Type

import pytest

from omegaconf import (
    AnyNode,
    BooleanNode,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    OmegaConf,
    StringNode,
    ValueNode,
)
from omegaconf.errors import ValidationError

from . import Color, IllegalType, User


# testing valid conversions
@pytest.mark.parametrize(  # type: ignore
    "type_,input_,output_",
    [
        # string
        (StringNode, "abc", "abc"),
        (StringNode, 100, "100"),
        # integer
        (IntegerNode, 10, 10),
        (IntegerNode, "10", 10),
        (IntegerNode, -100, -100),
        (IntegerNode, "-100", -100),
        # float
        (FloatNode, float("inf"), float("inf")),
        # Yes, we treat nan as equal to nan in OmegaConf
        (FloatNode, float("nan"), float("nan")),
        (FloatNode, 10, 10.0),
        (FloatNode, 10.1, 10.1),
        (FloatNode, "10.2", 10.2),
        (FloatNode, "10e-3", 10e-3),
        # bool true
        (BooleanNode, True, True),
        (BooleanNode, "Y", True),
        (BooleanNode, "true", True),
        (BooleanNode, "Yes", True),
        (BooleanNode, "On", True),
        (BooleanNode, "1", True),
        (BooleanNode, 100, True),
        # bool false
        (BooleanNode, False, False),
        (BooleanNode, "N", False),
        (BooleanNode, "false", False),
        (BooleanNode, "No", False),
        (BooleanNode, "Off", False),
        (BooleanNode, None, None),
        (BooleanNode, "0", False),
        (BooleanNode, 0, False),
        # any
        (AnyNode, 3, 3),
        (AnyNode, 3.14, 3.14),
        (AnyNode, False, False),
        (AnyNode, Color.RED, Color.RED),
        (AnyNode, None, None),
        # Enum node
        (lambda v: EnumNode(enum_type=Color, value=v), Color.RED, Color.RED),
        (lambda v: EnumNode(enum_type=Color, value=v), "Color.RED", Color.RED),
        (lambda v: EnumNode(enum_type=Color, value=v), "RED", Color.RED),
        (lambda v: EnumNode(enum_type=Color, value=v), 1, Color.RED),
    ],
)
def test_valid_inputs(type_: type, input_: Any, output_: Any) -> None:
    node = type_(input_)
    assert node == output_
    assert node == node
    assert not (node != output_)
    assert not (node != node)
    assert str(node) == str(output_)


# testing invalid conversions
@pytest.mark.parametrize(  # type: ignore
    "type_,input_",
    [
        (IntegerNode, "abc"),
        (IntegerNode, 10.1),
        (IntegerNode, "-1132c"),
        (FloatNode, "abc"),
        (IntegerNode, "-abc"),
        (BooleanNode, "Nope"),
        (BooleanNode, "Yup"),
        (StringNode, [1, 2]),
        (StringNode, ListConfig([1, 2])),
        (StringNode, {"foo": "var"}),
        (FloatNode, DictConfig({"foo": "var"})),
        (IntegerNode, [1, 2]),
        (IntegerNode, ListConfig([1, 2])),
        (IntegerNode, {"foo": "var"}),
        (IntegerNode, DictConfig({"foo": "var"})),
        (BooleanNode, [1, 2]),
        (BooleanNode, ListConfig([1, 2])),
        (BooleanNode, {"foo": "var"}),
        (BooleanNode, DictConfig({"foo": "var"})),
        (FloatNode, [1, 2]),
        (FloatNode, ListConfig([1, 2])),
        (FloatNode, {"foo": "var"}),
        (FloatNode, DictConfig({"foo": "var"})),
        (AnyNode, [1, 2]),
        (AnyNode, ListConfig([1, 2])),
        (AnyNode, {"foo": "var"}),
        (AnyNode, DictConfig({"foo": "var"})),
        (AnyNode, IllegalType()),
    ],
)
def test_invalid_inputs(type_: type, input_: Any) -> None:
    empty_node = type_()

    with pytest.raises(ValidationError):
        empty_node._set_value(input_)
    with pytest.raises(ValidationError):
        type_(input_)


@pytest.mark.parametrize(  # type: ignore
    "input_, expected_type",
    [
        ({}, DictConfig),
        ([], ListConfig),
        (5, AnyNode),
        (5.0, AnyNode),
        (True, AnyNode),
        (False, AnyNode),
        ("str", AnyNode),
    ],
)
def test_assigned_value_node_type(input_: type, expected_type: Any) -> None:
    c = OmegaConf.create()
    assert isinstance(c, DictConfig)
    c.foo = input_
    assert type(c._get_node("foo")) == expected_type


# dict
def test_dict_any() -> None:
    c = OmegaConf.create()
    assert isinstance(c, DictConfig)
    # default type is Any
    c.foo = 10
    c[Enum1.FOO] = "bar"

    assert c.foo == 10
    assert type(c._get_node("foo")) == AnyNode
    c.foo = "string"
    assert c.foo == "string"

    assert type(c._get_node(Enum1.FOO)) == AnyNode


def test_dict_integer_1() -> None:
    c = OmegaConf.create()
    assert isinstance(c, DictConfig)
    c.foo = IntegerNode(10)
    assert type(c._get_node("foo")) == IntegerNode
    assert c.foo == 10


# list
def test_list_any() -> None:
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)
    # default type is Any
    c.append(10)
    assert c[0] == 10
    assert type(c._get_node(0)) == AnyNode
    c[0] = "string"
    assert c[0] == "string"


def test_list_integer() -> None:
    val = 10
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)
    c.append(IntegerNode(val))
    assert type(c._get_node(0)) == IntegerNode
    assert c.get(0) == val


def test_list_integer_rejects_string() -> None:
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)
    c.append(IntegerNode(10))
    assert c.get(0) == 10
    with pytest.raises(ValidationError):
        c[0] = "string"
    assert c[0] == 10
    assert type(c._get_node(0)) == IntegerNode


# Test merge raises validation error
@pytest.mark.parametrize(  # type: ignore
    "c1, c2",
    [
        (dict(a=IntegerNode(10)), dict(a="str")),
        (dict(a=IntegerNode(10)), dict(a=StringNode("str"))),
        (dict(a=10, b=IntegerNode(10)), dict(a=20, b="str")),
        (dict(foo=dict(bar=IntegerNode(10))), dict(foo=dict(bar="str"))),
    ],
)
def test_merge_validation_error(c1: Dict[str, Any], c2: Dict[str, Any]) -> None:
    conf1 = OmegaConf.create(c1)
    conf2 = OmegaConf.create(c2)
    with pytest.raises(ValidationError):
        OmegaConf.merge(conf1, conf2)
    # make sure that conf1 and conf2 were not modified
    assert conf1 == OmegaConf.create(c1)
    assert conf2 == OmegaConf.create(c2)


@pytest.mark.parametrize(  # type: ignore
    "type_,valid_value, invalid_value",
    [
        (IntegerNode, 1, "invalid"),
        (FloatNode, 3.1415, "invalid"),
        (BooleanNode, True, "invalid"),
        (AnyNode, "aaa", None),
        (StringNode, "blah", None),
    ],
)
def test_accepts_mandatory_missing(
    type_: type, valid_value: Any, invalid_value: Any
) -> None:
    node = type_()
    node._set_value("???")
    assert node._value() == "???"

    conf = OmegaConf.create({"foo": node})
    assert isinstance(conf, DictConfig)
    assert "foo" not in conf
    assert type(conf._get_node("foo")) == type_

    conf.foo = valid_value
    # make sure valid assignment does not change the type
    assert type(conf._get_node("foo")) == type_
    assert "foo" in conf
    assert conf.foo == valid_value

    if invalid_value is not None:
        with pytest.raises(ValidationError):
            conf.foo = invalid_value


class Enum1(Enum):
    FOO = 1
    BAR = 2


class Enum2(Enum):
    NOT_FOO = 1
    NOT_BAR = 2


@pytest.mark.parametrize(  # type: ignore
    "type_", [BooleanNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode]
)
@pytest.mark.parametrize(  # type: ignore
    "values, success_map",
    [
        (
            # True aliases
            (True, "Y", "true", "yes", "on"),
            {
                "BooleanNode": True,  # noqa F601
                "StringNode": str,  # noqa F601
                "AnyNode": copy.copy,  # noqa F601
            },
        ),
        (
            ("1", 1, 10, -10),
            {
                "BooleanNode": True,  # noqa F601
                "IntegerNode": int,  # noqa F601
                "FloatNode": float,  # noqa F601
                "StringNode": str,  # noqa F601
                "AnyNode": copy.copy,  # noqa F601
            },
        ),
        (
            # Floaty things
            ("1.0", 1.0, float("inf"), float("-inf"), "10e-3", 10e-3),
            {"FloatNode": float, "StringNode": str, "AnyNode": copy.copy},
        ),
        (
            # False aliases
            (False, "N", "false", "no", "off"),
            {
                "BooleanNode": False,  # noqa F601
                "StringNode": str,  # noqa F601
                "AnyNode": copy.copy,  # noqa F601
            },
        ),
        (
            # Falsy integers
            ("0", 0),
            {
                "BooleanNode": False,  # noqa F601
                "IntegerNode": 0,  # noqa F601
                "FloatNode": 0.0,  # noqa F601
                "StringNode": str,  # noqa F601
                "AnyNode": copy.copy,  # noqa F601
            },
        ),
    ],
)
def test_legal_assignment(
    type_: type, values: Any, success_map: Dict[Any, Dict[str, Any]]
) -> None:

    if not isinstance(values, (list, tuple)):
        values = [values]

    for value in values:
        if type_.__name__ in success_map.keys():
            expected = success_map[type_.__name__]
            if callable(expected):
                expected = expected(value)
            node = type_(value)
            assert node._value() == expected
        else:
            with pytest.raises(ValidationError):
                type_(value)


@pytest.mark.parametrize(  # type: ignore
    "node,value",
    [
        (IntegerNode(), "foo"),
        (BooleanNode(), "foo"),
        (FloatNode(), "foo"),
        (EnumNode(enum_type=Enum1), "foo"),
    ],
)
def test_illegal_assignment(node: ValueNode, value: Any) -> None:
    with pytest.raises(ValidationError):
        node._set_value(value)


@pytest.mark.parametrize(  # type: ignore
    "node_type", [BooleanNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode]
)
@pytest.mark.parametrize(  # type: ignore
    "enum_type, values, success_map",
    [
        (
            Enum1,
            (Enum1.FOO, "Enum1.FOO", "FOO", 1),
            {EnumNode: Enum1.FOO, AnyNode: copy.copy, StringNode: str},
        )
    ],
)
def test_legal_assignment_enum(
    node_type: Type[EnumNode],
    enum_type: Type[Enum],
    values: Tuple[Any],
    success_map: Dict[Any, Any],
) -> None:
    assert isinstance(values, (list, tuple))

    for value in values:
        if node_type in success_map.keys():
            expected = success_map[node_type]
            if callable(expected):
                expected = expected(value)
            node = node_type(enum_type)
            node._set_value(value)
            assert node._value() == expected
        else:
            with pytest.raises(ValidationError):
                node_type(enum_type)


class DummyEnum(Enum):
    FOO = 1


@pytest.mark.parametrize("is_optional", [True, False])  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "ref_type, type_, value, expected_type",
    [
        (Any, Any, 10, AnyNode),
        (DummyEnum, DummyEnum, DummyEnum.FOO, EnumNode),
        (int, int, 42, IntegerNode),
        (float, float, 3.1415, FloatNode),
        (bool, bool, True, BooleanNode),
        (str, str, "foo", StringNode),
    ],
)
def test_node_wrap(
    ref_type: type, type_: type, is_optional: bool, value: Any, expected_type: Any
) -> None:
    from omegaconf.omegaconf import _node_wrap

    ret = _node_wrap(
        ref_type=Any,
        type_=type_,
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
            ref_type=Any,
            type_=type_,
            value=None,
            is_optional=is_optional,
            parent=None,
            key=None,
        )
        assert type(ret) == expected_type
        # noinspection PyComparisonWithNone
        assert ret == None  # noqa E711


def test_node_wrap_illegal_type() -> None:
    class UserClass:
        pass

    from omegaconf.omegaconf import _node_wrap

    with pytest.raises(ValidationError):
        _node_wrap(
            type_=UserClass, value=UserClass(), is_optional=False, parent=None, key=None
        )


@pytest.mark.parametrize(  # type: ignore
    "obj",
    [
        StringNode(),
        StringNode(value="foo"),
        StringNode(value="foo", is_optional=False),
        BooleanNode(value=True),
        IntegerNode(value=10),
        FloatNode(value=10.0),
        OmegaConf.create({}),
        OmegaConf.create([]),
        OmegaConf.create({"foo": "foo"}),
    ],
)
def test_deepcopy(obj: Any) -> None:
    cp = copy.deepcopy(obj)
    assert cp == obj
    assert id(cp) != id(obj)
    assert obj.__dict__.keys() == cp.__dict__.keys()
    for k in obj.__dict__.keys():
        assert obj.__dict__[k] == cp.__dict__[k]


@pytest.mark.parametrize(  # type: ignore
    "node, value, expected",
    [
        (StringNode(), None, True),
        (StringNode(), 100, False),
        (StringNode("foo"), "foo", True),
        (IntegerNode(), 1, False),
        (IntegerNode(1), 1, True),
        (IntegerNode(1), "foo", False),
        (FloatNode(), 1, False),
        (FloatNode(), None, True),
        (FloatNode(1.0), None, False),
        (FloatNode(1.0), 1.0, True),
        (FloatNode(1), 1, True),
        (FloatNode(1.0), "foo", False),
        (BooleanNode(), True, False),
        (BooleanNode(), False, False),
        (BooleanNode(), None, True),
        (BooleanNode(True), None, False),
        (BooleanNode(True), False, False),
        (BooleanNode(False), False, True),
        (AnyNode(value=1, is_optional=True), AnyNode(value=1, is_optional=True), True),
        (
            AnyNode(value=1, is_optional=True),
            AnyNode(value=1, is_optional=False),
            True,
        ),
        (EnumNode(enum_type=Enum1), Enum1.BAR, False),
        (EnumNode(enum_type=Enum1), EnumNode(Enum1), True),
        (EnumNode(enum_type=Enum1), "nope", False),
        (
            EnumNode(enum_type=Enum1, value=Enum1.BAR),
            EnumNode(enum_type=Enum1, value=Enum1.BAR),
            True,
        ),
        (EnumNode(enum_type=Enum1, value=Enum1.BAR), Enum1.BAR, True),
    ],
)
def test_eq(node: ValueNode, value: Any, expected: Any) -> None:
    assert (node == value) == expected
    assert (node != value) != expected
    assert (value == node) == expected
    assert (value != node) != expected
    assert (node.__hash__() == value.__hash__()) == expected


@pytest.mark.parametrize("value", [1, 3.14, True, None, Enum1.FOO])  # type: ignore
def test_set_anynode_with_primitive_type(value: Any) -> None:
    cfg = OmegaConf.create({"a": 5})
    a_before = cfg._get_node("a")
    cfg.a = value
    # changing anynode's value with a primitive type should set value
    assert id(cfg._get_node("a")) == id(a_before)
    assert cfg.a == value


@pytest.mark.parametrize(  # type: ignore
    "value, container_type",
    [
        (ListConfig(content=[1, 2]), ListConfig),
        ([1, 2], ListConfig),
        (DictConfig(content={"foo": "var"}), DictConfig),
        ({"foo": "var"}, DictConfig),
    ],
)
def test_set_anynode_with_container(value: Any, container_type: Any) -> None:
    cfg = OmegaConf.create({"a": 5})
    a_before = cfg._get_node("a")
    cfg.a = value
    # changing anynode's value with a container should wrap a new node
    assert id(cfg._get_node("a")) != id(a_before)
    assert isinstance(cfg.a, container_type)
    assert cfg.a == value


def test_set_anynode_with_illegal_type() -> None:
    cfg = OmegaConf.create({"a": 5})
    with pytest.raises(ValidationError):
        cfg.a = IllegalType()


def test_set_valuenode() -> None:
    cfg = OmegaConf.structured(User)
    a_before = cfg._get_node("age")
    cfg.age = 12
    assert id(cfg._get_node("age")) == id(a_before)
    with pytest.raises(ValidationError):
        cfg.age = []
