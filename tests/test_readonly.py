import re

import pytest

from omegaconf import ReadonlyConfigError, OmegaConf


@pytest.mark.parametrize(
    "src, func, expectation",
    [
        (
            {},
            lambda c: c.__setitem__("a", 1),
            pytest.raises(ReadonlyConfigError, match="a"),
        ),
        (
            dict(a=dict(b=dict(c=1))),
            lambda c: c.__getattr__("a").__getattr__("b").__setitem__("c", 1),
            pytest.raises(ReadonlyConfigError, match="a.b.c"),
        ),
        (
            {},
            lambda c: c.update("a.b", 10),
            pytest.raises(ReadonlyConfigError, match="a"),
        ),
        (
            dict(a=10),
            lambda c: c.__setattr__("a", 1),
            pytest.raises(ReadonlyConfigError, match="a"),
        ),
        (
            dict(a=10),
            lambda c: c.pop("a"),
            pytest.raises(ReadonlyConfigError, match="a"),
        ),
        (
            dict(a=10),
            lambda c: c.__delitem__("a"),
            pytest.raises(ReadonlyConfigError, match="a"),
        ),
    ],
)
def test_readonly(src, func, expectation):
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)
    with expectation:
        func(c)
    assert c == src


@pytest.mark.parametrize("src", [{}, []])
def test_readonly_flag(src):
    c = OmegaConf.create(src)
    assert not OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, True)
    assert OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, False)
    assert not OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, None)
    assert not OmegaConf.is_readonly(c)


def test_readonly_nested_list():
    c = OmegaConf.create([[1]])
    assert not OmegaConf.is_readonly(c)
    assert not OmegaConf.is_readonly(c[0])
    OmegaConf.set_readonly(c, True)
    assert OmegaConf.is_readonly(c)
    assert OmegaConf.is_readonly(c[0])
    OmegaConf.set_readonly(c, False)
    assert not OmegaConf.is_readonly(c)
    assert not OmegaConf.is_readonly(c[0])
    OmegaConf.set_readonly(c, None)
    assert not OmegaConf.is_readonly(c)
    assert not OmegaConf.is_readonly(c[0])
    OmegaConf.set_readonly(c[0], True)
    assert not OmegaConf.is_readonly(c)
    assert OmegaConf.is_readonly(c[0])


def test_readonly_list_insert():
    c = OmegaConf.create([])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match="[0]"):
        c.insert(0, 10)
    assert c == []


def test_readonly_list_insert_deep():
    src = [dict(a=[dict(b=[])])]
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match=re.escape("[0].a[0].b[0]")):
        c[0].a[0].b.insert(0, 10)
    assert c == src


def test_readonly_list_append():
    c = OmegaConf.create([])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match="[0]"):
        c.append(10)
    assert c == []


def test_readonly_list_change_item():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match="[1]"):
        c[1] = 10
    assert c == [1, 2, 3]


def test_readonly_list_pop():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match="[1]"):
        c.pop(1)
    assert c == [1, 2, 3]


def test_readonly_list_del():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match="[1]"):
        del c[1]
    assert c == [1, 2, 3]


def test_readonly_list_sort():
    c = OmegaConf.create([3, 1, 2])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError):
        c.sort()
    assert c == [3, 1, 2]
