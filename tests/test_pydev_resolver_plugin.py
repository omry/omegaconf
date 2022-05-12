import builtins
from typing import Any

from pytest import fixture, mark, param

from omegaconf import (
    AnyNode,
    BooleanNode,
    BytesNode,
    Container,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    Node,
    OmegaConf,
    PathNode,
    StringNode,
    ValueNode,
)
from omegaconf._utils import type_str
from pydevd_plugins.extensions.pydevd_plugin_omegaconf import (
    OmegaConfDeveloperResolver,
    OmegaConfUserResolver,
)
from tests import Color


@fixture
def resolver() -> Any:
    yield OmegaConfUserResolver()


@mark.parametrize(
    ("obj", "expected"),
    [
        # nodes
        param(AnyNode(10), {}, id="any:10"),
        param(StringNode("foo"), {}, id="str:foo"),
        param(IntegerNode(10), {}, id="int:10"),
        param(FloatNode(3.14), {}, id="float:3.14"),
        param(BooleanNode(True), {}, id="bool:True"),
        param(BytesNode(b"binary"), {}, id="bytes:binary"),
        param(PathNode("hello.txt"), {}, id="path:hello.txt"),
        param(EnumNode(enum_type=Color, value=Color.RED), {}, id="Color:Color.RED"),
        # nodes are never returning a dictionary
        param(AnyNode("${foo}", parent=DictConfig({"foo": 10})), {}, id="any:inter_10"),
        # DictConfig
        param(DictConfig({"a": 10}), {"a": AnyNode(10)}, id="dict"),
        param(
            DictConfig({"a": 10, "b": "${a}"}),
            {"a": AnyNode(10), "b": AnyNode("${a}")},
            id="dict:interpolation_value",
        ),
        param(
            DictConfig({"a": 10, "b": "${zzz}"}),
            {"a": AnyNode(10), "b": AnyNode("${zzz}")},
            id="dict:interpolation_value_error",
        ),
        param(
            DictConfig({"a": 10, "b": "foo_${a}"}),
            {"a": AnyNode(10), "b": AnyNode("foo_${a}")},
            id="dict:str_interpolation_value",
        ),
        param(DictConfig("${zzz}"), {}, id="dict:inter_error"),
        # ListConfig
        param(
            ListConfig(["a", "b"]), {"0": AnyNode("a"), "1": AnyNode("b")}, id="list"
        ),
        param(
            ListConfig(["${1}", 10]),
            {"0": AnyNode("${1}"), "1": AnyNode(10)},
            id="list:interpolation_value",
        ),
        param(ListConfig("${zzz}"), {}, id="list:inter_error"),
    ],
)
def test_get_dictionary_node(resolver: Any, obj: Any, expected: Any) -> None:
    res = resolver.get_dictionary(obj)
    assert res == expected


@mark.parametrize(
    ("obj", "attribute", "expected"),
    [
        # dictconfig
        param(DictConfig({"a": 10}), "a", AnyNode(10), id="dict"),
        param(
            DictConfig({"a": DictConfig(None)}),
            "a",
            DictConfig(None),
            id="dict:none",
        ),
        # listconfig
        param(ListConfig([10]), 0, AnyNode(10), id="list"),
        param(ListConfig(["???"]), 0, AnyNode("???"), id="list:missing_item"),
    ],
)
def test_resolve(
    resolver: Any,
    obj: Any,
    attribute: str,
    expected: Any,
) -> None:
    res = resolver.resolve(obj, attribute)
    assert res == expected
    assert type(res) is type(expected)


@mark.parametrize(
    ("obj", "attribute", "expected"),
    [
        param(
            OmegaConf.create({"a": 10, "inter": "${a}"}), "inter", {}, id="dict:inter"
        ),
        param(
            OmegaConf.create({"missing": "???"}),
            "missing",
            {},
            id="dict:missing_value",
        ),
        param(
            OmegaConf.create({"none": None}),
            "none",
            {},
            id="dict:none_value",
        ),
        param(
            OmegaConf.create({"none": DictConfig(None)}),
            "none",
            {},
            id="dict:none_dictconfig_value",
        ),
        param(
            OmegaConf.create({"missing": DictConfig("???")}),
            "missing",
            {},
            id="dict:missing_dictconfig_value",
        ),
        param(
            OmegaConf.create({"a": {"b": 10}, "b": DictConfig("${a}")}),
            "b",
            {"b": 10},
            id="dict:interpolation_dictconfig_value",
        ),
    ],
)
def test_get_dictionary_dictconfig(
    resolver: Any,
    obj: Any,
    attribute: str,
    expected: Any,
) -> None:
    field = resolver.resolve(obj, attribute)
    res = resolver.get_dictionary(field)
    assert res == expected
    assert type(res) is type(expected)


