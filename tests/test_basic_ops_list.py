# -*- coding: utf-8 -*-
import re
from typing import Any, List, Optional

import pytest

from omegaconf import AnyNode, ListConfig, OmegaConf
from omegaconf.errors import (
    ConfigKeyError,
    ConfigTypeError,
    KeyValidationError,
    MissingMandatoryValue,
    UnsupportedValueType,
    ValidationError,
)
from omegaconf.nodes import IntegerNode, StringNode

from . import Color, IllegalType, User, does_not_raise


def test_list_value() -> None:
    c = OmegaConf.create("a: [1,2]")
    assert {"a": [1, 2]} == c


def test_list_of_dicts() -> None:
    v = [dict(key1="value1"), dict(key2="value2")]
    c = OmegaConf.create(v)
    assert c[0].key1 == "value1"
    assert c[1].key2 == "value2"


def test_list_get_with_default() -> None:
    c = OmegaConf.create([None, "???", "found"])
    assert c.get(0, "default_value") == "default_value"
    assert c.get(1, "default_value") == "default_value"
    assert c.get(2, "default_value") == "found"


@pytest.mark.parametrize(  # type: ignore
    "input_, expected, list_key",
    [
        pytest.param([1, 2], [1, 2], None, id="simple"),
        pytest.param(["${1}", 2], [2, 2], None, id="interpolation"),
        pytest.param(
            {
                "defaults": [
                    {"optimizer": "adam"},
                    {"dataset": "imagenet"},
                    {"foo": "${defaults.0.optimizer}_${defaults.1.dataset}"},
                ]
            },
            [{"optimizer": "adam"}, {"dataset": "imagenet"}, {"foo": "adam_imagenet"}],
            "defaults",
            id="str_interpolation",
        ),
    ],
)
def test_iterate_list(input_: Any, expected: Any, list_key: str) -> None:
    c = OmegaConf.create(input_)
    if list_key is not None:
        lst = c.get(list_key)
    else:
        lst = c
    items = [x for x in lst]
    assert items == expected


def test_iterate_list_with_missing_interpolation() -> None:
    c = OmegaConf.create([1, "${10}"])
    itr = iter(c)
    assert 1 == next(itr)
    with pytest.raises(ConfigKeyError):
        next(itr)


def test_iterate_list_with_missing() -> None:
    c = OmegaConf.create([1, "???"])
    itr = iter(c)
    assert 1 == next(itr)
    with pytest.raises(MissingMandatoryValue):
        next(itr)


def test_items_with_interpolation() -> None:
    c = OmegaConf.create(["foo", "${0}"])
    assert c == ["foo", "foo"]


def test_list_pop() -> None:
    c = OmegaConf.create([1, 2, 3, 4])
    assert c.pop(0) == 1
    assert c.pop() == 4
    assert c == [2, 3]
    with pytest.raises(IndexError):
        c.pop(100)
    validate_list_keys(c)


def test_list_pop_on_unexpected_exception_not_modifying() -> None:
    src = [1, 2, 3, 4]
    c = OmegaConf.create(src)

    with pytest.raises(ConfigTypeError):
        c.pop("foo")  # type: ignore
    assert c == src


def test_in_list() -> None:
    c = OmegaConf.create([10, 11, dict(a=12)])
    assert 10 in c
    assert 11 in c
    assert dict(a=12) in c
    assert "blah" not in c


def test_list_config_with_list() -> None:
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)


def test_list_config_with_tuple() -> None:
    c = OmegaConf.create(())
    assert isinstance(c, ListConfig)


def test_items_on_list() -> None:
    c = OmegaConf.create([1, 2])
    with pytest.raises(AttributeError):
        c.items()


def test_list_enumerate() -> None:
    src: List[Optional[str]] = ["a", "b", "c", "d"]
    c = OmegaConf.create(src)
    for i, v in enumerate(c):
        assert src[i] == v
        assert v is not None
        src[i] = None

    for v in src:
        assert v is None


def test_list_delitem() -> None:
    c = OmegaConf.create([1, 2, 3])
    assert c == [1, 2, 3]
    del c[0]
    assert c == [2, 3]
    with pytest.raises(IndexError):
        del c[100]

    validate_list_keys(c)


