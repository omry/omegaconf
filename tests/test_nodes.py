import pytest

from omegaconf import OmegaConf, nodes
from omegaconf.errors import ValidationError


# testing valid conversions
@pytest.mark.parametrize('type_,input_,output_', [
    # string
    (nodes.StringNode, "abc", "abc"),
    (nodes.StringNode, 100, "100"),
    # integer
    (nodes.IntegerNode, 10, 10),
    (nodes.IntegerNode, 10.1, 10),
    (nodes.IntegerNode, '10', 10),
    (nodes.IntegerNode, -100, -100),
    (nodes.IntegerNode, "-100", -100),
    # float
    (nodes.FloatNode, float('inf'), float('inf')),
    (nodes.FloatNode, float('nan'), float('nan')),  # Yes, we treat nan as equal to nan in OmegaConf
    (nodes.FloatNode, 10, 10.0),
    (nodes.FloatNode, 10.1, 10.1),
    (nodes.FloatNode, "10.2", 10.2),
    (nodes.FloatNode, "10e-3", 10e-3),
    # bool true
    (nodes.BooleanNode, True, True),
    (nodes.BooleanNode, "Y", True),
    (nodes.BooleanNode, "true", True),
    (nodes.BooleanNode, "Yes", True),
    (nodes.BooleanNode, "On", True),
    (nodes.BooleanNode, "1", True),
    (nodes.BooleanNode, 100, True),
    # bool false
    (nodes.BooleanNode, False, False),
    (nodes.BooleanNode, "N", False),
    (nodes.BooleanNode, "false", False),
    (nodes.BooleanNode, "No", False),
    (nodes.BooleanNode, "Off", False),
    (nodes.BooleanNode, None, False),
    (nodes.BooleanNode, "0", False),
    (nodes.BooleanNode, 0, False),

])
def test_valid_inputs(type_, input_, output_):
    node = type_(input_)
    assert node == output_


# testing invalid conversions
@pytest.mark.parametrize('type_,input_', [
    (nodes.IntegerNode, 'abc'),
    (nodes.IntegerNode, '-1132c'),
    (nodes.FloatNode, 'abc'),
    (nodes.IntegerNode, '-abc'),
    (nodes.BooleanNode, "Nope"),
    (nodes.BooleanNode, "Yup"),
])
def test_invalid_inputs(type_, input_):
    empty_node = type_()
    with pytest.raises(ValidationError):
        empty_node.set_value(input_)

    with pytest.raises(ValidationError):
        type_(input_)


# dict
def test_dict_any():
    c = OmegaConf.create()
    # default type is Any
    c.foo = 10
    assert c.foo == 10
    assert type(c.get_node('foo')) == nodes.UntypedNode
    c.foo = 'string'
    assert c.foo == 'string'


def test_dict_integer_1():
    c = OmegaConf.create()
    c.foo = nodes.IntegerNode(10)
    assert type(c.get_node('foo')) == nodes.IntegerNode
    assert c.foo == 10


def test_dict_integer_rejects_string():
    c = OmegaConf.create()
    c.foo = nodes.IntegerNode(10)
    assert c.foo == 10
    with pytest.raises(ValidationError):
        c.foo = 'string'
    assert c.foo == 10
    assert type(c.get_node('foo')) == nodes.IntegerNode


# list
def test_list_any():
    c = OmegaConf.create([])
    # default type is Any
    c.append(10)
    assert c[0] == 10
    assert type(c.get_node(0)) == nodes.UntypedNode
    c[0] = 'string'
    assert c[0] == 'string'


def test_list_integer():
    val = 10
    c = OmegaConf.create([])
    c.append(nodes.IntegerNode(val))
    assert type(c.get_node(0)) == nodes.IntegerNode
    assert c.get(0) == val


def test_list_integer_rejects_string():
    c = OmegaConf.create([])
    c.append(nodes.IntegerNode(10))
    assert c.get(0) == 10
    with pytest.raises(ValidationError):
        c[0] = 'string'
    assert c[0] == 10
    assert type(c.get_node(0)) == nodes.IntegerNode


# merge validation error
@pytest.mark.parametrize('c1, c2', [
    (dict(a=nodes.IntegerNode(10)), dict(a='str')),
    (dict(a=nodes.IntegerNode(10)), dict(a=nodes.StringNode('str'))),
    (dict(a=10, b=nodes.IntegerNode(10)), dict(a=20, b='str')),
    (dict(foo=dict(bar=nodes.IntegerNode(10))), dict(foo=dict(bar='str')))
])
def test_merge_validation_error(c1, c2):
    conf1 = OmegaConf.create(c1)
    conf2 = OmegaConf.create(c2)
    with pytest.raises(ValidationError):
        OmegaConf.merge(conf1, conf2)
    # make sure that conf1 and conf2 were not modified
    assert conf1 == OmegaConf.create(c1)
    assert conf2 == OmegaConf.create(c2)

