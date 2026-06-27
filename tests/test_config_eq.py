from dataclasses import dataclass, field
from typing import Any, List

import attr
from pytest import mark, param

from omegaconf import MISSING, AnyNode, DictConfig, ListConfig, OmegaConf
from tests import Group, User


@mark.parametrize(
    "i1,i2",
    [
        # === LISTS ===
        # empty list
        param([], [], id="empty"),
        # simple list
        param(["a", 12, "15"], ["a", 12, "15"], id="simple_list"),
        # raw vs any
        ([1, 2, 12], [1, 2, AnyNode(12)]),
        # nested empty dict
        ([12, {}], [12, {}]),
        # nested dict
        ([12, {"c": 10}], [12, {"c": 10}]),
        # nested list
        ([1, 2, 3, [10, 20, 30]], [1, 2, 3, [10, 20, 30]]),
        # nested list with any
        ([1, 2, 3, [1, 2, AnyNode(3)]], [1, 2, 3, [1, 2, AnyNode(3)]]),
        # === DICTS ===
        # empty
        ({}, {}),
        # simple
        ({"a": 12}, {"a": 12}),
        # any vs raw
        ({"a": 12}, {"a": AnyNode(12)}),
        # nested dict empty
        (dict(a=12, b=dict()), dict(a=12, b=dict())),
        # nested dict
        (dict(a=12, b=dict(c=10)), dict(a=12, b=dict(c=10))),
        # nested list
        (dict(a=12, b=[1, 2, 3]), dict(a=12, b=[1, 2, 3])),
        # nested list with any
        (dict(a=12, b=[1, 2, AnyNode(3)]), dict(a=12, b=[1, 2, AnyNode(3)])),
        # In python 3.6+ insert order changes iteration order. this ensures that equality is preserved.
        (dict(a=1, b=2, c=3, d=4, e=5), dict(e=5, b=2, c=3, d=4, a=1)),
        (DictConfig(content=None), DictConfig(content=None)),
        param({"a": [1, 2]}, {"a": [1, 2]}, id="list_in_dict"),
        # With interpolations
        ([10, "${0}"], [10, 10]),
        (dict(a=12, b="${a}"), dict(a=12, b=12)),
        # With missing interpolation
        param([10, "${0}"], [10, 10], id="list_simple_interpolation"),
        param({"a": "${ref_error}"}, {"a": "${ref_error}"}, id="dict==dict,ref_error"),
        param({"a": "???"}, {"a": "???"}, id="dict==dict,missing"),
        param(User, User, id="User==User"),
        param({"name": "poo", "age": 7}, User(name="poo", age=7), id="dict==User"),
        param(Group, Group, id="Group==Group"),
        param({"group": {"admin": None}}, {"group": Group}, id="dict==Group"),
        param(
            {"i1": "${n1}", "n1": {"a": 10}},
            {"i1": "${n1}", "n1": {"a": 10}},
            id="node_interpolation",
        ),
        # Inter containers
        param(
            {"foo": DictConfig(content="${bar}"), "bar": 10},
            {"foo": 10, "bar": 10},
            id="dictconfig_inter",
        ),
        param(
            {"foo": ListConfig(content="${bar}"), "bar": 10},
            {"foo": 10, "bar": 10},
            id="listconfig_inter",
        ),
        # None containers
        param({"foo": DictConfig(content=None)}, {"foo": None}, id="dictconfig_none"),
        param({"foo": ListConfig(content=None)}, {"foo": None}, id="listconfig_none"),
        # Missing containers
        param(DictConfig("???"), DictConfig("???"), id="missing_dictconfig"),
        param(ListConfig("???"), ListConfig("???"), id="missing_listconfig"),
        param(
            {"foo": DictConfig("???")}, {"foo": "???"}, id="nested_missing_dictconfig"
        ),
        param(
            {"foo": ListConfig("???")}, {"foo": "???"}, id="nested_missing_listconfig"
        ),
    ],
)
def test_eq(i1: Any, i2: Any) -> None:
    c1 = OmegaConf.create(i1)
    c2 = OmegaConf.create(i2)

    def eq(a: Any, b: Any) -> None:
        assert a == b
        assert b == a
        assert not a != b
        assert not b != a

    eq(c1, c2)
    eq(c1, i1)
    eq(c2, i2)


