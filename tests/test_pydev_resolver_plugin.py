import builtins
from typing import Any

from pytest import fixture, mark, param

from omegaconf import (
    AnyNode,
    BooleanNode,
    Container,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    Node,
    OmegaConf,
    StringNode,
    ValueNode,
)
from omegaconf._utils import type_str
from pydevd_plugins.extensions.pydevd_plugin_omegaconf import (
    OmegaConfNodeResolver,
    Wrapper,
)
from tests import Color


@fixture
def resolver() -> Any:
    yield OmegaConfNodeResolver()


@mark.parametrize(
    ("obj", "expected"),
    [
        # nodes
        param(AnyNode(10), {"_val": 10}, id="any:10"),
        param(StringNode("foo"), {"_val": "foo"}, id="str:foo"),
        param(IntegerNode(10), {"_val": 10}, id="int:10"),
        param(FloatNode(3.14), {"_val": 3.14}, id="float:3.14"),
        param(BooleanNode(True), {"_val": True}, id="bool:True"),
        param(
            EnumNode(enum_type=Color, value=Color.RED),
            {"_val": Color.RED},
            id="Color:Color.RED",
        ),
        param(AnyNode("${foo}"), {"interpolation": "${foo}", "->": None}, id="any:10"),
        param(
            AnyNode("${foo}", parent=OmegaConf.create({"foo": 10})),
            {"interpolation": "${foo}", "->": AnyNode(10)},
            id="any:10",
        ),
        # DictConfig
        param(DictConfig({"a": 10}), {"a": AnyNode(10)}, id="dict"),
        param(
            DictConfig({"a": 10, "b": "${a}"}),
            {"a": AnyNode(10), "b": AnyNode(10)},
            id="dict:interpolation_value",
        ),
        param(
            DictConfig({"a": 10, "b": "${zzz}"}),
            {"a": AnyNode(10), "b": AnyNode("${zzz}")},
            id="dict:interpolation_value_error",
        ),
        param(
            DictConfig({"a": 10, "b": "foo_${a}"}),
            {"a": AnyNode(10), "b": AnyNode("foo_10")},
            id="dict:str_interpolation_value",
        ),
        # ListConfig
        param(
            ListConfig(["a", "b"]), {"0": AnyNode("a"), "1": AnyNode("b")}, id="list"
        ),
        param(
            ListConfig(["${1}", 10]),
            {"0": AnyNode("${1}"), "1": AnyNode(10)},
            id="list:interpolation_value",
        ),
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
        param(
            DictConfig({"a": "${b}", "b": 10}),
            "a",
            Wrapper(AnyNode("${b}"), desc="${b} -> { int } 10"),
            id="dict:value_interpolation",
        ),
        # listconfig
        param(ListConfig([10]), 0, AnyNode(10), id="list"),
        param(ListConfig(["???"]), 0, AnyNode("???"), id="list"),
        param(
            ListConfig(["${.1}", 10]),
            0,
            Wrapper(AnyNode("${.1}"), desc="${.1} -> { int } 10"),
            id="list",
        ),
        # wrapper
        param(
            Wrapper(DictConfig({"a": 10}), desc=".."),
            "a",
            AnyNode(10),
            id="dict_in_wrapper",
        ),
        # dereference
        param(
            AnyNode("${a}", parent=DictConfig({"a": 10})),
            "->",
            AnyNode(10),
            id="dereference",
        ),
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
            OmegaConf.create({"a": 10, "inter": "${a}"}),
            "inter",
            {"interpolation": "${a}", "->": AnyNode(10)},
            id="dict:inter",
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
            {"interpolation": "${a}", "->": {"b": 10}},
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
            OmegaConf.create(["${.1}", 10]),
            "0",
            {"interpolation": "${.1}", "->": AnyNode(10)},
            id="list:inter_value",
        ),
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
            {"interpolation": "${a}", "->": [1, 2]},
            id="list:interpolationn_listconfig_value",
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
        # internal wrapper
        (Wrapper, True),
        # not covering some other things.
        (builtins.int, False),
        (dict, False),
        (list, False),
    ],
)
def test_can_provide(resolver: Any, type_: Any, expected: bool) -> None:
    assert resolver.can_provide(type_, type_str(type_)) == expected
