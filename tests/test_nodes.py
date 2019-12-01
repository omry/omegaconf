import pytest

from omegaconf import (
    StringNode,
    IntegerNode,
    FloatNode,
    BooleanNode,
    BaseNode,
    ListConfig,
    DictConfig,
    UntypedNode,
    OmegaConf,
)
from omegaconf.errors import ValidationError


def test_base_node():
    b = BaseNode()
    assert b.value() is None
    with pytest.raises(NotImplementedError):
        b.set_value(10)


# testing valid conversions
@pytest.mark.parametrize(
    "type_,input_,output_",
    [
        # string
        (StringNode, "abc", "abc"),
        (StringNode, 100, "100"),
        # integer
        (IntegerNode, 10, 10),
        (IntegerNode, 10.1, 10),
        (IntegerNode, "10", 10),
        (IntegerNode, -100, -100),
        (IntegerNode, "-100", -100),
        # float
        (FloatNode, float("inf"), float("inf")),
        (
            FloatNode,
            float("nan"),
            float("nan"),
        ),  # Yes, we treat nan as equal to nan in OmegaConf
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
        (BooleanNode, None, False),
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
        (5, UntypedNode),
        (5.0, UntypedNode),
        (True, UntypedNode),
        (False, UntypedNode),
        ("str", UntypedNode),
    ],
)
def test_assigned_value_node_type(input_, expected_type):
    c = OmegaConf.create()
    c.foo = input_
    assert type(c.get_node("foo")) == expected_type


# dict
def test_dict_any():
    c = OmegaConf.create()
    # default type is Any
    c.foo = 10
    assert c.foo == 10
    assert type(c.get_node("foo")) == UntypedNode
    c.foo = "string"
    assert c.foo == "string"


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
    assert type(c.get_node(0)) == UntypedNode
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
    "type_,input_,target,expected",
    [
        (FloatNode, None, 1, False),
        (FloatNode, "1", 1, True),
        (FloatNode, float("nan"), float("nan"), True),
        (FloatNode, None, float("nan"), False),
    ],
)
def test_eq(type_, input_, target, expected):
    node = type_(input_)
    assert (node == target) == expected

