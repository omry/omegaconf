import pytest

from omegaconf import OmegaConf


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
    assert not c.get_flag('foo')
    c.set_flag('foo', True)
    assert c.get_flag('foo')
    c.set_flag('foo', False)
    assert not c.get_flag('foo')
    c.set_flag('foo', None)
    assert not c.get_flag('foo')


def test_freeze_nested_dict():
    c = OmegaConf.create(dict(a=dict(b=2)))
    assert not c.get_flag('foo')
    assert not c.a.get_flag('foo')
    c.set_flag('foo', True)
    assert c.get_flag('foo')
    assert c.a.get_flag('foo')
    c.set_flag('foo', False)
    assert not c.get_flag('foo')
    assert not c.a.get_flag('foo')
    c.set_flag('foo', None)
    assert not c.get_flag('foo')
    assert not c.a.get_flag('foo')
    c.a.set_flag('foo', True)
    assert not c.get_flag('foo')
    assert c.a.get_flag('foo')