@mark.parametrize(
    "cfg,other",
    [
        param(DictConfig("???"), "???", id="missing_dictconfig"),
        param(ListConfig("???"), "???", id="missing_listconfig"),
    ],
)
def test_missing_container_string_eq(cfg: Any, other: Any) -> None:
    assert cfg == other
    assert other == cfg
    assert not (cfg != other)
    assert not (other != cfg)


@mark.parametrize(
    "input1, input2",
    [
        # Dicts
        param({}, {"a": 10}, id="empty_dict_neq_dict"),
        param({}, [], id="empty_dict_vs_list"),
        param({}, None, id="dict_neq_none"),
        param(DictConfig(None), {}, id="none_dictconfig_neq_dict"),
        param({"foo": None}, {"foo": "bar"}, id="dict_none_neq_dict_not_none"),
        param({"a": 12}, {"a": 13}, id="simple_dict_neq"),
        param({"a": 0}, {"b": 0}, id="different_key_same_value"),
        param(dict(a=12), dict(a=AnyNode(13))),
        param(dict(a=12, b=dict()), dict(a=13, b=dict())),
        param(dict(a=12, b=dict(c=10)), dict(a=13, b=dict(c=10))),
        param(dict(a=12, b=[1, 2, 3]), dict(a=12, b=[10, 2, 3])),
        param(dict(a=12, b=[1, 2, AnyNode(3)]), dict(a=12, b=[1, 2, AnyNode(30)])),
        # Lists
        param([], [10], id="list:empty_vs_full"),
        param([10], [11], id="list:different_value"),
        ([12], [AnyNode(13)]),
        ([12, dict()], [13, dict()]),
        ([12, dict(c=10)], [13, dict(c=10)]),
        ([12, [1, 2, 3]], [12, [10, 2, 3]]),
        ([12, [1, 2, AnyNode(3)]], [12, [1, 2, AnyNode(30)]]),
        (dict(a="${foo1}"), dict(a="${foo2}")),
        param(
            {"i1": "${n1}", "n1": {"a": 10}},
            {"i1": "${n1}", "n1": {"a": 20}},
            id="node_interpolation",
        ),
    ],
)
def test_not_eq(input1: Any, input2: Any) -> None:
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def neq(a: Any, b: Any) -> None:
        assert a != b
        assert b != a
        assert not a == b
        assert not b == a

    neq(c1, c2)
    neq(c2, c1)


# ---
def test_config_eq_mismatch_types() -> None:
    c1 = OmegaConf.create({})
    c2 = OmegaConf.create([])
    assert c1 != c2


def test_dict_not_eq_with_another_class() -> None:
    assert OmegaConf.create({}) != "string"
    assert OmegaConf.create([]) != "string"


def _assert_structural_equality(input1: Any, input2: Any, expected: bool) -> None:
    cfg1 = input1 if OmegaConf.is_config(input1) else OmegaConf.create(input1)
    cfg2 = input2 if OmegaConf.is_config(input2) else OmegaConf.create(input2)

    assert OmegaConf.structural_equality(cfg1, cfg2) is expected
    assert OmegaConf.structural_equality(cfg2, cfg1) is expected
    assert (
        OmegaConf.to_container(cfg1, resolve=False, throw_on_missing=False)
        == OmegaConf.to_container(cfg2, resolve=False, throw_on_missing=False)
    ) is expected


