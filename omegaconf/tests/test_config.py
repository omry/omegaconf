"""Testing for OmegaConf"""
import tempfile
import sys
import os
from pytest import raises
from omegaconf import OmegaConf
from omegaconf import MissingMandatoryValue
from omegaconf.omegaconf import Config


def test_value():
    """Test a simple value"""
    s = 'hello'
    c = OmegaConf.from_string(s)
    assert {'hello': None} == c


def test_key_value():
    """Test a simple key:value"""
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    assert {'hello': 'world'} == c


def test_key_map():
    """Test a key to map"""
    s = '{hello: {a : 2}}'
    c = OmegaConf.from_string(s)
    assert {'hello': {'a': 2}} == c


def test_empty_input():
    """Test empty input"""
    s = ''
    c = OmegaConf.from_string(s)
    assert c == {}


def test_update_empty_to_value():
    """"""
    s = ''
    c = OmegaConf.from_string(s)
    c.update('hello')
    assert {'hello': None} == c


def test_update_same_value():
    """"""
    s = 'hello'
    c = OmegaConf.from_string(s)
    c.update('hello')
    assert {'hello': None} == c


def test_update_value_to_map():
    s = 'hello'
    c = OmegaConf.from_string(s)
    c.update('hi', 'there')
    assert {'hello': None, 'hi': 'there'} == c


def test_update_map_empty_to_map():
    s = ''
    c = OmegaConf.from_string(s)
    c.update('hello', 'there')
    assert {'hello': 'there'} == c


def test_update__map_value():
    # Replacing an existing key in a map
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    c.update('hello', 'there')
    assert {'hello': 'there'} == c


def test_update_map_new_keyvalue():
    # Adding another key to a map
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    c.update('who', 'goes there')
    assert {'hello': 'world', 'who': 'goes there'} == c


def test_update_map_to_value():
    # changing map to single node
    s = 'hello: world'
    c = OmegaConf.from_string(s)
    c.update('value')
    assert {'hello': 'world', 'value': None} == c


def test_update_with_empty_map_value():
    c = OmegaConf.empty()
    c.update('a', {})
    assert {'a': {}} == c


def test_update_with_map_value():
    c = OmegaConf.empty()
    c.update('a', {'aa': 1, 'bb': 2})
    assert {'a': {'aa': 1, 'bb': 2}} == c


def test_update_deep_from_empty():
    c = OmegaConf.empty()
    c.update('a.b', 1)
    assert {'a': {'b': 1}} == c


def test_update_deep_with_map():
    c = OmegaConf.from_string('a: b')
    c.update('a.b', {'c': 1})
    assert {'a': {'b': {'c': 1}}} == c


def test_update_deep_with_value():
    c = OmegaConf.empty()
    c.update('a.b', 1)
    assert {'a': {'b': 1}} == c


def test_update_deep_with_map2():
    c = OmegaConf.from_string('a: 1')
    c.update('b.c', 2)
    assert {'a': 1, 'b': {'c': 2}} == c


def test_update_deep_with_map_update():
    c = OmegaConf.from_string('a: {b : {c: 1}}')
    c.update('a.b.d', 2)
    assert {'a': {'b': {'c': 1, 'd': 2}}} == c


def test_setattr_value():
    c = OmegaConf.from_string('a: {b : {c: 1}}')
    c.a = 9
    assert {'a': 9} == c


def test_setattr_deep_value():
    c = OmegaConf.from_string('a: {b : {c: 1}}')
    c.a.b = 9
    assert {'a': {'b': 9}} == c


def test_setattr_deep_from_empty():
    c = OmegaConf.empty()
    # Unfortunately we can't just do c.a.b = 9 here.
    # The reason is that if c.a is being resolved first and it does not exist, so there
    # is nothing to call .b = 9 on.
    # The alternative is to auto-create fields as they are being accessed, but this is opening
    # a whole new can of worms, and is also breaking map semantics.
    c.a = {}
    c.a.b = 9
    assert {'a': {'b': 9}} == c


def test_setattr_deep_map():
    c = OmegaConf.from_string('a: {b : {c: 1}}')
    c.a.b = {'z': 10}
    assert {'a': {'b': {'z': 10}}} == c


def test_map_merge_1():
    a = {}
    b = {'a': 1}
    c = Config.map_merge(a, b)
    assert b == c


def test_map_merge_2():
    a = {'a': 1}
    b = {'b': 2}
    c = Config.map_merge(a, b)
    assert {'a': 1, 'b': 2} == c


def test_map_merge_3():
    a = {'a': {'a1': 1, 'a2': 2}}
    b = {'a': {'a1': 2}}
    c = Config.map_merge(a, b)
    assert {'a': {'a1': 2, 'a2': 2}} == c


def test_merge1():
    c1 = OmegaConf.from_string('a')
    c2 = OmegaConf.from_string('b')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': None, 'b': None} == c3


def test_merge2():
    # replaces an element with an element
    c1 = OmegaConf.from_string('{a: 1, b: 2}')
    c2 = OmegaConf.from_string('{b: 3}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': 1, 'b': 3} == c3


