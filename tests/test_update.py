import re
import sys
from typing import Any, Dict, List, Union

import pytest
from pytest import raises

from omegaconf import DictConfig, ListConfig, MissingMandatoryValue, OmegaConf


def test_update_map_value() -> None:
    # Replacing an existing key in a map
    s = "hello: world"
    c = OmegaConf.create(s)
    OmegaConf.update(c, "hello", "there")
    assert {"hello": "there"} == c


def test_update_map_new_keyvalue() -> None:
    # Adding another key to a map
    s = "hello: world"
    c = OmegaConf.create(s)
    OmegaConf.update(c, "who", "goes there")
    assert {"hello": "world", "who": "goes there"} == c


def test_update_map_to_value() -> None:
    # changing map to single node
    s = "hello: world"
    c = OmegaConf.create(s)
    OmegaConf.update(c, "value")
    assert {"hello": "world", "value": None} == c


def test_update_with_empty_map_value() -> None:
    c = OmegaConf.create()
    OmegaConf.update(c, "a", {})
    assert {"a": {}} == c


def test_update_with_map_value() -> None:
    c = OmegaConf.create()
    OmegaConf.update(c, "a", {"aa": 1, "bb": 2})
    assert {"a": {"aa": 1, "bb": 2}} == c


def test_update_deep_from_empty() -> None:
    c = OmegaConf.create()
    OmegaConf.update(c, "a.b", 1)
    assert {"a": {"b": 1}} == c


def test_update_deep_with_map() -> None:
    c = OmegaConf.create("a: b")
    OmegaConf.update(c, "a.b", {"c": 1})
    assert {"a": {"b": {"c": 1}}} == c


def test_update_deep_with_value() -> None:
    c = OmegaConf.create()
    OmegaConf.update(c, "a.b", 1)
    assert {"a": {"b": 1}} == c


def test_update_deep_with_map2() -> None:
    c = OmegaConf.create("a: 1")
    OmegaConf.update(c, "b.c", 2)
    assert {"a": 1, "b": {"c": 2}} == c


def test_update_deep_with_map_update() -> None:
    c = OmegaConf.create("a: {b : {c: 1}}")
    OmegaConf.update(c, "a.b.d", 2)
    assert {"a": {"b": {"c": 1, "d": 2}}} == c


def test_list_value_update() -> None:
    # List update is always a replace because a list can be merged in too many ways
    c = OmegaConf.create("a: [1,2]")
    OmegaConf.update(c, "a", [2, 3, 4])
    assert {"a": [2, 3, 4]} == c


def test_override_mandatory_value() -> None:
    c = OmegaConf.create('{a: "???"}')
    assert isinstance(c, DictConfig)
    with raises(MissingMandatoryValue):
        c.get("a")
    OmegaConf.update(c, "a", 123)
    assert {"a": 123} == c


def test_update_empty_to_value() -> None:
    """"""
    s = ""
    c = OmegaConf.create(s)
    OmegaConf.update(c, "hello")
    assert {"hello": None} == c


def test_update_same_value() -> None:
    """"""
    s = "hello"
    c = OmegaConf.create(s)
    OmegaConf.update(c, "hello")
    assert {"hello": None} == c


def test_update_value_to_map() -> None:
    s = "hello"
    c = OmegaConf.create(s)
    OmegaConf.update(c, "hi", "there")
    assert {"hello": None, "hi": "there"} == c


def test_update_map_empty_to_map() -> None:
    s = ""
    c = OmegaConf.create(s)
    OmegaConf.update(c, "hello", "there")
    assert {"hello": "there"} == c


def test_update_list() -> None:
    c = OmegaConf.create([1, 2, 3])
    assert isinstance(c, ListConfig)
    OmegaConf.update(c, "1", "abc")
    OmegaConf.update(c, "-1", "last")
    with raises(IndexError):
        OmegaConf.update(c, "4", "abc")

    assert len(c) == 3
    assert c[0] == 1
    assert c[1] == "abc"
    assert c[2] == "last"


def test_update_nested_list() -> None:
    c = OmegaConf.create(dict(deep=dict(list=[1, 2, 3])))
    OmegaConf.update(c, "deep.list.1", "abc")
    OmegaConf.update(c, "deep.list.-1", "last")
    with raises(IndexError):
        OmegaConf.update(c, "deep.list.4", "abc")

    assert c.deep.list[0] == 1
    assert c.deep.list[1] == "abc"
    assert c.deep.list[2] == "last"


def test_update_list_make_dict() -> None:
    c = OmegaConf.create([None, None])
    assert isinstance(c, ListConfig)
    OmegaConf.update(c, "0.a.a", "aa")
    OmegaConf.update(c, "0.a.b", "ab")
    OmegaConf.update(c, "1.b.a", "ba")
    OmegaConf.update(c, "1.b.b", "bb")
    assert c[0].a.a == "aa"
    assert c[0].a.b == "ab"
    assert c[1].b.a == "ba"
    assert c[1].b.b == "bb"


@pytest.mark.parametrize(  # type:ignore
    "cfg,overrides,expected",
    [
        ([1, 2, 3], ["0=bar", "2.a=100"], ["bar", 2, dict(a=100)]),
        ({}, ["foo=bar", "bar=100"], {"foo": "bar", "bar": 100}),
        ({}, ["foo=bar=10"], {"foo": "bar=10"}),
    ],
)
def test_merge_with_dotlist(
    cfg: Union[List[Any], Dict[str, Any]],
    overrides: List[str],
    expected: Union[List[Any], Dict[str, Any]],
) -> None:
    c = OmegaConf.create(cfg)
    c.merge_with_dotlist(overrides)
    assert c == expected


def test_merge_with_cli() -> None:
    c = OmegaConf.create([1, 2, 3])
    sys.argv = ["app.py", "0=bar", "2.a=100"]
    c.merge_with_cli()
    assert c == ["bar", 2, dict(a=100)]


@pytest.mark.parametrize(  # type:ignore
    "dotlist, expected",
    [([], {}), (["foo=1"], {"foo": 1}), (["foo=1", "bar"], {"foo": 1, "bar": None})],
)
def test_merge_empty_with_dotlist(dotlist: List[str], expected: Dict[str, Any]) -> None:
    c = OmegaConf.create()
    c.merge_with_dotlist(dotlist)
    assert c == expected


@pytest.mark.parametrize("dotlist", ["foo=10", ["foo=1", 10]])  # type:ignore
def test_merge_with_dotlist_errors(dotlist: List[str]) -> None:
    c = OmegaConf.create()
    with pytest.raises(ValueError):
        c.merge_with_dotlist(dotlist)


def test_update_node_deprecated() -> None:
    c = OmegaConf.create()
    with pytest.warns(
        expected_warning=UserWarning,
        match=re.escape(
            "update_node() is deprecated, use OmegaConf.update(). (Since 2.0)"
        ),
    ):
        c.update_node("foo", "bar")
    assert c.foo == "bar"
