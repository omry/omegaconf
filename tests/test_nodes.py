import copy
import functools
import re
from enum import Enum
from functools import partial
from typing import Any, Dict, Tuple, Type

from pytest import mark, param, raises

from omegaconf import (
    AnyNode,
    BooleanNode,
    BytesNode,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    Node,
    OmegaConf,
    StringNode,
    ValueNode,
)
from omegaconf._utils import type_str
from omegaconf.errors import (
    InterpolationToMissingValueError,
    UnsupportedValueType,
    ValidationError,
)
from omegaconf.nodes import InterpolationResultNode
from tests import Color, Enum1, IllegalType, User


# testing valid conversions
@mark.parametrize(
    "type_,input_,output_",
    [
        # string
        (StringNode, "abc", "abc"),
        (StringNode, 100, "100"),
        (StringNode, Color.RED, "Color.RED"),
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
        # bytes
        (BytesNode, b"binary", b"binary"),
        (BytesNode, b"\xf0\xf1\xf2", b"\xf0\xf1\xf2"),
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
        (AnyNode, b"\xf0\xf1\xf2", b"\xf0\xf1\xf2"),
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
@mark.parametrize(
    "type_,input_",
    [
        (IntegerNode, "abc"),
        (IntegerNode, "-abc"),
        (IntegerNode, 10.1),
        (IntegerNode, "-1132c"),
        (IntegerNode, Color.RED),
        (IntegerNode, b"123"),
        (FloatNode, "abc"),
        (FloatNode, Color.RED),
        (FloatNode, b"10.1"),
        (BytesNode, "abc"),
        (BytesNode, 23),
        (BytesNode, Color.RED),
        (BytesNode, 3.14),
        (BytesNode, True),
        (BooleanNode, "Nope"),
        (BooleanNode, "Yup"),
        (BooleanNode, Color.RED),
        (BooleanNode, b"True"),
        (IntegerNode, [1, 2]),
        (IntegerNode, ListConfig([1, 2])),
        (IntegerNode, {"foo": "var"}),
        (IntegerNode, b"10"),
        (IntegerNode, DictConfig({"foo": "var"})),
        (BytesNode, [1, 2]),
        (BytesNode, ListConfig([1, 2])),
        (BytesNode, {"foo": "var"}),
        (BytesNode, DictConfig({"foo": "var"})),
        (BooleanNode, [1, 2]),
        (BooleanNode, ListConfig([1, 2])),
        (BooleanNode, {"foo": "var"}),
        (BooleanNode, DictConfig({"foo": "var"})),
        (FloatNode, [1, 2]),
        (FloatNode, ListConfig([1, 2])),
        (FloatNode, {"foo": "var"}),
        (FloatNode, DictConfig({"foo": "var"})),
        (StringNode, [1, 2]),
        (StringNode, ListConfig([1, 2])),
        (StringNode, {"foo": "var"}),
        (StringNode, b"\xf0\xf1\xf2"),
        (FloatNode, DictConfig({"foo": "var"})),
        (AnyNode, [1, 2]),
        (AnyNode, ListConfig([1, 2])),
        (AnyNode, {"foo": "var"}),
        (AnyNode, DictConfig({"foo": "var"})),
        (AnyNode, IllegalType()),
        (partial(EnumNode, Color), "Color.TYPO"),
        (partial(EnumNode, Color), "TYPO"),
        (partial(EnumNode, Color), Enum1.FOO),
        (partial(EnumNode, Color), "Enum1.RED"),
        (partial(EnumNode, Color), 1000000),
        (partial(EnumNode, Color), 1.0),
        (partial(EnumNode, Color), b"binary"),
        (partial(EnumNode, Color), True),
        (partial(EnumNode, Color), [1, 2]),
        (partial(EnumNode, Color), {"foo": "bar"}),
        (partial(EnumNode, Color), ListConfig([1, 2])),
        (partial(EnumNode, Color), DictConfig({"foo": "bar"})),
    ],
)
def test_invalid_inputs(type_: type, input_: Any) -> None:
    empty_node = type_()

    with raises(ValidationError):
        empty_node._set_value(input_)
    with raises(ValidationError):
        type_(input_)


@mark.parametrize(
    "input_, expected_type",
    [
        ({}, DictConfig),
        ([], ListConfig),
        (5, AnyNode),
        (5.0, AnyNode),
        (True, AnyNode),
        (False, AnyNode),
        ("str", AnyNode),
        (b"\xf0\xf1\xf2", AnyNode),
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
    with raises(ValidationError):
        c[0] = "string"
    assert c[0] == 10
    assert type(c._get_node(0)) == IntegerNode


# Test merge raises validation error
@mark.parametrize(
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
    with raises(ValidationError):
        OmegaConf.merge(conf1, conf2)
    # make sure that conf1 and conf2 were not modified
    assert conf1 == OmegaConf.create(c1)
    assert conf2 == OmegaConf.create(c2)


@mark.parametrize(
    "type_,valid_value, invalid_value",
    [
        (IntegerNode, 1, "invalid"),
        (FloatNode, 3.1415, "invalid"),
        (BooleanNode, True, "invalid"),
        (AnyNode, "aaa", None),
        (StringNode, "blah", None),
        (BytesNode, b"foobar", None),
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
        with raises(ValidationError):
            conf.foo = invalid_value


@mark.parametrize(
    "type_",
    [BooleanNode, BytesNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode],
)
@mark.parametrize(
    "values, success_map",
    [
        param(
            # True aliases
            (True, "Y", "true", "yes", "on"),
            {
                "BooleanNode": True,
                "StringNode": str,
                "AnyNode": copy.copy,
            },
            id="true-aliases",
        ),
        param(
            # Integers
            ("1", 1, 10, -10),
            {
                "BooleanNode": True,
                "IntegerNode": int,
                "FloatNode": float,
                "StringNode": str,
                "AnyNode": copy.copy,
            },
            id="integers",
        ),
        param(
            # Floaty things
            ("1.0", 1.0, float("inf"), float("-inf"), "10e-3", 10e-3),
            {"FloatNode": float, "StringNode": str, "AnyNode": copy.copy},
            id="floaty-things",
        ),
        param(
            # False aliases
            (False, "N", "false", "no", "off"),
            {
                "BooleanNode": False,
                "StringNode": str,
                "AnyNode": copy.copy,
            },
            id="false-alises",
        ),
        param(
            # Falsy integers
            ("0", 0),
            {
                "BooleanNode": False,
                "IntegerNode": 0,
                "FloatNode": 0.0,
                "StringNode": str,
                "AnyNode": copy.copy,
            },
            id="falsey-integers",
        ),
        param(
            # Binary data
            (b"binary",),
            {
                "BytesNode": b"binary",
                "AnyNode": copy.copy,
            },
            id="binary-data",
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
            with raises(ValidationError):
                type_(value)


@mark.parametrize(
    "node,value",
    [
        (IntegerNode(), "foo"),
        (BooleanNode(), "foo"),
        (FloatNode(), "foo"),
        (BytesNode(), "foo"),
        (EnumNode(enum_type=Enum1), "foo"),
    ],
)
def test_illegal_assignment(node: ValueNode, value: Any) -> None:
    with raises(ValidationError):
        node._set_value(value)


@mark.parametrize(
    "node_type",
    [BooleanNode, BytesNode, EnumNode, FloatNode, IntegerNode, StringNode, AnyNode],
)
@mark.parametrize(
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
    values: Tuple[Any, ...],
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
            with raises(ValidationError):
                node_type(enum_type)


@mark.parametrize(
    "obj",
    [
        StringNode(),
        StringNode(value="foo"),
        StringNode(value="foo", is_optional=False),
        BytesNode(value=b"\xf0\xf1\xf2"),
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


@mark.parametrize(
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
        (BytesNode(), None, True),
        (BytesNode(), b"binary", False),
        (BytesNode(b"binary"), b"binary", True),
        (BooleanNode(), True, False),
        (BooleanNode(), False, False),
        (BooleanNode(), None, True),
        (BooleanNode(True), None, False),
        (BooleanNode(True), False, False),
        (BooleanNode(False), False, True),
        (AnyNode(value=1), AnyNode(value=1), True),
        (EnumNode(enum_type=Enum1), Enum1.BAR, False),
        (EnumNode(enum_type=Enum1), EnumNode(Enum1), True),
        (EnumNode(enum_type=Enum1), "nope", False),
        (
            EnumNode(enum_type=Enum1, value=Enum1.BAR),
            EnumNode(enum_type=Enum1, value=Enum1.BAR),
            True,
        ),
        (EnumNode(enum_type=Enum1, value=Enum1.BAR), Enum1.BAR, True),
        (InterpolationResultNode("foo"), "foo", True),
        (InterpolationResultNode("${foo}"), "${foo}", True),
        (InterpolationResultNode("${foo"), "${foo", True),
        (InterpolationResultNode(None), None, True),
        (InterpolationResultNode(1), 1, True),
        (InterpolationResultNode(1.0), 1.0, True),
        (InterpolationResultNode(True), True, True),
        (InterpolationResultNode(Color.RED), Color.RED, True),
        (InterpolationResultNode({"a": 0, "b": 1}), {"a": 0, "b": 1}, True),
        (InterpolationResultNode([0, None, True]), [0, None, True], True),
        (InterpolationResultNode("foo"), 100, False),
        (InterpolationResultNode(100), "foo", False),
    ],
)
def test_eq(node: ValueNode, value: Any, expected: Any) -> None:
    assert (node == value) == expected
    assert (node != value) != expected
    assert (value == node) == expected
    assert (value != node) != expected

    # Check hash except for unhashable types (dict/list).
    if not isinstance(value, (dict, list)):
        assert (node.__hash__() == value.__hash__()) == expected


@mark.parametrize("value", [1, 3.14, True, None, Enum1.FOO])
def test_set_anynode_with_primitive_type(value: Any) -> None:
    cfg = OmegaConf.create({"a": 5})
    a_before = cfg._get_node("a")
    cfg.a = value
    # changing anynode's value with a primitive type should set value
    assert id(cfg._get_node("a")) == id(a_before)
    assert cfg.a == value


@mark.parametrize(
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
    with raises(ValidationError):
        cfg.a = IllegalType()


def test_set_valuenode() -> None:
    cfg = OmegaConf.structured(User)
    a_before = cfg._get_node("age")
    cfg.age = 12
    assert id(cfg._get_node("age")) == id(a_before)
    with raises(ValidationError):
        cfg.age = []


def test_allow_objects() -> None:
    c = OmegaConf.create({"foo": AnyNode()})
    with raises(UnsupportedValueType):
        c.foo = IllegalType()
    c._set_flag("allow_objects", True)
    iv = IllegalType()
    c.foo = iv
    assert c.foo == iv


def test_dereference_missing() -> None:
    cfg = OmegaConf.create({"x": "???"})
    x_node = cfg._get_node("x")
    assert isinstance(x_node, Node)
    assert x_node._dereference_node() is x_node


@mark.parametrize(
    "make_func",
    [
        StringNode,
        IntegerNode,
        FloatNode,
        BooleanNode,
        BytesNode,
        lambda val, is_optional: EnumNode(
            enum_type=Color, value=val, is_optional=is_optional
        ),
    ],
)
def test_validate_and_convert_none(make_func: Any) -> None:
    node = make_func("???", is_optional=False)
    ref_type_str = type_str(node._metadata.ref_type)
    with raises(
        ValidationError,
        match=re.escape(
            f"Incompatible value 'None' for field of type '{ref_type_str}'"
        ),
    ):
        node.validate_and_convert(None)


def test_dereference_interpolation_to_missing() -> None:
    cfg = OmegaConf.create({"x": "${y}", "y": "???"})
    x_node = cfg._get_node("x")
    assert isinstance(x_node, Node)
    assert x_node._maybe_dereference_node() is None
    with raises(InterpolationToMissingValueError):
        cfg.x


@mark.parametrize(
    "flags",
    [
        {},
        {"flag": True},
        {"flag": False},
        {"flag1": True, "flag2": False},
    ],
)
@mark.parametrize(
    "type_",
    [
        AnyNode,
        BooleanNode,
        BytesNode,
        functools.partial(EnumNode, enum_type=Color),
        FloatNode,
        IntegerNode,
        InterpolationResultNode,
        StringNode,
    ],
)
def test_set_flags_in_init(type_: Any, flags: Dict[str, bool]) -> None:
    node = type_(value=None, flags=flags)
    for f, v in flags.items():
        assert node._get_flag(f) is v


@mark.parametrize(
    "flags",
    [
        None,
        {"flag": True},
        {"flag": False},
        {"readonly": True},
        {"readonly": False},
        {"flag1": True, "flag2": False, "readonly": False},
        {"flag1": False, "flag2": True, "readonly": True},
    ],
)
def test_interpolation_result_readonly(flags: Any) -> None:
    readonly = None if flags is None else flags.get("readonly")
    expected = [] if flags is None else list(flags.items())
    node = InterpolationResultNode("foo", flags=flags)

    # Check that flags are set to their desired value.
    for k, v in expected:
        assert node._get_node_flag(k) is v

    # If no value was provided for the "readonly" flag, it should be set.
    if readonly is None:
        assert node._get_node_flag("readonly")
