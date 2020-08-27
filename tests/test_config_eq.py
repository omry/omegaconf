from typing import Any

import pytest

from omegaconf import AnyNode, DictConfig, ListConfig, OmegaConf

from . import Group, User


@pytest.mark.parametrize(  # type: ignore
    "i1,i2",
    [
        # === LISTS ===
        # empty list
        pytest.param([], [], id="empty"),
        # simple list
        pytest.param(["a", 12, "15"], ["a", 12, "15"], id="simple_list"),
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
        pytest.param({"a": [1, 2]}, {"a": [1, 2]}, id="list_in_dict"),
        # With interpolations
        ([10, "${0}"], [10, 10]),
        (dict(a=12, b="${a}"), dict(a=12, b=12)),
        # With missing interpolation
        pytest.param([10, "${0}"], [10, 10], id="list_simple_interpolation"),
        pytest.param(
            {"a": "${ref_error}"}, {"a": "${ref_error}"}, id="dict==dict,ref_error"
        ),
        pytest.param({"a": "???"}, {"a": "???"}, id="dict==dict,missing"),
        pytest.param(User, User, id="User==User"),
        pytest.param(
            {"name": "poo", "age": 7}, User(name="poo", age=7), id="dict==User"
        ),
        pytest.param(Group, Group, id="Group==Group"),
        pytest.param({"group": {"admin": None}}, {"group": Group}, id="dict==Group"),
        pytest.param(
            {"i1": "${n1}", "n1": {"a": 10}},
            {"i1": "${n1}", "n1": {"a": 10}},
            id="node_interpolation",
        ),
        # Inter containers
        pytest.param(
            {"foo": DictConfig(content="${bar}"), "bar": 10},
            {"foo": 10, "bar": 10},
            id="dictconfig_inter",
        ),
        pytest.param(
            {"foo": ListConfig(content="${bar}"), "bar": 10},
            {"foo": 10, "bar": 10},
            id="listconfig_inter",
        ),
        # None containers
        pytest.param(
            {"foo": DictConfig(content=None)}, {"foo": None}, id="dictconfig_none"
        ),
        pytest.param(
            {"foo": ListConfig(content=None)}, {"foo": None}, id="listconfig_none"
        ),
        # Missing containers
        pytest.param(
            {"foo": DictConfig(content="???")}, {"foo": "???"}, id="dictconfig_missing"
        ),
        pytest.param(
            {"foo": ListConfig(content="???")}, {"foo": "???"}, id="listconfig_missing"
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


@pytest.mark.parametrize(  # type: ignore
    "input1, input2",
    [
        # Dicts
        pytest.param({}, {"a": 10}, id="empty_dict_neq_dict"),
        pytest.param({}, [], id="empty_dict_vs_list"),
        pytest.param({}, None, id="dict_neq_none"),
        pytest.param({"foo": None}, {"foo": "bar"}, id="dict_none_neq_dict_not_none"),
        pytest.param({"a": 12}, {"a": 13}, id="simple_dict_neq"),
        pytest.param({"a": 0}, {"b": 0}, id="different_key_same_value"),
        pytest.param(dict(a=12), dict(a=AnyNode(13))),
        pytest.param(dict(a=12, b=dict()), dict(a=13, b=dict())),
        pytest.param(dict(a=12, b=dict(c=10)), dict(a=13, b=dict(c=10))),
        pytest.param(dict(a=12, b=[1, 2, 3]), dict(a=12, b=[10, 2, 3])),
        pytest.param(
            dict(a=12, b=[1, 2, AnyNode(3)]), dict(a=12, b=[1, 2, AnyNode(30)])
        ),
        # Lists
        pytest.param([], [10], id="list:empty_vs_full"),
        pytest.param([10], [11], id="list:different_value"),
        ([12], [AnyNode(13)]),
        ([12, dict()], [13, dict()]),
        ([12, dict(c=10)], [13, dict(c=10)]),
        ([12, [1, 2, 3]], [12, [10, 2, 3]]),
        ([12, [1, 2, AnyNode(3)]], [12, [1, 2, AnyNode(30)]]),
        (dict(a="${foo1}"), dict(a="${foo2}")),
        pytest.param(
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
