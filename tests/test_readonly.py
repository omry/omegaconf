import pytest
import re
from omegaconf import *


def test_readonly_dict_add_field():
    c = OmegaConf.create()
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a'):
        c.a = 1
    assert c == {}


def test_readonly_dict_add_field_deep():
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a.b.c'):
        c.a.b.c = 1
    assert c == dict(a=dict(b=dict(c=1)))


def test_readonly_dict_update():
    c = OmegaConf.create()
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a'):
        c.update("a.b", 10)
    assert c == {}


def test_readonly_dict_change_leaf():
    c = OmegaConf.create(dict(a=10))
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a'):
        c.a = 20
    assert c == dict(a=10)


def test_readonly_dict_pop():
    c = OmegaConf.create(dict(a=10))
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a'):
        c.pop('a')
    assert c == dict(a=10)


def test_readonly_dict_del():
    c = OmegaConf.create(dict(a=10))
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='a'):
        del c['a']
    assert c == dict(a=10)


# LIST #
def test_freeze_list():
    c = OmegaConf.create([])
    assert not OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, True)
    assert OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, False)
    assert not OmegaConf.is_readonly(c)
    OmegaConf.set_readonly(c, None)
    assert not OmegaConf.is_readonly(c)


def test_freeze_nested_list():
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
    with pytest.raises(ReadonlyConfigError, match='[0]'):
        c.insert(0, 10)
    assert c == []


def test_readonly_list_insert_deep():
    src = [dict(a=[dict(b=[])])]
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match=re.escape('[0].a[0].b[0]')):
        c[0].a[0].b.insert(0, 10)
    assert c == src


def test_readonly_list_append():
    c = OmegaConf.create([])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='[0]'):
        c.append(10)
    assert c == []


def test_readonly_list_change_item():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='[1]'):
        c[1] = 10
    assert c == [1, 2, 3]


def test_readonly_list_pop():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='[1]'):
        c.pop(1)
    assert c == [1, 2, 3]


def test_readonly_list_del():
    c = OmegaConf.create([1, 2, 3])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError, match='[1]'):
        del c[1]
    assert c == [1, 2, 3]


def test_readonly_list_sort():
    c = OmegaConf.create([3, 1, 2])
    OmegaConf.set_readonly(c, True)
    with pytest.raises(ReadonlyConfigError):
        c.sort()
    assert c == [3, 1, 2]
