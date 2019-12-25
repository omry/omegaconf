import copy
from enum import Enum
from typing import Any

import pytest

from omegaconf import (
    StringNode,
    IntegerNode,
    EnumNode,
    FloatNode,
    BooleanNode,
    AnyNode,
    ListConfig,
    DictConfig,
    OmegaConf,
)

# noinspection PyProtectedMember
from omegaconf.errors import ValidationError


# testing valid conversions
@pytest.mark.parametrize(
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
    ],
)
def test_valid_inputs(type_, input_, output_):
    node = type_(input_)
    assert node == output_
    assert node == node
    assert not (node != output_)
    assert not (node != node)
    assert str(node) == str(output_)


# testing invalid conversions
@pytest.mark.parametrize(
    "type_,input_",
    [
        (IntegerNode, "abc"),
        (IntegerNode, 10.1),
        (IntegerNode, "-1132c"),
        (FloatNode, "abc"),
        (IntegerNode, "-abc"),
        (BooleanNode, "Nope"),
        (BooleanNode, "Yup"),
    ],
)
def test_invalid_inputs(type_, input_):
    empty_node = type_()
    with pytest.raises(ValidationError):
        empty_node.set_value(input_)

    with pytest.raises(ValidationError):
        type_(input_)


@pytest.mark.parametrize(
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
def test_assigned_value_node_type(input_, expected_type):
    c = OmegaConf.create()
    c.foo = input_
    assert type(c.get_node("foo")) == expected_type


def test_get_node_no_validate_access():
    c = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(c, True)
    with pytest.raises(KeyError):
        c.get_node("zoo", validate_access=True)

    assert c.get_node("zoo", validate_access=False) is None

    assert (
        c.get_node("zoo", validate_access=False, default_value="default") == "default"
    )


# dict
def test_dict_any():
    c = OmegaConf.create()
    # default type is Any
    c.foo = 10
    c[Enum1.FOO] = "bar"

    assert c.foo == 10
    assert type(c.get_node("foo")) == AnyNode
    c.foo = "string"
    assert c.foo == "string"

    assert type(c.get_node(Enum1.FOO)) == AnyNode


def test_dict_integer_1():
    c = OmegaConf.create()
    c.foo = IntegerNode(10)
    assert type(c.get_node("foo")) == IntegerNode
    assert c.foo == 10


# list
def test_list_any():
    c = OmegaConf.create([])
    # default type is Any
    c.append(10)
    assert c[0] == 10
    assert type(c.get_node(0)) == AnyNode
    c[0] = "string"
    assert c[0] == "string"


def test_list_integer():
    val = 10
    c = OmegaConf.create([])
    c.append(IntegerNode(val))
    assert type(c.get_node(0)) == IntegerNode
    assert c.get(0) == val


def test_list_integer_rejects_string():
    c = OmegaConf.create([])
    c.append(IntegerNode(10))
    assert c.get(0) == 10
    with pytest.raises(ValidationError):
        c[0] = "string"
    assert c[0] == 10
    assert type(c.get_node(0)) == IntegerNode


# Test merge raises validation error
@pytest.mark.parametrize(
    "c1, c2",
    [
        (dict(a=IntegerNode(10)), dict(a="str")),
        (dict(a=IntegerNode(10)), dict(a=StringNode("str"))),
        (dict(a=10, b=IntegerNode(10)), dict(a=20, b="str")),
        (dict(foo=dict(bar=IntegerNode(10))), dict(foo=dict(bar="str"))),
    ],
)
def test_merge_validation_error(c1, c2):
    conf1 = OmegaConf.create(c1)
    conf2 = OmegaConf.create(c2)
    with pytest.raises(ValidationError):
        OmegaConf.merge(conf1, conf2)
    # make sure that conf1 and conf2 were not modified
    assert conf1 == OmegaConf.create(c1)
    assert conf2 == OmegaConf.create(c2)


@pytest.mark.parametrize(
    "type_,valid_value, invalid_value",
    [
        (IntegerNode, 1, "invalid"),
        (FloatNode, 3.1415, "invalid"),
        (BooleanNode, True, "invalid"),
        (AnyNode, "aaa", None),
        (StringNode, "blah", None),
    ],
)
def test_accepts_mandatory_missing(type_, valid_value, invalid_value):
    node = type_()
    node.set_value("???")
    assert node.value() == "???"

    conf = OmegaConf.create({"foo": node})
    assert "foo" not in conf
    assert type(conf.get_node("foo")) == type_

    conf.foo = valid_value
    # make sure valid assignment does not change the type
    assert type(conf.get_node("foo")) == type_
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


@pytest.mark.parametrize(
    "type_", [BooleanNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode]
)
@pytest.mark.parametrize(
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
def test_legal_assignment(type_, values, success_map):

    if not isinstance(values, (list, tuple)):
        values = [values]

    for value in values:
        if type_.__name__ in success_map.keys():
            expected = success_map[type_.__name__]
            if callable(expected):
                expected = expected(value)
            node = type_(value)
            assert node.value() == expected
        else:
            with pytest.raises(ValidationError):
                type_(value)


@pytest.mark.parametrize(
    "node,value",
    [
        (IntegerNode(), "foo"),
        (BooleanNode(), "foo"),
        (FloatNode(), "foo"),
        (EnumNode(enum_type=Enum1), "foo"),
    ],
)
def test_illegal_assignment(node, value):
    with pytest.raises(ValidationError):
        node.set_value(value)


@pytest.mark.parametrize(
    "node_type", [BooleanNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode]
)
@pytest.mark.parametrize(
    "enum_type, values, success_map",
    [
        (
            Enum1,
            (Enum1.FOO, "Enum1.FOO", "FOO", 1),
            {EnumNode: Enum1.FOO, AnyNode: copy.copy, StringNode: str},
        )
    ],
)
def test_legal_assignment_enum(node_type, enum_type, values, success_map):
    assert isinstance(values, (list, tuple))

    for value in values:
        if node_type in success_map.keys():
            expected = success_map[node_type]
            if callable(expected):
                expected = expected(value)
            node = node_type(enum_type)
            node.set_value(value)
            assert node.value() == expected
        else:
            with pytest.raises(ValidationError):
                node_type(enum_type)


def test_pretty_with_enum():
    cfg = OmegaConf.create()
    cfg.foo = EnumNode(Enum1)
    cfg.foo = Enum1.FOO

    expected = """foo: Enum1.FOO
"""
    assert cfg.pretty() == expected


class DummyEnum(Enum):
    FOO = 1


@pytest.mark.parametrize("is_optional", [True, False])
@pytest.mark.parametrize(
    "type_,value, expected_type",
    [
        (Any, 10, AnyNode),
        (DummyEnum, DummyEnum.FOO, EnumNode),
        (int, 42, IntegerNode),
        (float, 3.1415, FloatNode),
        (bool, True, BooleanNode),
        (str, "foo", StringNode),
    ],
)
def test_node_wrap(type_, is_optional, value, expected_type):
    from omegaconf.omegaconf import _node_wrap

    ret = _node_wrap(type_=type_, value=value, is_optional=is_optional, parent=None)
    assert type(ret) == expected_type
    assert ret == value

    if is_optional:
        ret = _node_wrap(type_=type_, value=None, is_optional=is_optional, parent=None)
        assert type(ret) == expected_type
        # noinspection PyComparisonWithNone
        assert ret == None  # noqa E711


def test_node_wrap_illegal_type():
    class UserClass:
        pass

    from omegaconf.omegaconf import _node_wrap

    with pytest.raises(ValueError):
        _node_wrap(type_=UserClass, value=UserClass(), is_optional=False, parent=None)


@pytest.mark.parametrize(
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
def test_deepcopy(obj):
    cp = copy.deepcopy(obj)
    assert cp == obj
    assert id(cp) != id(obj)


@pytest.mark.parametrize(
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
    ],
)
def test_eq(node, value, expected):
    assert (node == value) == expected
    assert (node != value) != expected
    assert (value == node) == expected
    assert (value != node) != expected