@pytest.mark.parametrize(  # type: ignore
    "lst,expected",
    [
        (OmegaConf.create([1, 2]), 2),
        (ListConfig(content=None), 0),
        (ListConfig(content="???"), 0),
    ],
)
def test_list_len(lst: Any, expected: Any) -> None:
    assert len(lst) == expected


def test_nested_list_assign_illegal_value() -> None:
    c = OmegaConf.create({"a": [None]})
    with pytest.raises(
        UnsupportedValueType,
        match=re.escape(
            "Value 'IllegalType' is not a supported primitive type\n\tfull_key: a[0]"
        ),
    ):
        c.a[0] = IllegalType()


def test_list_append() -> None:
    c = OmegaConf.create([])
    c.append(1)
    c.append(2)
    c.append({})
    c.append([])
    assert c == [1, 2, {}, []]

    validate_list_keys(c)


@pytest.mark.parametrize(  # type: ignore
    "lc,element,expected",
    [
        pytest.param(
            ListConfig(content=[], element_type=int),
            "foo",
            pytest.raises(
                ValidationError,
                match=re.escape("Value 'foo' could not be converted to Integer"),
            ),
            id="append_str_to_list[int]",
        ),
        pytest.param(
            ListConfig(content=[], element_type=Color),
            "foo",
            pytest.raises(
                ValidationError,
                match=re.escape(
                    "Invalid value 'foo', expected one of [RED, GREEN, BLUE]"
                ),
            ),
            id="append_str_to_list[Color]",
        ),
        pytest.param(
            ListConfig(content=[], element_type=User),
            "foo",
            pytest.raises(
                ValidationError,
                match=re.escape(
                    "Invalid type assigned : str is not a subclass of User. value: foo"
                ),
            ),
            id="append_str_to_list[User]",
        ),
        pytest.param(
            ListConfig(content=[], element_type=User),
            {"name": "Bond", "age": 7},
            pytest.raises(
                ValidationError,
                match=re.escape(
                    "Invalid type assigned : dict is not a subclass of User. value: {'name': 'Bond', 'age': 7}"
                ),
            ),
            id="list:convert_dict_to_user",
        ),
        pytest.param(
            ListConfig(content=[], element_type=User),
            {},
            pytest.raises(
                ValidationError,
                match=re.escape(
                    "Invalid type assigned : dict is not a subclass of User. value: {}"
                ),
            ),
            id="list:convert_empty_dict_to_user",
        ),
    ],
)
def test_append_invalid_element_type(
    lc: ListConfig, element: Any, expected: Any
) -> None:
    with expected:
        lc.append(element)


@pytest.mark.parametrize(  # type: ignore
    "lc,element,expected",
    [
        pytest.param(
            ListConfig(content=[], element_type=int),
            "10",
            10,
            id="list:convert_str_to_int",
        ),
        pytest.param(
            ListConfig(content=[], element_type=float),
            "10",
            10.0,
            id="list:convert_str_to_float",
        ),
        pytest.param(
            ListConfig(content=[], element_type=Color),
            "RED",
            Color.RED,
            id="list:convert_str_to_float",
        ),
    ],
)
def test_append_convert(lc: ListConfig, element: Any, expected: Any) -> None:
    lc.append(element)
    value = lc[-1]
    assert value == expected
    assert type(value) == type(expected)


@pytest.mark.parametrize(  # type: ignore
    "index, expected", [(slice(1, 3), [11, 12]), (slice(0, 3, 2), [10, 12]), (-1, 13)]
)
def test_list_index(index: Any, expected: Any) -> None:
    c = OmegaConf.create([10, 11, 12, 13])
    assert c[index] == expected


@pytest.mark.parametrize(  # type: ignore
    "cfg, expected",
    [
        (OmegaConf.create([1, 2, 3]), ["0", "1", "2"]),
        (ListConfig(content="???"), []),
        (ListConfig(content=None), []),
    ],
)
def test_list_dir(cfg: Any, expected: Any) -> None:
    assert dir(cfg) == expected


def validate_list_keys(c: Any) -> None:
    # validate keys are maintained
    for i in range(len(c)):
        assert c._get_node(i)._metadata.key == i


