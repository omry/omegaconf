# -*- coding: utf-8 -*-
import re
from contextlib import nullcontext
from pathlib import Path
from textwrap import dedent
from typing import Any, Callable, List, MutableSequence, Optional, Union

from _pytest.python_api import RaisesContext
from pytest import mark, param, raises

from omegaconf import MISSING, AnyNode, DictConfig, ListConfig, OmegaConf, flag_override
from omegaconf._utils import _ensure_container
from omegaconf.base import Node
from omegaconf.errors import (
    ConfigTypeError,
    InterpolationKeyError,
    InterpolationToMissingValueError,
    KeyValidationError,
    MissingMandatoryValue,
    UnsupportedValueType,
    ValidationError,
)
from omegaconf.nodes import IntegerNode, StringNode
from tests import Color, IllegalType, User


def test_list_value() -> None:
    c = OmegaConf.create("a: [1,2]")
    assert {"a": [1, 2]} == c


def test_list_of_dicts() -> None:
    v = [dict(key1="value1"), dict(key2="value2")]
    c = OmegaConf.create(v)
    assert c[0].key1 == "value1"
    assert c[1].key2 == "value2"


@mark.parametrize("default", [None, 0, "default"])
@mark.parametrize(
    ("cfg", "key"),
    [
        (["???"], 0),
        ([DictConfig(content="???")], 0),
        ([ListConfig(content="???")], 0),
    ],
)
def test_list_get_return_default(cfg: List[Any], key: int, default: Any) -> None:
    c = OmegaConf.create(cfg)
    val = c.get(key, default_value=default)
    assert val is default


@mark.parametrize("default", [None, 0, "default"])
@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        (["found"], 0, "found"),
        ([None], 0, None),
        ([DictConfig(content=None)], 0, None),
        ([ListConfig(content=None)], 0, None),
    ],
)
def test_list_get_do_not_return_default(
    cfg: List[Any], key: int, expected: Any, default: Any
) -> None:
    c = OmegaConf.create(cfg)
    val = c.get(key, default_value=default)
    assert val == expected


@mark.parametrize(
    "input_, expected, expected_no_resolve, list_key",
    [
        param([1, 2], [1, 2], [1, 2], None, id="simple"),
        param(["${1}", 2], [2, 2], ["${1}", 2], None, id="interpolation"),
        param(
            [ListConfig(None), ListConfig("${.2}"), [1, 2]],
            [None, ListConfig([1, 2]), ListConfig([1, 2])],
            [None, ListConfig("${.2}"), ListConfig([1, 2])],
            None,
            id="iter_over_lists",
        ),
        param(
            [DictConfig(None), DictConfig("${.2}"), {"a": 10}],
            [None, DictConfig({"a": 10}), DictConfig({"a": 10})],
            [None, DictConfig("${.2}"), DictConfig({"a": 10})],
            None,
            id="iter_over_dicts",
        ),
        param(
            ["???", ListConfig("???"), DictConfig("???")],
            raises(MissingMandatoryValue),
            ["???", ListConfig("???"), DictConfig("???")],
            None,
            id="iter_over_missing",
        ),
        param(
            {
                "defaults": [
                    {"optimizer": "adam"},
                    {"dataset": "imagenet"},
                    {"foo": "${defaults.0.optimizer}_${defaults.1.dataset}"},
                ]
            },
            [
                OmegaConf.create({"optimizer": "adam"}),
                OmegaConf.create({"dataset": "imagenet"}),
                OmegaConf.create({"foo": "adam_imagenet"}),
            ],
            [
                OmegaConf.create({"optimizer": "adam"}),
                OmegaConf.create({"dataset": "imagenet"}),
                OmegaConf.create(
                    {"foo": "${defaults.0.optimizer}_${defaults.1.dataset}"}
                ),
            ],
            "defaults",
            id="str_interpolation",
        ),
    ],
)
def test_iterate_list(
    input_: Any, expected: Any, expected_no_resolve: Any, list_key: str
) -> None:
    c = OmegaConf.create(input_)
    if list_key is not None:
        lst = c.get(list_key)
    else:
        lst = c

    def test_iter(iterator: Any, expected_output: Any) -> None:
        if isinstance(expected_output, list):
            items = [x for x in iterator]
            assert items == expected_output
            for idx in range(len(items)):
                assert type(items[idx]) is type(expected_output[idx])  # noqa
        else:
            with expected_output:
                for _ in iterator:
                    pass

    test_iter(iter(lst), expected)
    test_iter(lst._iter_ex(resolve=False), expected_no_resolve)


