import pytest

from omegaconf import OmegaConf, Config


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


@pytest.mark.parametrize('a_, b_, expected', [
    # merge dict 1
    (dict(a=None), dict(b=None), dict(a=None, b=None)),
    # merge dict 2
    (dict(a=1, b=2), dict(b=3), dict(a=1, b=3)),
    # merge with nested dict
    (dict(a=1, b=2), dict(b=dict(c=3)), dict(a=1, b=dict(c=3))),
    # merge nested with dict
    (dict(b=dict(c=1)), dict(b=1), dict(b=1)),
    # merge lists
    ([1, 2, 3], [4, 5, 6], [4, 5, 6]),
    # merge nested lists
    ([[1, 2, 3]], [[4, 5, 6]], [[4, 5, 6]]),
    # merge dict(list)
    (dict(list=[1, 2, 3]), dict(list=[4, 5, 6]), dict(list=[4, 5, 6])),
    # merge list(dict)
    ([1, 2, dict(a=10)], [4, 5, dict(b=20)], [4, 5, dict(b=20)]),
])
def test_merge(a_, b_, expected):
    a = OmegaConf.create(a_)
    b = OmegaConf.create(b_)
    c = OmegaConf.merge(a, b)
    # verify merge did not touch input
    assert a == a_
    assert b == b_
    # verify merge result is expected
    assert expected == c


# like above but don't verify merge does not change because even eq does not work no tuples because we convert
# them to a list
@pytest.mark.parametrize('a_, b_, expected', [
    ((1, 2, 3), (4, 5, 6), [4, 5, 6]),
])
def test_merge_no_eq_verify(a_, b_, expected):
    a = OmegaConf.create(a_)
    b = OmegaConf.create(b_)
    c = OmegaConf.merge(a, b)
    # verify merge result is expected
    assert expected == c


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


def test_3way_dict_merge():
    c1 = OmegaConf.create('{a: 1, b: 2}')
    c2 = OmegaConf.create('{b: 3}')
    c3 = OmegaConf.create('{a: 2, c: 3}')
    c4 = OmegaConf.merge(c1, c2, c3)
    assert {'a': 2, 'b': 3, 'c': 3} == c4


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
    a.merge_with(b)
    assert a == b


def test_merge_with_exception():
    a = OmegaConf.create({})
    b = OmegaConf.create([])
    with pytest.raises(TypeError):
        a.merge_with(b)


def test_merge_list_list__deprecated():
    a = OmegaConf.create([1, 2, 3])
    b = OmegaConf.create([4, 5, 6])
    a.merge_from(b)
    assert a == b


def test_merge_with_interpolation():
    src = dict(
        data=123,
        reference='${data}'
    )
    a = OmegaConf.create(src)
    b = OmegaConf.create(src)
    merged = OmegaConf.merge(a, b)
    merged.data = 456
    assert merged.reference == 456
    assert merged.data == 456
