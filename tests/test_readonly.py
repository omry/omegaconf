import re

import pytest
from pytest import raises

from omegaconf import OmegaConf, ReadonlyConfigError


@pytest.mark.parametrize(
    "src, func, expectation",
    [
        ({}, lambda c: c.__setitem__("a", 1), raises(ReadonlyConfigError, match="a")),
        (
            dict(a=dict(b=dict(c=1))),
            lambda c: c.__getattr__("a").__getattr__("b").__setitem__("c", 1),
            raises(ReadonlyConfigError, match="a.b.c"),
        ),
        ({}, lambda c: c.update("a.b", 10), raises(ReadonlyConfigError, match="a")),
        (
            dict(a=10),
            lambda c: c.__setattr__("a", 1),
            raises(ReadonlyConfigError, match="a"),
        ),
        (dict(a=10), lambda c: c.pop("a"), raises(ReadonlyConfigError, match="a")),
        (
            dict(a=10),
            lambda c: c.__delitem__("a"),
            raises(ReadonlyConfigError, match="a"),
        ),
        # list
        ([], lambda c: c.__setitem__(0, 1), raises(ReadonlyConfigError, match="0")),
        ([], lambda c: c.update("0.b", 10), raises(ReadonlyConfigError, match="[0]")),
        ([10], lambda c: c.pop(), raises(ReadonlyConfigError)),
        ([0], lambda c: c.__delitem__(0), raises(ReadonlyConfigError, match="[0]")),
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
    with raises(ReadonlyConfigError, match="[0]"):
        c.insert(0, 10)
    assert c == []


def test_readonly_list_insert_deep():
    src = [dict(a=[dict(b=[])])]
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError, match=re.escape("[0].a[0].b[0]")):
        c[0].a[0].b.insert(0, 10)
    assert c == src


def test_readonly_list_append():
    c = OmegaConf.create([])
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError, match="[0]"):
        c.append(10)
    assert c == []


def test_readonly_list_change_item():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError, match="[1]"):
        c[1] = 10
    assert c == [1, 2, 3]


def test_readonly_list_pop():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError, match="[1]"):
        c.pop(1)
    assert c == [1, 2, 3]


def test_readonly_list_del():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError, match="[1]"):
        del c[1]
    assert c == [1, 2, 3]


def test_readonly_list_sort():
    c = OmegaConf.create([3, 1, 2])
    OmegaConf.set_readonly(c, True)
    with raises(ReadonlyConfigError):
        c.sort()
    assert c == [3, 1, 2]


def test_readonly_from_cli():
    c = OmegaConf.create({"foo": {"bar": [1]}})
    OmegaConf.set_readonly(c, True)
    cli = OmegaConf.from_dotlist(["foo.bar=[2]"])
    with raises(ReadonlyConfigError, match="foo.bar"):
        OmegaConf.merge(c, cli)
