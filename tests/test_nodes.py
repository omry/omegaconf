import pytest

from omegaconf import OmegaConf, nodes
from omegaconf.errors import ValidationError
from . import IllegalType


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