@pytest.mark.parametrize(  # type: ignore
    "input_, index, value, expected, expected_node_type, expectation",
    [
        (["a", "b", "c"], 1, 100, ["a", 100, "b", "c"], AnyNode, None),
        (
            ["a", "b", "c"],
            1,
            IntegerNode(100),
            ["a", 100, "b", "c"],
            IntegerNode,
            None,
        ),
        (["a", "b", "c"], 1, "foo", ["a", "foo", "b", "c"], AnyNode, None),
        (
            ["a", "b", "c"],
            1,
            StringNode("foo"),
            ["a", "foo", "b", "c"],
            StringNode,
            None,
        ),
        (
            ListConfig(element_type=int, content=[]),
            0,
            "foo",
            None,
            None,
            ValidationError,
        ),
    ],
)
def test_insert(
    input_: List[str],
    index: int,
    value: Any,
    expected: Any,
    expected_node_type: type,
    expectation: Any,
) -> None:
    c = OmegaConf.create(input_)
    if expectation is None:
        c.insert(index, value)
        assert c == expected
        assert type(c._get_node(index)) == expected_node_type
    else:
        with pytest.raises(expectation):
            c.insert(index, value)
    validate_list_keys(c)


@pytest.mark.parametrize(  # type: ignore
    "lst,idx,value,expectation",
    [
        (ListConfig(content=None), 0, 10, pytest.raises(TypeError)),
        (ListConfig(content="???"), 0, 10, pytest.raises(MissingMandatoryValue)),
    ],
)
def test_insert_special_list(lst: Any, idx: Any, value: Any, expectation: Any) -> None:
    with expectation:
        lst.insert(idx, value)


@pytest.mark.parametrize(  # type: ignore
    "src, append, result",
    [
        ([], [], []),
        ([1, 2], [3], [1, 2, 3]),
        ([1, 2], ("a", "b", "c"), [1, 2, "a", "b", "c"]),
    ],
)
def test_extend(src: List[Any], append: List[Any], result: List[Any]) -> None:
    lst = OmegaConf.create(src)
    lst.extend(append)
    assert lst == result


@pytest.mark.parametrize(  # type: ignore
    "src, remove, result, expectation",
    [
        ([10], 10, [], does_not_raise()),
        ([], "oops", None, pytest.raises(ValueError)),
        ([0, dict(a="blah"), 10], dict(a="blah"), [0, 10], does_not_raise()),
        ([1, 2, 1, 2], 2, [1, 1, 2], does_not_raise()),
    ],
)
def test_remove(src: List[Any], remove: Any, result: Any, expectation: Any) -> None:
    with expectation:
        lst = OmegaConf.create(src)
        assert isinstance(lst, ListConfig)
        lst.remove(remove)
        assert lst == result


@pytest.mark.parametrize("src", [[], [1, 2, 3], [None, dict(foo="bar")]])  # type: ignore
@pytest.mark.parametrize("num_clears", [1, 2])  # type: ignore
def test_clear(src: List[Any], num_clears: int) -> None:
    lst = OmegaConf.create(src)
    for i in range(num_clears):
        lst.clear()
    assert lst == []


@pytest.mark.parametrize(  # type: ignore
    "src, item, expected_index, expectation",
    [
        ([], 20, -1, pytest.raises(ValueError)),
        ([10, 20], 10, 0, does_not_raise()),
        ([10, 20], 20, 1, does_not_raise()),
    ],
)
def test_index(
    src: List[Any], item: Any, expected_index: int, expectation: Any
) -> None:
    with expectation:
        lst = OmegaConf.create(src)
        assert lst.index(item) == expected_index


def test_index_with_range() -> None:
    lst = OmegaConf.create([10, 20, 30, 40, 50])
    assert lst.index(x=30) == 2
    assert lst.index(x=30, start=1) == 2
    assert lst.index(x=30, start=1, end=3) == 2
    with pytest.raises(ValueError):
        lst.index(x=30, start=3)

    with pytest.raises(ValueError):
        lst.index(x=30, end=2)


@pytest.mark.parametrize(  # type: ignore
    "src, item, count",
    [([], 10, 0), ([10], 10, 1), ([10, 2, 10], 10, 2), ([10, 2, 10], None, 0)],
)
def test_count(src: List[Any], item: Any, count: int) -> None:
    lst = OmegaConf.create(src)
    assert lst.count(item) == count


def test_sort() -> None:
    c = OmegaConf.create(["bbb", "aa", "c"])
    c.sort()
    assert ["aa", "bbb", "c"] == c
    c.sort(reverse=True)
    assert ["c", "bbb", "aa"] == c
    c.sort(key=len)
    assert ["c", "aa", "bbb"] == c
    c.sort(key=len, reverse=True)
    assert ["bbb", "aa", "c"] == c


