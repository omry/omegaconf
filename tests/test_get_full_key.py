from typing import Any, Union

from pytest import mark, param

from omegaconf import DictConfig, IntegerNode, OmegaConf, UnionNode
from tests import Color


@mark.parametrize(
    "cfg, select, key, expected",
    [
        ({}, "", "a", "a"),
        # 1
        # dict
        ({"a": 1}, "", "a", "a"),
        ({"a": 1}, "", "bad", "bad"),
        # dict empty key
        ({"a": 1}, "", "", ""),
        ({"a": 1}, "", "bad", "bad"),
        # list
        ([1, 2, 3], "", "2", "[2]"),
        ([1, 2, 3], "", "999", "[999]"),
        # list empty key
        ([1, 2, 3], "", "", ""),
        ([1, 2, 3], "", "999", "[999]"),
        # 2
        # dd
        ({"a": 1, "b": {"c": 1}}, "b", "c", "b.c"),
        ({"a": 1, "b": {"c": 1}}, "b", "bad", "b.bad"),
        # dl
        ({"a": [1, 2, 3]}, "a", 1, "a[1]"),
        ({"a": [1, 2, 3]}, "a", 999, "a[999]"),
        # ll
        ([[1, 2, 3]], "0", "2", "[0][2]"),
        ([[1, 2, 3]], "0", "999", "[0][999]"),
        # ld
        ([1, 2, {"a": 1}], "2", "a", "[2].a"),
        ([1, 2, {"a": 1}], "2", "bad", "[2].bad"),
        # dd empty key
        ({"a": 1, "b": {"c": 1}}, "b", "", "b"),
        ({"a": 1, "b": {"c": 1}}, "b", "bad", "b.bad"),
        # 3
        # ddd
        ({"a": {"b": {"c": 1}}}, "a.b", "c", "a.b.c"),
        ({"a": {"b": {"c": 1}}}, "a.b", "bad", "a.b.bad"),
        # ddl
        ({"a": {"b": [0, 1]}}, "a.b", 0, "a.b[0]"),
        ({"a": {"b": [0, 1]}}, "a.b", 999, "a.b[999]"),
        # dll
        ({"a": [1, [2]]}, "a.1", 0, "a[1][0]"),
        ({"a": [1, [2]]}, "a.1", 999, "a[1][999]"),
        # dld
        ({"a": [{"b": 2}]}, "a.0", "b", "a[0].b"),
        ({"a": [{"b": 2}]}, "a.0", "bad", "a[0].bad"),
        # ldd
        ([{"a": {"b": 1}}], "0.a", "b", "[0].a.b"),
        ([{"a": {"b": 1}}], "0.a", "bad", "[0].a.bad"),
        # ldl
        ([{"a": [0]}], "0.a", 0, "[0].a[0]"),
        ([{"a": [0]}], "0.a", 999, "[0].a[999]"),
        # lld
        ([[{"a": 1}]], "0.0", "a", "[0][0].a"),
        ([[{"a": 1}]], "0.0", "bad", "[0][0].bad"),
        # lll
        ([[[0]]], "0.0", 0, "[0][0][0]"),
        # lldddl
        ([[{"a": {"a": [0]}}]], "0.0.a.a", 0, "[0][0].a.a[0]"),
        # special cases
        # parent_with_missing_item
        ({"x": "???", "a": 1, "b": {"c": 1}}, "b", "c", "b.c"),
        ({"foo": IntegerNode(value=10)}, "", "foo", "foo"),
        ({"foo": {"bar": IntegerNode(value=10)}}, "foo", "bar", "foo.bar"),
        # enum
        param(
            DictConfig(key_type=Color, element_type=str, content={Color.RED: "red"}),
            "RED",
            "",
            "RED",
            id="get_full_key_with_enum_key",
        ),
        param(
            {
                "foo": DictConfig(
                    key_type=Color, element_type=str, content={Color.RED: "red"}
                )
            },
            "foo",
            "RED",
            "foo.RED",
            id="get_full_key_with_nested_enum_key",
        ),
        # slice
        ([1, 2, 3], "", slice(0, 1), "[0:1]"),
        ([1, 2, 3], "", slice(0, 1, 2), "[0:1:2]"),
        # union
        ({"foo": UnionNode(123, Union[int, str])}, "", "foo", "foo"),
        ([UnionNode(123, Union[int, str])], "", "0", "[0]"),
        ({"foo": {"bar": UnionNode(123, Union[int, str])}}, "foo", "bar", "foo.bar"),
        ({"foo": {"bar": UnionNode(123, Union[int, str])}}, "foo.bar", None, "foo.bar"),
    ],
)
def test_get_full_key_from_config(
    cfg: Any, select: str, key: Any, expected: Any
) -> None:
    c = OmegaConf.create(cfg)
    _root, _last_key, node = c._select_impl(
        select,
        throw_on_missing=True,
        throw_on_resolution_failure=True,
    )
    assert node is not None
    assert node._get_full_key(key) == expected


def test_value_node_get_full_key() -> None:
    cfg = OmegaConf.create({"foo": IntegerNode(value=10)})
    assert cfg._get_node("foo")._get_full_key(None) == "foo"  # type: ignore

    node = IntegerNode(value=10)
    assert node._get_full_key(None) == ""
    node = IntegerNode(key="foo", value=10)
    assert node._get_full_key(None) == "foo"


def test_union_node_get_full_key() -> None:
    cfg = OmegaConf.create({"foo": UnionNode(10, Union[int, str])})
    assert cfg._get_node("foo")._get_full_key(None) == "foo"  # type: ignore

    node = UnionNode(10, Union[int, str])
    assert node._get_full_key(None) == ""
    node = UnionNode(10, Union[int, str], key="foo")
    assert node._get_full_key(None) == "foo"