@mark.parametrize(
    "input1,input2,expected",
    [
        param({}, {}, True, id="dict:empty"),
        param({"a": 10}, {"a": 10}, True, id="dict:level1-same"),
        param({"a": 10}, {"a": 20}, False, id="dict:level1-diff"),
        param({"a": {"b": 10}}, {"a": {"b": 10}}, True, id="dict:level2-same"),
        param({"a": {"b": 10}}, {"a": {"b": 20}}, False, id="dict:level2-diff"),
        param(
            {"a": {"b": {"c": 10}}},
            {"a": {"b": {"c": 10}}},
            True,
            id="dict:level3-same",
        ),
        param(
            {"a": {"b": {"c": 10}}},
            {"a": {"b": {"c": 20}}},
            False,
            id="dict:level3-diff",
        ),
        param([], [], True, id="list:empty"),
        param([10], [10], True, id="list:level1-same"),
        param([10], [20], False, id="list:level1-diff"),
        param([[10]], [[10]], True, id="list:level2-same"),
        param([[10]], [[20]], False, id="list:level2-diff"),
        param([[[10]]], [[[10]]], True, id="list:level3-same"),
        param([[[10]]], [[[20]]], False, id="list:level3-diff"),
        param(
            {"a": [{"b": [10, {"c": 20}]}]},
            {"a": [{"b": [10, {"c": 20}]}]},
            True,
            id="mixed:dict-list-dict-list-dict-same",
        ),
        param(
            {"a": [{"b": [10, {"c": 20}]}]},
            {"a": [{"b": [10, {"c": 21}]}]},
            False,
            id="mixed:dict-list-dict-list-dict-diff",
        ),
        param({}, [], False, id="type:dict-vs-list"),
        param({"a": "???"}, {"a": "???"}, True, id="missing:dict-value-same"),
        param({"a": "???"}, {"a": 10}, False, id="missing:dict-value-vs-value"),
        param(["???"], ["???"], True, id="missing:list-item-same"),
        param(["???"], [10], False, id="missing:list-item-vs-value"),
        param(DictConfig("???"), DictConfig("???"), True, id="missing:dictconfig-root"),
        param(ListConfig("???"), ListConfig("???"), True, id="missing:listconfig-root"),
        param(
            {"a": DictConfig("???")},
            {"a": DictConfig("???")},
            True,
            id="missing:nested-dictconfig",
        ),
        param(
            {"a": ListConfig("???")},
            {"a": ListConfig("???")},
            True,
            id="missing:nested-listconfig",
        ),
    ],
)
def test_structural_equality_plain_containers(
    input1: Any, input2: Any, expected: bool
) -> None:
    _assert_structural_equality(input1, input2, expected)


@mark.parametrize(
    "data1,data2,path",
    [
        param(
            {"node": {"value": "${target}"}, "target": 10},
            {"node": {"value": "${target}"}, "target": 20},
            ["node"],
            id="dict:level1",
        ),
        param(
            {"node": {"child": {"value": "${target}"}}, "target": 10},
            {"node": {"child": {"value": "${target}"}}, "target": 20},
            ["node", "child"],
            id="dict:level2",
        ),
        param(
            {"node": [{"value": "${target}"}], "target": 10},
            {"node": [{"value": "${target}"}], "target": 20},
            ["node", 0],
            id="list-in-dict",
        ),
        param(
            [[{"value": "${target}"}], {"target": 10}],
            [[{"value": "${target}"}], {"target": 20}],
            [0, 0],
            id="dict-in-nested-list",
        ),
    ],
)
def test_structural_equality_compares_raw_interpolations_at_nested_levels(
    data1: Any, data2: Any, path: List[Any]
) -> None:
    cfg1 = OmegaConf.create(data1)
    cfg2 = OmegaConf.create(data2)
    node1 = cfg1
    node2 = cfg2
    for key in path:
        node1 = node1[key]
        node2 = node2[key]

    assert OmegaConf.structural_equality(node1, node2)
    assert not OmegaConf.structural_equality(cfg1, cfg2)


def test_structural_equality_compares_different_raw_interpolations() -> None:
    cfg1 = OmegaConf.create({"a": {"b": "${c}"}, "c": 10})
    cfg2 = OmegaConf.create({"a": {"b": "${d}"}, "d": 10})

    assert not OmegaConf.structural_equality(cfg1.a, cfg2.a)


def test_structural_equality_does_not_resolve_missing_interpolation() -> None:
    cfg1 = OmegaConf.create({"a": "${missing}"})
    cfg2 = OmegaConf.create({"a": "${missing}"})

    assert OmegaConf.structural_equality(cfg1, cfg2)


