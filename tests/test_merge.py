from omegaconf import OmegaConf
from omegaconf.omegaconf import Config

from pytest import raises


def test_dict_merge_1():
    a = OmegaConf.create({})
    b = OmegaConf.create({'a': 1})
    c = Config.map_merge(a, b)
    assert b == c


def test_dict_merge_no_modify():
    # Test that map_merge does not modify the input
    a = OmegaConf.create({})
    b = OmegaConf.create({'a': 1})
    Config.map_merge(a, b)
    assert a == {}
    assert b == {'a': 1}


def test_dict_merge_2():
    a = OmegaConf.create({'a': 1})
    b = OmegaConf.create({'b': 2})
    c = Config.map_merge(a, b)
    assert {'a': 1, 'b': 2} == c


def test_dict_merge_3():
    a = OmegaConf.create({'a': {'a1': 1, 'a2': 2}})
    b = OmegaConf.create({'a': {'a1': 2}})
    c = Config.map_merge(a, b)
    assert {'a': {'a1': 2, 'a2': 2}} == c


def test_dict_merge_4():
    c1 = OmegaConf.create('a')
    c2 = OmegaConf.create('b')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': None, 'b': None} == c3


def test_dict_merge5():
    # replaces an element with an element
    c1 = OmegaConf.create('{a: 1, b: 2}')
    c2 = OmegaConf.create('{b: 3}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': 1, 'b': 3} == c3


def test_dict_merge_dict6():
    # replaces an element with a map
    c1 = OmegaConf.create('{a: 1, b: 2}')
    c2 = OmegaConf.create('{b: {c: 3}}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'a': 1, 'b': {'c': 3}} == c3


def test_dict_merge7():
    # replaces a map with an element
    c1 = OmegaConf.create('{b: {c: 1}}')
    c2 = OmegaConf.create('{b: 1}')
    c3 = OmegaConf.merge(c1, c2)
    assert {'b': 1} == c3


def test_3way_dict_merge():
    c1 = OmegaConf.create('{a: 1, b: 2}')
    c2 = OmegaConf.create('{b: 3}')
    c3 = OmegaConf.create('{a: 2, c: 3}')
    c4 = OmegaConf.merge(c1, c2, c3)
    assert {'a': 2, 'b': 3, 'c': 3} == c4


def test_merge_list_root():
    c1 = OmegaConf.create([1, 2, 3])
    c2 = OmegaConf.create([4, 5, 6])
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == [4, 5, 6]


def test_merge_tuple_root():
    c1 = OmegaConf.create((1, 2, 3))
    c2 = OmegaConf.create((4, 5, 6))
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == [4, 5, 6]


def test_merge_list_nested_in_list():
    c1 = OmegaConf.create([[1, 2, 3]])
    c2 = OmegaConf.create([[4, 5, 6]])
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == [[4, 5, 6]]


def test_merge_list_nested_in_dict():
    c1 = OmegaConf.create(dict(list=[1, 2, 3]))
    c2 = OmegaConf.create(dict(list=[4, 5, 6]))
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == dict(list=[4, 5, 6])


def test_merge_dict_nested_in_list():
    c1 = OmegaConf.create([1, 2, dict(a=10)])
    c2 = OmegaConf.create([4, 5, dict(b=20)])
    c3 = OmegaConf.merge(c1, c2)
    assert c3 == [4, 5, dict(b=20)]


def test_merge_with_1():
    a = OmegaConf.create()
    b = OmegaConf.create(dict(a=1, b=2))
    a.merge_with(b)
    assert a == b


def test_merge_with_2():
    a = OmegaConf.create()
    a.inner = {}
    b = OmegaConf.create('''
    a : 1
    b : 2
    ''')
    a.inner.merge_with(b)
    assert a.inner == b


def test_nested_map_merge_bug():
    cfg = """
launcher:
  queue: a
  queues:
    local:
      clazz: foo

"""
    cli = """
launcher:
  instances: 2
"""
    cfg = OmegaConf.create(cfg)
    cli = OmegaConf.create(cli)
    ret = OmegaConf.merge(cfg, cli)
    assert ret.launcher.queues is not None


def test_merge_list_list():
    a = OmegaConf.create([1, 2, 3])
    b = OmegaConf.create([4, 5, 6])
    assert a.merge_with(b) == b


def test_merge_with_exception():
    a = OmegaConf.create({})
    b = OmegaConf.create([])
    with raises(TypeError):
        a.merge_with(b)
