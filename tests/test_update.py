from pytest import raises

from omegaconf import MissingMandatoryValue
from omegaconf import OmegaConf


def test_update_map_value():
    # Replacing an existing key in a map
    s = 'hello: world'
    c = OmegaConf.create(s)
    c.update('hello', 'there')
    assert {'hello': 'there'} == c


def test_update_map_new_keyvalue():
    # Adding another key to a map
    s = 'hello: world'
    c = OmegaConf.create(s)
    c.update('who', 'goes there')
    assert {'hello': 'world', 'who': 'goes there'} == c


def test_update_map_to_value():
    # changing map to single node
    s = 'hello: world'
    c = OmegaConf.create(s)
    c.update('value')
    assert {'hello': 'world', 'value': None} == c


def test_update_with_empty_map_value():
    c = OmegaConf.create()
    c.update('a', {})
    assert {'a': {}} == c


def test_update_with_map_value():
    c = OmegaConf.create()
    c.update('a', {'aa': 1, 'bb': 2})
    assert {'a': {'aa': 1, 'bb': 2}} == c


def test_update_deep_from_empty():
    c = OmegaConf.create()
    c.update('a.b', 1)
    assert {'a': {'b': 1}} == c


def test_update_deep_with_map():
    c = OmegaConf.create('a: b')
    c.update('a.b', {'c': 1})
    assert {'a': {'b': {'c': 1}}} == c


def test_update_deep_with_value():
    c = OmegaConf.create()
    c.update('a.b', 1)
    assert {'a': {'b': 1}} == c


def test_update_deep_with_map2():
    c = OmegaConf.create('a: 1')
    c.update('b.c', 2)
    assert {'a': 1, 'b': {'c': 2}} == c


def test_update_deep_with_map_update():
    c = OmegaConf.create('a: {b : {c: 1}}')
    c.update('a.b.d', 2)
    assert {'a': {'b': {'c': 1, 'd': 2}}} == c


def test_list_value_update():
    # List update is always a replace because a list can be merged in too many ways
    c = OmegaConf.create('a: [1,2]')
    c.update('a', [2, 3, 4])
    assert {'a': [2, 3, 4]} == c


def test_override_mandatory_value():
    c = OmegaConf.create('{a: "???"}')
    with raises(MissingMandatoryValue):
        c.get('a')
    c.update('a', 123)
    assert {'a': 123} == c


def test_update_empty_to_value():
    """"""
    s = ''
    c = OmegaConf.create(s)
    c.update('hello')
    assert {'hello': None} == c


def test_update_same_value():
    """"""
    s = 'hello'
    c = OmegaConf.create(s)
    c.update('hello')
    assert {'hello': None} == c


def test_update_value_to_map():
    s = 'hello'
    c = OmegaConf.create(s)
    c.update('hi', 'there')
    assert {'hello': None, 'hi': 'there'} == c


def test_update_map_empty_to_map():
    s = ''
    c = OmegaConf.create(s)
    c.update('hello', 'there')
    assert {'hello': 'there'} == c


def test_update_list():
    c = OmegaConf.create([1, 2, 3])
    c.update("1", "abc")
    c.update("-1", "last")
    with raises(IndexError):
        c.update("4", "abc")

    assert len(c) == 3
    assert c[0] == 1
    assert c[1] == 'abc'
    assert c[2] == 'last'


def test_update_nested_list():
    c = OmegaConf.create(dict(deep=dict(list=[1, 2, 3])))
    c.update("deep.list.1", "abc")
    c.update("deep.list.-1", "last")
    with raises(IndexError):
        c.update("deep.list.4", "abc")

    assert c.deep.list[0] == 1
    assert c.deep.list[1] == 'abc'
    assert c.deep.list[2] == 'last'


def test_update_list_make_dict():
    c = OmegaConf.create([None, None])
    c.update("0.a.a", "aa")
    c.update("0.a.b", "ab")
    c.update("1.b.a", "ba")
    c.update("1.b.b", "bb")
    assert c[0].a.a == 'aa'
    assert c[0].a.b == 'ab'
    assert c[1].b.a == 'ba'
    assert c[1].b.b == 'bb'