def test_structural_equality_dataclass_structured_configs() -> None:
    @dataclass
    class Level3:
        value: int = 10
        raw: str = "${target}"
        missing: str = MISSING

    @dataclass
    class Level2:
        child: Level3 = field(default_factory=Level3)
        values: List[int] = field(default_factory=lambda: [1, 2, 3])

    @dataclass
    class Level1:
        child: Level2 = field(default_factory=Level2)
        target: int = 10

    cfg1 = OmegaConf.structured(Level1(target=10))
    cfg2 = OmegaConf.structured(Level1(target=20))
    cfg3 = OmegaConf.structured(Level1(child=Level2(child=Level3(value=20)), target=10))

    assert OmegaConf.structural_equality(cfg1.child, cfg2.child)
    assert OmegaConf.structural_equality(cfg1.child.child, cfg2.child.child)
    assert not OmegaConf.structural_equality(cfg1, cfg2)
    assert not OmegaConf.structural_equality(cfg1, cfg3)


def test_structural_equality_attrs_structured_configs() -> None:
    @attr.s(auto_attribs=True)
    class Level3:
        value: int = 10
        raw: str = "${target}"
        missing: str = MISSING

    @attr.s(auto_attribs=True)
    class Level2:
        child: Level3 = attr.ib(factory=Level3)
        values: List[int] = attr.ib(factory=lambda: [1, 2, 3])

    @attr.s(auto_attribs=True)
    class Level1:
        child: Level2 = attr.ib(factory=Level2)
        target: int = 10

    cfg1 = OmegaConf.structured(Level1(target=10))
    cfg2 = OmegaConf.structured(Level1(target=20))
    cfg3 = OmegaConf.structured(Level1(child=Level2(child=Level3(value=20))))

    assert OmegaConf.structural_equality(cfg1.child, cfg2.child)
    assert OmegaConf.structural_equality(cfg1.child.child, cfg2.child.child)
    assert not OmegaConf.structural_equality(cfg1, cfg2)
    assert not OmegaConf.structural_equality(cfg1, cfg3)


def test_structural_equality_custom_resolvers_are_not_called_in_dicts_and_lists(
    restore_resolvers: Any,
) -> None:
    calls = 0

    def fail_if_called() -> int:
        nonlocal calls
        calls += 1
        raise AssertionError("resolver should not be called")

    OmegaConf.register_resolver("fail_if_called", fail_if_called)

    cfg1 = OmegaConf.create(
        {
            "dict_node": {"value": "${fail_if_called:}"},
            "list_node": [{"value": "${fail_if_called:1}"}],
            "other": 10,
        }
    )
    cfg2 = OmegaConf.create(
        {
            "dict_node": {"value": "${fail_if_called:}"},
            "list_node": [{"value": "${fail_if_called:1}"}],
            "other": 20,
        }
    )
    cfg3 = OmegaConf.create({"dict_node": {"value": "${fail_if_called:2}"}})

    assert OmegaConf.structural_equality(cfg1.dict_node, cfg2.dict_node)
    assert OmegaConf.structural_equality(cfg1.list_node[0], cfg2.list_node[0])
    assert not OmegaConf.structural_equality(cfg1, cfg2)
    assert not OmegaConf.structural_equality(cfg1.dict_node, cfg3.dict_node)
    assert calls == 0


def test_structural_equality_custom_resolvers_are_not_called_in_structured_configs(
    restore_resolvers: Any,
) -> None:
    calls = 0

    def fail_if_called() -> int:
        nonlocal calls
        calls += 1
        raise AssertionError("resolver should not be called")

    OmegaConf.register_resolver("fail_if_called", fail_if_called)

    @dataclass
    class Child:
        value: str = "${fail_if_called:}"

    @dataclass
    class Parent:
        child: Child = field(default_factory=Child)
        other: int = 10

    cfg1 = OmegaConf.structured(Parent(other=10))
    cfg2 = OmegaConf.structured(Parent(other=20))
    cfg3 = OmegaConf.structured(Parent(child=Child(value="${fail_if_called:1}")))

    assert OmegaConf.structural_equality(cfg1.child, cfg2.child)
    assert not OmegaConf.structural_equality(cfg1, cfg2)
    assert not OmegaConf.structural_equality(cfg1.child, cfg3.child)
    assert calls == 0
