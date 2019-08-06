import copy

import pytest

from omegaconf import *


@pytest.mark.parametrize('input_, key, value, expected', [
    # dict
    (dict(), 'foo', 10, dict(foo=10)),
    (dict(), 'foo', IntegerNode(10), dict(foo=10)),
    (dict(foo=5), 'foo', IntegerNode(10), dict(foo=10)),
    # changing type of a node
    (dict(foo=StringNode('str')), 'foo', IntegerNode(10), dict(foo=10)),
    # list
    ([0], 0, 10, [10]),
    (['a', 'b', 'c'], 1, 10, ['a', 10, 'c']),
    ([1, 2], 1, IntegerNode(10), [1, 10]),
    ([1, IntegerNode(2)], 1, IntegerNode(10), [1, 10]),
    # changing type of a node
    ([1, StringNode('str')], 1, IntegerNode(10), [1, 10]),
])
def test_set_value(input_, key, value, expected):
    c = OmegaConf.create(input_)
    c[key] = value
    assert c == expected


@pytest.mark.parametrize('input_, key, value', [
    # dict
    (dict(foo=IntegerNode(10)), 'foo', 'str'),
    # list
    ([1, IntegerNode(10)], 1, 'str'),

])
def test_set_value_validation_fail(input_, key, value):
    c = OmegaConf.create(input_)
    with pytest.raises(ValidationError):
        c[key] = value


@pytest.mark.parametrize('input_', [
    [1, 2, 3],
    [1, 2, dict(a=3)],
    [1, 2, [10, 20]],
    dict(b=dict(b=10)),
    dict(b=[1, 2, 3]),
])
def test_to_container_returns_primitives(input_):
    def assert_container_with_primitives(container):
        if isinstance(container, list):
            for v in container:
                assert_container_with_primitives(v)
        elif isinstance(container, dict):
            for _k, v in container.items():
                assert_container_with_primitives(v)
        else:
            assert isinstance(container, (int, str, bool))

    c = OmegaConf.create(input_)
    res = c.to_container(resolve=True)
    assert_container_with_primitives(res)


@pytest.mark.parametrize('input_, is_empty', [
    ([], True),
    ({}, True),
    ([1, 2], False),
    (dict(a=10), False),
])
def test_empty(input_, is_empty):
    c = OmegaConf.create(input_)
    assert c.is_empty() == is_empty


@pytest.mark.parametrize('input_', [
    [],
    {},
    [1, 2, 3],
    [1, 2, dict(a=3)],
    [1, 2, [10, 20]],
    dict(b=dict(b=10)),
    dict(b=[1, 2, 3]),
])
def test_repr(input_):
    c = OmegaConf.create(input_)
    assert repr(input_) == repr(c)


@pytest.mark.parametrize('input_', [
    [],
    {},
    [1, 2, 3],
    [1, 2, dict(a=3)],
    [1, 2, [10, 20]],
    dict(b=dict(b=10)),
    dict(b=[1, 2, 3]),
])
def test_str(input_):
    c = OmegaConf.create(input_)
    assert str(input_) == str(c)


def test_flag_dict():
    c = OmegaConf.create()
    assert not c._get_flag('foo')
    c._set_flag('foo', True)
    assert c._get_flag('foo')
    c._set_flag('foo', False)
    assert not c._get_flag('foo')
    c._set_flag('foo', None)
    assert not c._get_flag('foo')


def test_freeze_nested_dict():
    c = OmegaConf.create(dict(a=dict(b=2)))
    assert not c._get_flag('foo')
    assert not c.a._get_flag('foo')
    c._set_flag('foo', True)
    assert c._get_flag('foo')
    assert c.a._get_flag('foo')
    c._set_flag('foo', False)
    assert not c._get_flag('foo')
    assert not c.a._get_flag('foo')
    c._set_flag('foo', None)
    assert not c._get_flag('foo')
    assert not c.a._get_flag('foo')
    c.a._set_flag('foo', True)
    assert not c._get_flag('foo')
    assert c.a._get_flag('foo')


copy_list = [
    [],
    [1, 2, 3],
    dict(),
    dict(a=10),
]


@pytest.mark.parametrize('src', copy_list)
def test_deepcopy(src):
    c1 = OmegaConf.create(src)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        c2.append(1000)
    elif isinstance(c2, DictConfig):
        c2.foo = 'bar'
    assert c1 != c2


@pytest.mark.parametrize('src', copy_list)
def test_deepcopy_readonly(src):
    c1 = OmegaConf.create(src)
    OmegaConf.set_readonly(c1, True)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        with pytest.raises(ReadonlyConfigError):
            c2.append(1000)
    elif isinstance(c2, DictConfig):
        with pytest.raises(ReadonlyConfigError):
            c2.foo = 'bar'
    assert c1 == c2


@pytest.mark.parametrize('src', copy_list)
def test_deepcopy_struct(src):
    c1 = OmegaConf.create(src)
    OmegaConf.set_struct(c1, True)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        c2.append(1000)
    elif isinstance(c2, DictConfig):
        with pytest.raises(KeyError):
            c2.foo = 'bar'


def test_deepcopy_after_del():
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(foo=[1, 2, 3], bar=10))
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    del c1['foo']
    c3 = copy.deepcopy(c1)
    assert c1 == c3


def test_deepcopy_with_interpolation():
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(a=dict(b='${c}'), c=10))
    assert c1.a.b == 10
    c2 = copy.deepcopy(c1)
    assert c2.a.b == 10
