"""Testing for OmegaConf"""
import re
import sys

from pytest import raises

from omegaconf import OmegaConf


def test_create_value():
    """Test a simple value"""
    s = 'hello'
    c = OmegaConf.create(s)
    assert {'hello': None} == c


def test_create_key_value():
    """Test a simple key:value"""
    s = 'hello: world'
    c = OmegaConf.create(s)
    assert {'hello': 'world'} == c


def test_create_key_map():
    """Test a key to map"""
    c = OmegaConf.create(dict(hello=dict(a=2)))
    assert {'hello': {'a': 2}} == c


def test_create_empty_string():
    """Test empty input"""
    s = ''
    c = OmegaConf.create(s)
    assert c == {}


def test_create_list_value():
    c = OmegaConf.create([1, 2])
    assert [1, 2] == c


def test_create_tupple_value():
    # For simplicity, tuples are converted to lists.
    c = OmegaConf.create((1, 2))
    assert [1, 2] == c


def test_create_from_dict1():
    d = {'a': 2, 'b': 10}
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_dict2():
    d = dict(a=2, b=10)
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_nested_dict():
    d = {'a': 2, 'b': {'c': {'f': 1}, 'd': {}}}
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_cli():
    sys.argv = ['program.py', 'a=1', 'b.c=2']
    c = OmegaConf.from_cli()
    assert {'a': 1, 'b': {'c': 2}} == c


def test_cli_passing():
    args_list = ['a=1', 'b.c=2']
    c = OmegaConf.from_cli(args_list)
    assert {'a': 1, 'b': {'c': 2}} == c


def test_dotlist():
    args_list = ['a=1', 'b.c=2']
    c = OmegaConf.from_dotlist(args_list)
    assert {'a': 1, 'b': {'c': 2}} == c


class IllegalType:
    def __init__(self):
        pass


def test_create_list_with_illegal_value_idx0():
    with raises(ValueError, match=re.escape("key [0]")):
        OmegaConf.create([IllegalType()])


def test_create_list_with_illegal_value_idx1():
    with raises(ValueError, match=re.escape("key [1]")):
        OmegaConf.create([1, IllegalType(), 3])


def test_create_dict_with_illegal_value():
    with raises(ValueError, match=re.escape("key a")):
        OmegaConf.create(dict(a=IllegalType()))


# TODO: improve exception message to contain full key a.b
# https://github.com/omry/omegaconf/issues/14
def test_create_nested_dict_with_illegal_value():
    with raises(ValueError, match=re.escape("key b")):
        OmegaConf.create(dict(a=dict(b=IllegalType())))


def test_create_empty__deprecated():
    assert OmegaConf.empty() == {}


def test_create_from_string__deprecated():
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    assert {'hello': 'world'} == c


def test_create_from_dict__deprecated():
    src = dict(a=1, b=2)
    c = OmegaConf.from_dict(src)
    assert c == src


def test_create_from_list__deprecated():
    src = [1, 2, 3, 4]
    c = OmegaConf.from_list(src)
    assert c == src