def test_insert_throws_not_changing_list() -> None:
    c = OmegaConf.create([])
    with pytest.raises(ValueError):
        c.insert(0, IllegalType())
    assert len(c) == 0
    assert c == []


def test_append_throws_not_changing_list() -> None:
    c = OmegaConf.create([])
    v = IllegalType()
    with pytest.raises(ValueError):
        c.append(v)
    assert len(c) == 0
    assert c == []
    validate_list_keys(c)


def test_hash() -> None:
    c1 = OmegaConf.create([10])
    c2 = OmegaConf.create([10])
    assert hash(c1) == hash(c2)
    c2[0] = 20
    assert hash(c1) != hash(c2)


@pytest.mark.parametrize(
    "in_list1, in_list2,in_expected",
    [
        ([], [], []),
        ([1, 2], [3, 4], [1, 2, 3, 4]),
        (["x", 2, "${0}"], [5, 6, 7], ["x", 2, "x", 5, 6, 7]),
    ],
)
class TestListAdd:
    def test_list_plus(
        self, in_list1: List[Any], in_list2: List[Any], in_expected: List[Any]
    ) -> None:
        list1 = OmegaConf.create(in_list1)
        list2 = OmegaConf.create(in_list2)
        expected = OmegaConf.create(in_expected)
        ret = list1 + list2
        assert ret == expected

    def test_list_plus_eq(
        self, in_list1: List[Any], in_list2: List[Any], in_expected: List[Any]
    ) -> None:
        list1 = OmegaConf.create(in_list1)
        list2 = OmegaConf.create(in_list2)
        expected = OmegaConf.create(in_expected)
        list1 += list2
        assert list1 == expected


def test_deep_add() -> None:
    cfg = OmegaConf.create({"foo": [1, 2, "${bar}"], "bar": "xx"})
    lst = cfg.foo + [10, 20]
    assert lst == [1, 2, "xx", 10, 20]


def test_set_with_invalid_key() -> None:
    cfg = OmegaConf.create([1, 2, 3])
    with pytest.raises(KeyValidationError):
        cfg["foo"] = 4  # type: ignore


@pytest.mark.parametrize(  # type: ignore
    "lst,idx,expected",
    [
        (OmegaConf.create([1, 2]), 0, 1),
        (ListConfig(content=None), 0, TypeError),
        (ListConfig(content="???"), 0, MissingMandatoryValue),
    ],
)
def test_getitem(lst: Any, idx: Any, expected: Any) -> None:
    if isinstance(expected, type):
        with pytest.raises(expected):
            lst.__getitem__(idx)
    else:
        assert lst.__getitem__(idx) == expected


@pytest.mark.parametrize(  # type: ignore
    "sli",
    [
        (slice(None, None, None)),
        (slice(1, None, None)),
        (slice(-1, None, None)),
        (slice(None, 1, None)),
        (slice(None, -1, None)),
        (slice(None, None, 1)),
        (slice(None, None, -1)),
        (slice(1, None, -2)),
        (slice(None, 1, -2)),
        (slice(1, 3, -1)),
        (slice(3, 1, -1)),
    ],
)
def test_getitem_slice(sli: slice) -> None:
    lst = [1, 2, 3]
    olst = OmegaConf.create([1, 2, 3])
    expected = lst[sli.start : sli.stop : sli.step]
    assert olst.__getitem__(sli) == expected


@pytest.mark.parametrize(  # type: ignore
    "lst,idx,expected",
    [
        (OmegaConf.create([1, 2]), 0, 1),
        (OmegaConf.create([1, 2]), "foo", KeyValidationError),
        (ListConfig(content=None), 0, TypeError),
        (ListConfig(content="???"), 0, MissingMandatoryValue),
    ],
)
def test_get(lst: Any, idx: Any, expected: Any) -> None:
    if isinstance(expected, type):
        with pytest.raises(expected):
            lst.get(idx)
    else:
        lst.__getitem__(idx) == expected


def test_getattr() -> None:
    src = ["a", "b", "c"]
    cfg = OmegaConf.create(src)
    with pytest.raises(AttributeError):
        getattr(cfg, "foo")
    assert getattr(cfg, "0") == src[0]
    assert getattr(cfg, "1") == src[1]
    assert getattr(cfg, "2") == src[2]