def test_merge3():
    # replaces an element with a map
    c1 = OmegaConf.from_string('{a: 1, b: 2}')
    c2 = OmegaConf.from_string('{b: {c: 3}}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': 1, 'b': {'c': 3}} == c3


def test_merge4():
    # replaces a map with an element
    c1 = OmegaConf.from_string('{b: {c: 1}}')
    c2 = OmegaConf.from_string('{b: 1}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'b': 1} == c3


def test_3way_merge():
    c1 = OmegaConf.from_string('{a: 1, b: 2}')
    c2 = OmegaConf.from_string('{b: 3}')
    c3 = OmegaConf.from_string('{a: 2, c: 3}')
    c4 = OmegaConf.merge(c1, c2, c3)
    assert {'a': 2, 'b': 3, 'c': 3} == c4


def test_dir():
    c = OmegaConf.from_string('a: b')
    assert ['a'] == dir(c)


def test_getattr():
    c = OmegaConf.from_string('a: b')
    assert 'b' == c.a


def test_getattr_dict():
    c = OmegaConf.from_string('a: {b: 1}')
    assert {'b': 1} == c.a


def test_str():
    c = OmegaConf.from_string('a: b')
    assert "{'a': 'b'}" == str(c)


def test_repr():
    c = OmegaConf.from_string('a: b')
    assert "{'a': 'b'}" == repr(c)


def test_is_empty():
    c = OmegaConf.from_string('a: b')
    assert not c.is_empty()
    c = OmegaConf.empty()
    assert c.is_empty()


def test_list_value():
    c = OmegaConf.from_string('a: [1,2]')
    assert {'a': [1, 2]} == c


def test_list_value_update():
    # List update is always a replace because a list can be merged in too many ways
    c = OmegaConf.from_string('a: [1,2]')
    c.update('a', [2, 3, 4])
    assert {'a': [2, 3, 4]} == c


def test_from_file():
    with tempfile.TemporaryFile() as fp:
        s = b'a: b'
        fp.write(s)
        fp.flush()
        fp.seek(0)
        c = OmegaConf.from_file(fp)
        assert {'a': 'b'} == c


def test_from_filename():
    with tempfile.NamedTemporaryFile() as fp:
        s = b'a: b'
        fp.write(s)
        fp.flush()
        c = OmegaConf.from_filename(fp.name)
        assert {'a': 'b'} == c


def test_cli_config():
    sys.argv = ['program.py', 'a=1', 'b.c=2']
    c = OmegaConf.from_cli()
    assert {'a': 1, 'b': {'c': 2}} == c


def test_cli_passing():
    args_list = ['a=1', 'b.c=2']
    c = OmegaConf.from_cli(args_list)
    assert {'a': 1, 'b': {'c': 2}} == c


def test_env_config():
    os.environ['PREFIX.a'] = '1'
    os.environ['PREFIX.b.c'] = '2'
    c = OmegaConf.from_env(prefix="PREFIX.")
    assert {'a': 1, 'b': {'c': 2}} == c


def test_mandatory_value():
    c = OmegaConf.from_string('{a: "???"}')
    with raises(MissingMandatoryValue):
        c.get('a')


def test_override_mandatory_value():
    c = OmegaConf.from_string('{a: "???"}')
    with raises(MissingMandatoryValue):
        c.get('a')
    c.update('a', 123)
    assert {'a': 123} == c


def test_subscript_get():
    c = OmegaConf.from_string('a: b')
    assert 'b' == c['a']


def test_subscript_set():
    c = OmegaConf.empty()
    c['a'] = 'b'
    assert {'a': 'b'} == c


def test_pretty():
    c = OmegaConf.from_string('''
hello: world
list: [
    1,
    2
]
''')
    expected = '''hello: world
list:
- 1
- 2
'''
    assert expected == c.pretty()


def test_scientific_number():
    c = OmegaConf.from_string('a: 10e-3')
    assert 10e-3 == c.a


def test_with_default():
    s = '{hello: {a : 2}}'
    c = OmegaConf.from_string(s)
    assert c.get('missing', 4) == 4
    assert c.hello.get('missing', 5) == 5
    assert {'hello': {'a': 2}} == c


def test_map_expansion():
    c = OmegaConf.from_string('{a: 2, b: 10}')

    def foo(a, b):
        return a + b

    assert 12 == foo(**c)


def test_items():
    c = OmegaConf.from_string('{a: 2, b: 10}')
    assert {'a': 2, 'b': 10}.items() == c.items()


def test_pickle():
    with tempfile.TemporaryFile() as fp:
        s = 'a: b'
        import pickle
        c = OmegaConf.from_string(s)
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1


def test_iterate():
    c = OmegaConf.from_string('''
    a : 1
    b : 2
    ''')
    m2 = {}
    for k in c:
        m2[k] = c[k]
    assert m2 == c


def test_items():
    c = OmegaConf.from_string('''
    a:
      v: 1
    b:
      v: 1
    ''')
    for k, v in c.items():
        v.v = 2

    assert c.a.v == 2
    assert c.b.v == 2


def test_pop():
    c = OmegaConf.from_string('''
    a : 1
    b : 2
    ''')
    assert 1 == c.pop('a')
    assert {'b': 2} == c