def test_iterate_list_with_missing_interpolation() -> None:
    c = OmegaConf.create([1, "${10}"])
    itr = iter(c)
    assert 1 == next(itr)
    with raises(InterpolationKeyError):
        next(itr)


def test_iterate_list_with_missing() -> None:
    c = OmegaConf.create([1, "???"])
    itr = iter(c)
    assert 1 == next(itr)
    with raises(MissingMandatoryValue):
        next(itr)


def test_items_with_interpolation() -> None:
    c = OmegaConf.create(["foo", "${0}"])
    assert c == ["foo", "foo"]


@mark.parametrize(
    ["cfg", "key", "expected_out", "expected_cfg"],
    [
        param([1, 2, 3], 0, 1, [2, 3]),
        param([1, 2, 3], None, 3, [1, 2]),
        param(["???", 2, 3], 0, None, [2, 3]),
        param([1, None, 3], 1, None, [1, 3]),
    ],
)
def test_list_pop(
    cfg: List[Any], key: Optional[int], expected_out: Any, expected_cfg: Any
) -> None:
    c = OmegaConf.create(cfg)
    val = c.pop() if key is None else c.pop(key)
    assert val == expected_out
    assert c == expected_cfg
    validate_list_keys(c)


@mark.parametrize(
    ["cfg", "key", "exc"],
    [
        param([1, 2, 3], 100, IndexError),
        param(["${4}", 2, 3], 0, InterpolationKeyError),
        param(["${1}", "???", 3], 0, InterpolationToMissingValueError),
    ],
)
def test_list_pop_errors(cfg: List[Any], key: int, exc: type) -> None:
    c = OmegaConf.create(cfg)
    with raises(exc):
        c.pop(key)
    assert c == cfg
    validate_list_keys(c)


def test_list_pop_on_unexpected_exception_not_modifying() -> None:
    src = [1, 2, 3, 4]
    c = OmegaConf.create(src)

    with raises(ConfigTypeError):
        c.pop("foo")  # type: ignore
    assert c == src


def test_in_list() -> None:
    c = OmegaConf.create([10, 11, {"a": 12}])
    assert 10 in c
    assert 11 in c
    assert {"a": 12} in c
    assert "blah" not in c


def test_in_with_interpolation() -> None:
    c = OmegaConf.create({"a": ["${b}"], "b": 10})
    assert 10 in c.a


@mark.parametrize(
    ("lst", "expected"),
    [
        param(
            ListConfig(content=None),
            raises(
                TypeError,
                match="Cannot check if an item is in a ListConfig object representing None",
            ),
            id="ListConfig(None)",
        ),
        param(
            ListConfig(content="???"),
            raises(
                MissingMandatoryValue,
                match="Cannot check if an item is in missing ListConfig",
            ),
            id="ListConfig(???)",
        ),
    ],
)
def test_not_in_special_lists(lst: Any, expected: Any) -> None:
    with expected:
        "foo" not in lst


def test_list_config_with_list() -> None:
    c = OmegaConf.create([])
    assert isinstance(c, ListConfig)


def test_list_config_with_tuple() -> None:
    c = OmegaConf.create(())
    assert isinstance(c, ListConfig)


def test_items_on_list() -> None:
    c = OmegaConf.create([1, 2])
    with raises(AttributeError):
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
    with raises(IndexError):
        del c[100]

    validate_list_keys(c)


@mark.parametrize(
    "lst,expected",
    [
        (OmegaConf.create([1, 2]), 2),
        (ListConfig(content=None), 0),
        (ListConfig(content="???"), 0),
        (ListConfig(content="${foo}"), 0),
        (ListConfig(content="${foo}", parent=DictConfig({"foo": [1, 2]})), 0),
    ],
)
def test_list_len(lst: Any, expected: Any) -> None:
    assert len(lst) == expected


