import copy

import pytest

from omegaconf import OmegaConf, ListConfig, DictConfig, ReadonlyConfigError


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
