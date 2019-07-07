import copy
import re

import pytest

from omegaconf import *
from . import IllegalType


def test_repr_list():
    c = OmegaConf.create([1, 2, 3])
    assert "[1, 2, 3]" == repr(c)


def test_is_empty_list():
    c = OmegaConf.create([1, 2, 3])
    assert not c.is_empty()
    c = OmegaConf.create([])
    assert c.is_empty()


def test_list_value():
    c = OmegaConf.create('a: [1,2]')
    assert {'a': [1, 2]} == c


def test_list_of_dicts():
    v = [
        dict(key1='value1'),
        dict(key2='value2')
    ]
    c = OmegaConf.create(v)
    assert c[0].key1 == 'value1'
    assert c[1].key2 == 'value2'


def test_pretty_list():
    c = OmegaConf.create([
        'item1',
        'item2',
        dict(key3='value3')
    ])
    expected = '''- item1
- item2
- key3: value3
'''
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_list_get_with_default():
    c = OmegaConf.create([None, "???", "found"])
    assert c.get(0, 'default_value') == 'default_value'
    assert c.get(1, 'default_value') == 'default_value'
    assert c.get(2, 'default_value') == 'found'


def test_iterate_list():
    c = OmegaConf.create([1, 2])
    items = [x for x in c]
    assert items[0] == 1
    assert items[1] == 2


def test_list_pop():
    c = OmegaConf.create([1, 2, 3, 4])
    assert c.pop(0) == 1
    assert c.pop() == 4
    assert c == [2, 3]
    with pytest.raises(IndexError):
        c.pop(100)


def test_in_list():
    c = OmegaConf.create([10, 11, dict(a=12)])
    assert 10 in c
    assert 11 in c
    assert dict(a=12) in c
    assert 'blah' not in c


def test_list_config_with_list():
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)


def test_list_config_with_tuple():
    c = OmegaConf.create(())
    assert isinstance(c, ListConfig)


def test_items_on_list():
    c = OmegaConf.create([1, 2])
    with pytest.raises(AttributeError):
        c.items()


def test_list_enumerate():
    src = ['a', 'b', 'c', 'd']
    c = OmegaConf.create(src)
    for i, v in enumerate(c):
        assert src[i] == v
        assert v is not None
        src[i] = None

    for v in src:
        assert v is None


def test_list_delitem():
    c = OmegaConf.create([1, 2, 3])
    assert c == [1, 2, 3]
    del c[0]
    assert c == [2, 3]
    with pytest.raises(IndexError):
        del c[100]


def test_list_len():
    c = OmegaConf.create([1, 2])
    assert len(c) == 2


def test_assign_list_in_list():
    c = OmegaConf.create([10, 11])
    c[0] = ['a', 'b']
    assert c == [['a', 'b'], 11]
    assert isinstance(c[0], ListConfig)


def test_assign_dict_in_list():
    c = OmegaConf.create([None])
    c[0] = dict(foo='bar')
    assert c[0] == dict(foo='bar')
    assert isinstance(c[0], DictConfig)


def test_nested_list_assign_illegal_value():
    with pytest.raises(ValueError, match=re.escape("key a[0]")):
        c = OmegaConf.create(dict(a=[None]))
        c.a[0] = IllegalType()


def test_assign_list_in_dict():
    c = OmegaConf.create(dict())
    c.foo = ['a', 'b']
    assert c == dict(foo=['a', 'b'])
    assert isinstance(c.foo, ListConfig)


def test_list_append():
    c = OmegaConf.create([])
    c.append(1)
    c.append(2)
    c.append({})
    c.append([])
    assert isinstance(c[2], DictConfig)
    assert isinstance(c[3], ListConfig)
    assert c == [1, 2, {}, []]


def test_to_container():
    src = [1, None, dict(a=12), [1, 2]]
    c = OmegaConf.create(src)
    result = c.to_container()
    assert type(result) == type(src)
    assert result == src


def test_pretty_without_resolve():
    c = OmegaConf.create([100, '${0}'])
    # without resolve, references are preserved
    c2 = OmegaConf.create(c.pretty(resolve=False))
    c2[0] = 1000
    assert c2[1] == 1000


