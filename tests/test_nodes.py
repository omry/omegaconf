import pytest

from omegaconf import OmegaConf, nodes
from omegaconf.errors import ValidationError


# dict
def test_dict_any():
    c = OmegaConf.create()
    # default type is Any
    c.foo = 10
    assert c.foo == 10
    assert type(c.get_node('foo')) == nodes.AnyNode
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
    assert type(c.get_node(0)) == nodes.AnyNode
    c[0] = 'string'
    assert c[0] == 'string'


def test_list_integer_1():
    c = OmegaConf.create([])
    c.append(nodes.IntegerNode(10))
    assert type(c.get_node(0)) == nodes.IntegerNode
    assert c.get(0) == 10


def test_list_integer_rejects_string():
    c = OmegaConf.create([])
    c.append(nodes.IntegerNode(10))
    assert c.get(0) == 10
    with pytest.raises(ValidationError):
        c[0] = 'string'
    assert c[0] == 10
    assert type(c.get_node(0)) == nodes.IntegerNode


# TODO: add additional test cases with lists, and with multiple node types.
# merge
@pytest.mark.parametrize('c1, c2', [
    (dict(a=nodes.IntegerNode(10)), dict(a='str')),
    (dict(a=nodes.IntegerNode(10)), dict(a=nodes.StringNode('str'))),
    (dict(a=10, b=nodes.IntegerNode(10)), dict(a=20, b='str')),
])
def test_merge_validation_error(c1, c2):
    conf1 = OmegaConf.create(c1)
    conf2 = OmegaConf.create(c2)
    with pytest.raises(ValidationError):
        OmegaConf.merge(conf1, conf2)
    # make sure that conf1 and conf2 were not modified
    assert conf1 == OmegaConf.create(c1)
    assert conf2 == OmegaConf.create(c2)
