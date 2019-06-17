from omegaconf import OmegaConf
from omegaconf.omegaconf import Config


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