def test_pretty_with_resolve():
    c = OmegaConf.create([100, '${0}'])
    # with resolve, references are not preserved.
    c2 = OmegaConf.create(c.pretty(resolve=True))
    c2[0] = 1000
    assert c[1] == 100


def test_index_slice():
    c = OmegaConf.create([10, 11, 12, 13])
    assert c[1:3] == [11, 12]


def test_index_slice2():
    c = OmegaConf.create([10, 11, 12, 13])
    assert c[0:3:2] == [10, 12]


def test_negative_index():
    c = OmegaConf.create([10, 11, 12, 13])
    assert c[-1] == 13


def test_list_dir():
    c = OmegaConf.create([1, 2, 3])
    assert ["0", "1", "2"] == dir(c)


def test_getattr():
    c = OmegaConf.create(['a', 'b', 'c'])
    assert getattr(c, "0") == 'a'
    assert getattr(c, "1") == 'b'
    assert getattr(c, "2") == 'c'
    with pytest.raises(AttributeError):
        getattr(c, "anything")


def test_setitem():
    c = OmegaConf.create(['a', 'b', 'c'])
    c[1] = 10
    assert c == ['a', 10, 'c']


def test_insert():
    c = OmegaConf.create(['a', 'b', 'c'])
    c.insert(1, 100)
    assert c == ['a', 100, 'b', 'c']


def test_sort():
    c = OmegaConf.create(['bbb', 'aa', 'c'])
    c.sort()
    assert ['aa', 'bbb', 'c'] == c
    c.sort(reverse=True)
    assert ['c', 'bbb', 'aa'] == c
    c.sort(key=len)
    assert ['c', 'aa', 'bbb'] == c
    c.sort(key=len, reverse=True)
    assert ['bbb', 'aa', 'c'] == c


@pytest.mark.parametrize('l1,l2', [
    # empty list
    ([], []),
    # simple list
    (['a', 12, '15'], ['a', 12, '15']),
    # raw vs any
    ([1, 2, 12], [1, 2, nodes.UntypedNode(12)]),
    # nested empty dict
    ([12, dict()], [12, dict()]),
    # nested dict
    ([12, dict(c=10)], [12, dict(c=10)]),
    # nested list
    ([1, 2, 3, [10, 20, 30]], [1, 2, 3, [10, 20, 30]]),
    # nested list with any
    ([1, 2, 3, [1, 2, nodes.UntypedNode(3)]], [1, 2, 3, [1, 2, nodes.UntypedNode(3)]])
])
def test_list_eq(l1, l2):
    c1 = OmegaConf.create(l1)
    c2 = OmegaConf.create(l2)

    def eq(a, b):
        assert a == b
        assert b == a
        assert not a != b
        assert not b != a

    eq(c1, c2)
    eq(c1, l1)
    eq(c2, l2)


@pytest.mark.parametrize('input1, input2', [
    ([], [10]),
    ([10], [11]),
    ([12], [nodes.UntypedNode(13)]),
    ([12, dict()], [13, dict()]),
    ([12, dict(c=10)], [13, dict(c=10)]),
    ([12, [1, 2, 3]], [12, [10, 2, 3]]),
    ([12, [1, 2, nodes.UntypedNode(3)]], [12, [1, 2, nodes.UntypedNode(30)]]),
])
def test_list_not_eq(input1, input2):
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def neq(a, b):
        assert a != b
        assert b != a
        assert not a == b
        assert not b == a

    neq(c1, c2)


def test_insert_throws_not_changing_list():
    c = OmegaConf.create([])
    with pytest.raises(ValueError):
        c.insert(0, IllegalType())
    assert len(c) == 0
    assert c == []


def test_append_throws_not_changing_list():
    c = OmegaConf.create([])
    with pytest.raises(ValueError):
        c.append(IllegalType())
    assert len(c) == 0
    assert c == []


def test_deepcopy():
    c1 = OmegaConf.create([1, 2, 3])
    c2 = copy.deepcopy(c1)
    assert c2 == c1
    c1[0] = 10
    assert c1[0] == 10
    assert c2[0] == 1


def test_hash():
    c1 = OmegaConf.create([10])
    c2 = OmegaConf.create([10])
    assert hash(c1) == hash(c2)
    c2[0] = 20
    assert hash(c1) != hash(c2)