@mark.parametrize(
    ("obj", "attribute", "expected"),
    [
        param(
            ListConfig("${list}", parent=DictConfig({"list": [{"a": 10}]})),
            "0",
            {"a": 10},
            id="inter_list:dict_element",
        ),
        param(
            DictConfig("${dict}", parent=DictConfig({"dict": {"a": {"b": 10}}})),
            "a",
            {"b": 10},
            id="inter_dict:dict_element",
        ),
    ],
)
def test_resolve_through_container_interpolation(
    resolver: Any, obj: Any, attribute: str, expected: Any
) -> None:
    res = resolver.resolve(obj, attribute)
    assert res == expected


@mark.parametrize(
    ("obj", "attribute", "expected"),
    [
        param(OmegaConf.create(["${.1}", 10]), "0", {}, id="list:inter_value"),
        param(
            OmegaConf.create({"a": ListConfig(None)}),
            "a",
            {},
            id="list:none_listconfig_value",
        ),
        param(
            OmegaConf.create({"a": ListConfig("???")}),
            "a",
            {},
            id="list:missing_listconfig_value",
        ),
        param(
            OmegaConf.create({"a": [1, 2], "b": ListConfig("${a}")}),
            "b",
            {"0": 1, "1": 2},
            id="list:interpolation_listconfig_value",
        ),
    ],
)
def test_get_dictionary_listconfig(
    resolver: Any,
    obj: Any,
    attribute: str,
    expected: Any,
) -> None:
    field = resolver.resolve(obj, attribute)
    res = resolver.get_dictionary(field)
    assert res == expected
    assert type(res) is type(expected)


@mark.parametrize("resolver", [OmegaConfUserResolver(), OmegaConfDeveloperResolver()])
@mark.parametrize(
    ("type_", "expected"),
    [
        # containers
        (Container, True),
        (DictConfig, True),
        (ListConfig, True),
        # nodes
        (Node, True),
        (ValueNode, True),
        (AnyNode, True),
        (IntegerNode, True),
        (FloatNode, True),
        (StringNode, True),
        (BooleanNode, True),
        (BytesNode, True),
        (PathNode, True),
        (EnumNode, True),
        # not covering some other things.
        (builtins.int, False),
        (dict, False),
        (list, False),
    ],
)
def test_can_provide(resolver: Any, type_: Any, expected: bool) -> None:
    assert resolver.can_provide(type_, type_str(type_)) == expected


@mark.parametrize(
    ("obj", "expected"),
    [
        (AnyNode(10), "10"),
        (AnyNode("???"), "??? <MISSING>"),
        (
            AnyNode("${foo}", parent=OmegaConf.create({})),
            "${foo} -> ERR: Interpolation key 'foo' not found",
        ),
        (AnyNode("${foo}", parent=OmegaConf.create({"foo": 10})), "${foo} -> 10"),
        (
            DictConfig("${foo}", parent=OmegaConf.create({"foo": {"a": 10}})),
            "${foo} -> {'a': 10}",
        ),
        (
            ListConfig("${foo}", parent=OmegaConf.create({"foo": [1, 2]})),
            "${foo} -> [1, 2]",
        ),
    ],
)
def test_get_str(resolver: Any, obj: Any, expected: str) -> None:
    assert resolver.get_str(obj) == expected


def test_dev_resolver() -> None:
    resolver = OmegaConfDeveloperResolver()
    cfg = OmegaConf.create({"foo": 10})
    assert resolver.resolve(cfg, "_metadata") is cfg.__dict__["_metadata"]
    assert resolver.get_dictionary(cfg) is cfg.__dict__
