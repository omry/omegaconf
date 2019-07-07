import pytest
import re
from omegaconf import *


# dict *
def test_freeze_dict():
    c = OmegaConf.create()
    assert not c._frozen()
    c.freeze(True)
    assert c._frozen()
    c.freeze(False)
    assert not c._frozen()
    c.freeze(None)
    assert not c._frozen()


def test_freeze_nested_dict():
    c = OmegaConf.create(dict(a=dict(b=2)))
    assert not c._frozen()
    assert not c.a._frozen()
    c.freeze(True)
    assert c._frozen()
    assert c.a._frozen()
    c.freeze(False)
    assert not c._frozen()
    assert not c.a._frozen()
    c.freeze(None)
    assert not c._frozen()
    assert not c.a._frozen()
    c.a.freeze(True)
    assert not c._frozen()
    assert c.a._frozen()


def test_frozen_dict_add_field():
    c = OmegaConf.create()
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a'):
        c.a = 1
    assert c == {}


def test_frozen_dict_add_field_deep():
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a.b.c'):
        c.a.b.c = 1
    assert c == dict(a=dict(b=dict(c=1)))


def test_frozen_dict_update():
    c = OmegaConf.create()
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a'):
        c.update("a.b", 10)
    assert c == {}


def test_frozen_dict_change_leaf():
    c = OmegaConf.create(dict(a=10))
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a'):
        c.a = 20
    assert c == dict(a=10)


def test_frozen_dict_pop():
    c = OmegaConf.create(dict(a=10))
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a'):
        c.pop('a')
    assert c == dict(a=10)


def test_frozen_dict_del():
    c = OmegaConf.create(dict(a=10))
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='a'):
        del c['a']
    assert c == dict(a=10)


# LIST #

def test_freeze_list():
    c = OmegaConf.create([])
    assert not c._frozen()
    c.freeze(True)
    assert c._frozen()
    c.freeze(False)
    assert not c._frozen()
    c.freeze(None)
    assert not c._frozen()


def test_freeze_nested_list():
    c = OmegaConf.create([[1]])
    assert not c._frozen()
    assert not c[0]._frozen()
    c.freeze(True)
    assert c._frozen()
    assert c[0]._frozen()
    c.freeze(False)
    assert not c._frozen()
    assert not c[0]._frozen()
    c.freeze(None)
    assert not c._frozen()
    assert not c[0]._frozen()
    c[0].freeze(True)
    assert not c._frozen()
    assert c[0]._frozen()


def test_frozen_list_insert():
    c = OmegaConf.create([])
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='[0]'):
        c.insert(0, 10)
    assert c == []


def test_frozen_list_insert_deep():
    src = [dict(a=[dict(b=[])])]
    c = OmegaConf.create(src)
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match=re.escape('[0].a[0].b[0]')):
        c[0].a[0].b.insert(0, 10)
    assert c == src


def test_frozen_list_append():
    c = OmegaConf.create([])
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='[0]'):
        c.append(10)
    assert c == []


def test_frozen_list_change_item():
    c = OmegaConf.create([1, 2, 3])
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='[1]'):
        c[1] = 10
    assert c == [1, 2, 3]


def test_frozen_list_pop():
    c = OmegaConf.create([1, 2, 3])
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='[1]'):
        c.pop(1)
    assert c == [1, 2, 3]


def test_frozen_list_del():
    c = OmegaConf.create([1, 2, 3])
    c.freeze(True)
    with pytest.raises(FrozenConfigError, match='[1]'):
        del c[1]
    assert c == [1, 2, 3]


def test_frozen_list_sort():
    c = OmegaConf.create([3, 1, 2])
    c.freeze(True)
    with pytest.raises(FrozenConfigError):
        c.sort()
    assert c == [3, 1, 2]