def test_nested_list_assign_illegal_value() -> None:
    c = OmegaConf.create({"a": [None]})
    with raises(
        UnsupportedValueType,
        match=re.escape(
            dedent(
                """\
                Value 'IllegalType' is not a supported primitive type
                    full_key: a[0]"""
            )
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


@mark.parametrize(
    "lc,element,err",
    [
        param(
            ListConfig(content=[], element_type=int),
            "foo",
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="append_str_to_list[int]",
        ),
        param(
            ListConfig(content=[], element_type=Color),
            "foo",
            "Invalid value 'foo', expected one of [RED, GREEN, BLUE]",
            id="append_str_to_list[Color]",
        ),
        param(
            ListConfig(content=[], element_type=User),
            "foo",
            "Invalid type assigned: str is not a subclass of User. value: foo",
            id="append_str_to_list[User]",
        ),
        param(
            ListConfig(content=[], element_type=User),
            {"name": "Bond", "age": 7},
            "Invalid type assigned: dict is not a subclass of User. value: {'name': 'Bond', 'age': 7}",
            id="list:convert_dict_to_user",
        ),
        param(
            ListConfig(content=[], element_type=User),
            {},
            "Invalid type assigned: dict is not a subclass of User. value: {}",
            id="list:convert_empty_dict_to_user",
        ),
        param(
            ListConfig(content=[], element_type=List[int]),
            123,
            "Invalid value assigned: int is not a ListConfig, list or tuple.",
        ),
        param(
            ListConfig(content=[], element_type=List[int]),
            None,
            "Invalid type assigned: NoneType is not a subclass of List[int]",
        ),
    ],
)
def test_append_invalid_element_type(lc: ListConfig, element: Any, err: Any) -> None:
    with raises(ValidationError, match=re.escape(err)):
        lc.append(element)


@mark.parametrize(
    "lc,element,expected",
    [
        param(
            ListConfig(content=[], element_type=int),
            "10",
            10,
            id="list:convert_str_to_int",
        ),
        param(
            ListConfig(content=[], element_type=float),
            "10",
            10.0,
            id="list:convert_str_to_float",
        ),
        param(
            ListConfig(content=[], element_type=str),
            10,
            "10",
            id="list:convert_int_to_str",
        ),
        param(
            ListConfig(content=[], element_type=bool),
            "yes",
            True,
            id="list:convert_str_to_bool",
        ),
        param(
            ListConfig(content=[], element_type=Color),
            "RED",
            Color.RED,
            id="list:convert_str_to_enum",
        ),
        param(
            ListConfig(content=[], element_type=Path),
            "hello.txt",
            Path("hello.txt"),
            id="list:convert_str_to_path",
        ),
    ],
)
def test_append_convert(lc: ListConfig, element: Any, expected: Any) -> None:
    lc.append(element)
    value = lc[-1]
    assert value == expected
    assert type(value) == type(expected)


@mark.parametrize(
    "index, expected", [(slice(1, 3), [11, 12]), (slice(0, 3, 2), [10, 12]), (-1, 13)]
)
def test_list_index(index: Any, expected: Any) -> None:
    c = OmegaConf.create([10, 11, 12, 13])
    assert c[index] == expected


@mark.parametrize(
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


@mark.parametrize(
    "cfg, value, expected, expected_ref_type",
    [
        param(
            ListConfig(element_type=int, content=[]),
            123,
            [123],
            int,
            id="typed_list",
        ),
        param(
            ListConfig(element_type=int, content=[]),
            None,
            ValidationError,
            None,
            id="typed_list_append_none",
        ),
        param(
            ListConfig(element_type=Optional[int], content=[]),
            123,
            [123],
            int,
            id="optional_typed_list",
        ),
        param(
            ListConfig(element_type=Optional[int], content=[]),
            None,
            [None],
            int,
            id="optional_typed_list_append_none",
        ),
        param(
            ListConfig(element_type=User, content=[]),
            User(name="bond"),
            [User(name="bond")],
            User,
            id="user_list",
        ),
        param(
            ListConfig(element_type=User, content=[]),
            None,
            ValidationError,
            None,
            id="user_list_append_none",
        ),
        param(
            ListConfig(element_type=Optional[User], content=[]),
            User(name="bond"),
            [User(name="bond")],
            User,
            id="optional_user_list",
        ),
        param(
            ListConfig(element_type=Optional[User], content=[]),
            None,
            [None],
            User,
            id="optional_user_list_append_none",
        ),
    ],
)
def test_append_to_typed(
    cfg: ListConfig,
    value: Any,
    expected: Any,
    expected_ref_type: type,
) -> None:
    cfg = _ensure_container(cfg)
    if isinstance(expected, type):
        with raises(expected):
            cfg.append(value)
    else:
        cfg.append(value)
        assert cfg == expected
        node = cfg._get_node(-1)
        assert isinstance(node, Node)
        assert node._metadata.ref_type == expected_ref_type
        validate_list_keys(cfg)


@mark.parametrize(
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
        param(
            ListConfig(element_type=int, content=[]),
            0,
            123,
            [123],
            IntegerNode,
            None,
            id="typed_list",
        ),
        param(
            ListConfig(element_type=int, content=[]),
            0,
            None,
            None,
            None,
            ValidationError,
            id="typed_list_insert_none",
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
        with raises(expectation):
            c.insert(index, value)
    validate_list_keys(c)


@mark.parametrize(
    "lst,idx,value,expectation",
    [
        (ListConfig(content=None), 0, 10, raises(TypeError)),
        (ListConfig(content="???"), 0, 10, raises(MissingMandatoryValue)),
    ],
)
def test_insert_special_list(lst: Any, idx: Any, value: Any, expectation: Any) -> None:
    with expectation:
        lst.insert(idx, value)


@mark.parametrize(
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


@mark.parametrize(
    "src, remove, result, expectation",
    [
        ([10], 10, [], nullcontext()),
        ([], "oops", None, raises(ValueError)),
        ([0, dict(a="blah"), 10], dict(a="blah"), [0, 10], nullcontext()),
        ([1, 2, 1, 2], 2, [1, 1, 2], nullcontext()),
    ],
)
def test_remove(src: List[Any], remove: Any, result: Any, expectation: Any) -> None:
    with expectation:
        lst = OmegaConf.create(src)
        assert isinstance(lst, ListConfig)
        lst.remove(remove)
        assert lst == result


@mark.parametrize("src", [[], [1, 2, 3], [None, dict(foo="bar")]])
@mark.parametrize("num_clears", [1, 2])
def test_clear(src: List[Any], num_clears: int) -> None:
    lst = OmegaConf.create(src)
    for i in range(num_clears):
        lst.clear()
    assert lst == []


@mark.parametrize(
    "src, item, expected_index, expectation",
    [
        ([], 20, -1, raises(ValueError)),
        ([10, 20], 10, 0, nullcontext()),
        ([10, 20], 20, 1, nullcontext()),
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
    with raises(ValueError):
        lst.index(x=30, start=3)

    with raises(ValueError):
        lst.index(x=30, end=2)


@mark.parametrize(
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
    iv = IllegalType()
    with raises(ValueError):
        c.insert(0, iv)
    assert len(c) == 0
    assert c == []

    with flag_override(c, "allow_objects", True):
        c.insert(0, iv)
    assert c == [iv]


def test_append_throws_not_changing_list() -> None:
    c = OmegaConf.create([])
    iv = IllegalType()
    with raises(ValueError):
        c.append(iv)
    assert len(c) == 0
    assert c == []
    validate_list_keys(c)

    with flag_override(c, "allow_objects", True):
        c.append(iv)
    assert c == [iv]


def test_hash() -> None:
    c1 = OmegaConf.create([10])
    c2 = OmegaConf.create([10])
    assert hash(c1) == hash(c2)
    c2[0] = 20
    assert hash(c1) != hash(c2)


@mark.parametrize(
    "in_list1, in_list2,in_expected",
    [
        ([], [], []),
        ([1, 2], [3, 4], [1, 2, 3, 4]),
        (["x", 2, "${0}"], [5, 6, 7], ["x", 2, "x", 5, 6, 7]),
    ],
)
class TestListAdd:
    @mark.parametrize(
        "left_listconfig, right_listconfig",
        [
            param(True, True, id="listconfig_plus_listconfig"),
            param(True, False, id="listconfig_plus_list"),
            param(False, True, id="list_plus_listconfig"),
        ],
    )
    def test_list_plus(
        self,
        in_list1: List[Any],
        in_list2: List[Any],
        in_expected: List[Any],
        left_listconfig: bool,
        right_listconfig: bool,
    ) -> None:
        list1: Union[List[Any], ListConfig] = (
            OmegaConf.create(in_list1) if left_listconfig else in_list1
        )
        list2: Union[List[Any], ListConfig] = (
            OmegaConf.create(in_list2) if right_listconfig else in_list2
        )
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


def test_deep_radd() -> None:
    cfg = OmegaConf.create({"foo": [1, 2, "${bar}"], "bar": "xx"})
    lst = [10, 20] + cfg.foo
    assert lst == [10, 20, 1, 2, "xx"]


def test_set_with_invalid_key() -> None:
    cfg = OmegaConf.create([1, 2, 3])
    with raises(KeyValidationError):
        cfg["foo"] = 4  # type: ignore


@mark.parametrize(
    "lst,idx,expected",
    [
        (OmegaConf.create([1, 2]), 0, 1),
        (ListConfig(content=None), 0, TypeError),
        (ListConfig(content="???"), 0, MissingMandatoryValue),
    ],
)
def test_getitem(lst: Any, idx: Any, expected: Any) -> None:
    if isinstance(expected, type):
        with raises(expected):
            lst.__getitem__(idx)
    else:
        assert lst.__getitem__(idx) == expected


@mark.parametrize(
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


@mark.parametrize(
    "constructor",
    [OmegaConf.create, list, lambda lst: OmegaConf.create({"foo": lst}).foo],
)
@mark.parametrize(
    "lst, idx, value, expected",
    [
        param(
            ["a", "b", "c", "d"],
            slice(1, 3),
            ["x", "y"],
            ["a", "x", "y", "d"],
            id="same-number-of-elements",
        ),
        param(
            ["a", "x", "y", "d"],
            slice(1, 3),
            ["x", "y", "z"],
            ["a", "x", "y", "z", "d"],
            id="extra-elements",
        ),
        param(
            ["a", "x", "y", "z", "d"],
            slice(1, 1),
            ["b"],
            ["a", "b", "x", "y", "z", "d"],
            id="insert only",
        ),
        param(
            ["a", "b", "x", "y", "z", "d"],
            slice(1, 1),
            [],
            ["a", "b", "x", "y", "z", "d"],
            id="nop",
        ),
        param(
            ["a", "b", "x", "y", "z", "d"],
            slice(1, 3),
            [],
            ["a", "y", "z", "d"],
            id="less-elements",
        ),
        param(
            ["a", "y", "z", "d"],
            slice(1, 2, 1),
            ["b"],
            ["a", "b", "z", "d"],
            id="extended-slice",
        ),
        param(
            ["a", "b", "c", "d"],
            slice(1, 3, 1),
            ["x", "y"],
            ["a", "x", "y", "d"],
            id="extended-slice2",
        ),
        param(
            ["a", "b", "z", "d"],
            slice(0, 3, 2),
            ["a", "c"],
            ["a", "b", "c", "d"],
            id="extended-slice-disjoint",
        ),
        param(
            ["a", "b", "c", "d"],
            slice(1, 3),
            1,
            raises(TypeError),
            id="non-iterable-input",
        ),
        param(
            ["a", "b", "c", "d"],
            slice(1, 3),
            [object()],
            raises(UnsupportedValueType),
            id="partially-valid-input",
        ),
        param(
            ["a", "b", "c", "d"],
            slice(1, 3, 1),
            ["x", "y", "z"],
            ["a", "x", "y", "z", "d"],
            id="extended-slice-length-mismatch",
        ),
        param(
            ["a", "b", "c", "d", "e", "f"],
            slice(1, 5, 2),
            ["x", "y", "z"],
            raises(ValueError),
            id="extended-slice-length-mismatch2",
        ),
        param(
            ["a", "b", "c", "d", "e", "f"],
            slice(-1, -3, -1),
            ["F", "E"],
            ["a", "b", "c", "d", "E", "F"],
            id="extended-slice-reverse",
        ),
        param(
            ["a", "b", "c", "d", "e", "g"],
            slice(-1, -3, None),
            ["f"],
            ["a", "b", "c", "d", "e", "f", "g"],
            id="slice-reverse-insert",
        ),
        param(
            ["a", "b", "c", "r", "r", "e"],
            slice(-3, -1, None),
            ["d"],
            ["a", "b", "c", "d", "e"],
            id="slice-reverse-replace",
        ),
        param(
            ["c", "d"],
            slice(-10, -10, None),
            ["a", "b"],
            ["a", "b", "c", "d"],
            id="slice-reverse-insert-underflow",
        ),
        param(
            ["a", "b"],
            slice(10, 10, None),
            ["c", "d"],
            ["a", "b", "c", "d"],
            id="slice-reverse-insert-overflow",
        ),
    ],
)
def test_setitem_slice(
    lst: List[Any],
    idx: slice,
    value: Union[List[Any], Any],
    expected: Union[List[Any], RaisesContext[Any]],
    constructor: Callable[[List[Any]], MutableSequence[Any]],
) -> None:
    cfg = constructor(lst)
    if isinstance(expected, list):
        cfg[idx] = value
        assert cfg == expected
    else:
        expected_exception: Any = expected.expected_exception
        if type(constructor) == type(list) and issubclass(
            expected_exception, UnsupportedValueType
        ):
            return  # standard list() can accept object() so skip
        orig_cfg = cfg[:]
        with expected:
            cfg[idx] = value
        assert cfg == orig_cfg


@mark.parametrize(
    "lst,idx,expected",
    [
        (OmegaConf.create([1, 2]), 0, 1),
        (OmegaConf.create([1, 2]), "foo", KeyValidationError),
        (OmegaConf.create([1, "${2}"]), 1, InterpolationKeyError),
        (OmegaConf.create(["???", "${0}"]), 1, InterpolationToMissingValueError),
        (ListConfig(content=None), 0, TypeError),
        (ListConfig(content="???"), 0, MissingMandatoryValue),
    ],
)
def test_get(lst: Any, idx: Any, expected: Any) -> None:
    if isinstance(expected, type):
        with raises(expected):
            lst.get(idx)
    else:
        assert lst.__getitem__(idx) == expected


def test_getattr() -> None:
    src = ["a", "b", "c"]
    cfg = OmegaConf.create(src)
    with raises(AttributeError):
        getattr(cfg, "foo")
    assert getattr(cfg, "0") == src[0]
    assert getattr(cfg, "1") == src[1]
    assert getattr(cfg, "2") == src[2]


def test_shallow_copy() -> None:
    cfg = OmegaConf.create([1, 2])
    c = cfg.copy()
    assert cfg == c
    cfg[0] = 42
    assert cfg[0] == 42
    assert c[0] == 1


def test_shallow_copy_missing() -> None:
    cfg = ListConfig(content=MISSING)
    c = cfg.copy()
    c._set_value([1])
    assert c[0] == 1
    assert cfg._is_missing()


def test_shallow_copy_none() -> None:
    cfg = ListConfig(content=None)
    c = cfg.copy()
    c._set_value([1])
    assert c[0] == 1
    assert cfg._is_none()


@mark.parametrize("flag", ["struct", "readonly"])
def test_listconfig_creation_with_parent_flag(flag: str) -> None:
    parent = OmegaConf.create([])
    parent._set_flag(flag, True)
    d = [1, 2, 3]
    cfg = ListConfig(d, parent=parent)
    assert cfg == d


@mark.parametrize(
    "node",
    [
        param(AnyNode("hello"), id="any"),
        param(DictConfig({}), id="dict"),
        param(ListConfig([]), id="list"),
    ],
)
def test_node_copy_on_append(node: Any) -> None:
    cfg = OmegaConf.create([])
    cfg.append(node)
    assert cfg.__dict__["_content"][0] is not node


@mark.parametrize(
    "cfg,key,value,error",
    [
        param(
            ListConfig([], element_type=Optional[User]),
            0,
            "foo",
            True,
            id="structured:set_optional_to_bad_type",
        ),
        param(
            ListConfig([], element_type=int),
            0,
            None,
            True,
            id="set_to_none_raises",
        ),
        param(
            ListConfig([], element_type=Optional[int]),
            0,
            None,
            False,
            id="optional_set_to_none",
        ),
    ],
)
def test_validate_set(cfg: ListConfig, key: int, value: Any, error: bool) -> None:
    if error:
        with raises(ValidationError):
            cfg._validate_set(key, value)
    else:
        cfg._validate_set(key, value)
