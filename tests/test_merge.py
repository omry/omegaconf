import sys
from typing import Any, Dict, List, MutableMapping, MutableSequence, Tuple, Union

import pytest

from omegaconf import (
    MISSING,
    DictConfig,
    ListConfig,
    OmegaConf,
    ReadonlyConfigError,
    ValidationError,
    nodes,
)
from omegaconf._utils import is_structured_config
from omegaconf.errors import ConfigKeyError

from . import (
    A,
    B,
    C,
    ConcretePlugin,
    ConfWithMissingDict,
    Group,
    InterpolationDict,
    InterpolationList,
    MissingDict,
    MissingList,
    Package,
    Plugin,
    User,
    Users,
)


@pytest.mark.parametrize(  # type: ignore
    "inputs, expected",
    [
        # dictionaries
        ([{}, {"a": 1}], {"a": 1}),
        ([{"a": None}, {"b": None}], {"a": None, "b": None}),
        ([{"a": 1}, {"b": 2}], {"a": 1, "b": 2}),
        ([{"a": {"a1": 1, "a2": 2}}, {"a": {"a1": 2}}], {"a": {"a1": 2, "a2": 2}}),
        ([{"a": 1, "b": 2}, {"b": 3}], {"a": 1, "b": 3}),
        (({"a": 1, "b": 2}, {"b": {"c": 3}}), {"a": 1, "b": {"c": 3}}),
        (({"b": {"c": 1}}, {"b": 1}), {"b": 1}),
        (({"list": [1, 2, 3]}, {"list": [4, 5, 6]}), {"list": [4, 5, 6]}),
        (({"a": 1}, {"a": nodes.IntegerNode(10)}), {"a": 10}),
        (({"a": 1}, {"a": nodes.IntegerNode(10)}), {"a": nodes.IntegerNode(10)}),
        (({"a": nodes.IntegerNode(10)}, {"a": 1}), {"a": 1}),
        (({"a": nodes.IntegerNode(10)}, {"a": 1}), {"a": nodes.IntegerNode(1)}),
        pytest.param(
            ({"a": "???"}, {"a": {}}), {"a": {}}, id="dict_merge_into_missing"
        ),
        pytest.param(
            ({"a": "???"}, {"a": {"b": 10}}),
            {"a": {"b": 10}},
            id="dict_merge_into_missing",
        ),
        pytest.param(
            ({"a": {"b": 10}}, {"a": "???"}),
            {"a": "???"},
            id="dict_merge_missing_onto",
        ),
        # lists
        (([1, 2, 3], [4, 5, 6]), [4, 5, 6]),
        (([[1, 2, 3]], [[4, 5, 6]]), [[4, 5, 6]]),
        (([1, 2, {"a": 10}], [4, 5, {"b": 20}]), [4, 5, {"b": 20}]),
        pytest.param(
            ({"a": "???"}, {"a": []}), {"a": []}, id="list_merge_into_missing"
        ),
        pytest.param(
            ({"a": "???"}, {"a": [1, 2, 3]}),
            {"a": [1, 2, 3]},
            id="list_merge_into_missing",
        ),
        pytest.param(
            ({"a": [1, 2, 3]}, {"a": "???"}),
            {"a": "???"},
            id="list_merge_missing_onto",
        ),
        pytest.param(
            ([1, 2, 3], ListConfig(content=MISSING)),
            ListConfig(content=MISSING),
            id="list_merge_missing_onto2",
        ),
        # Interpolations
        # value interpolation
        pytest.param(
            ({"d1": 1, "inter": "${d1}"}, {"d1": 2}),
            {"d1": 2, "inter": 2},
            id="inter:updating_data",
        ),
        pytest.param(
            ({"d1": 1, "d2": 2, "inter": "${d1}"}, {"inter": "${d2}"}),
            {"d1": 1, "d2": 2, "inter": 2},
            id="inter:value_inter_over_value_inter",
        ),
        pytest.param(
            ({"inter": "${d1}"}, {"inter": 123}),
            {"inter": 123},
            id="inter:data_over_value_inter",
        ),
        pytest.param(
            ({"inter": "${d1}", "d1": 1, "n1": {"foo": "bar"}}, {"inter": "${n1}"}),
            {"inter": {"foo": "bar"}, "d1": 1, "n1": {"foo": "bar"}},
            id="inter:node_inter_over_value_inter",
        ),
        pytest.param(
            ({"inter": 123}, {"inter": "${data}"}),
            {"inter": "${data}"},
            id="inter:inter_over_data",
        ),
        # node interpolation
        pytest.param(
            ({"n": {"a": 10}, "i": "${n}"}, {"n": {"a": 20}}),
            {"n": {"a": 20}, "i": {"a": 20}},
            id="node_inter:node_update",
        ),
        pytest.param(
            ({"d": 20, "n": {"a": 10}, "i": "${n}"}, {"i": "${d}"}),
            {"d": 20, "n": {"a": 10}, "i": 20},
            id="node_inter:value_inter_over_node_inter",
        ),
        pytest.param(
            ({"n": {"a": 10}, "i": "${n}"}, {"i": 30}),
            {"n": {"a": 10}, "i": 30},
            id="node_inter:data_over_node_inter",
        ),
        pytest.param(
            ({"n1": {"a": 10}, "n2": {"b": 20}, "i": "${n1}"}, {"i": "${n2}"}),
            {"n1": {"a": 10}, "n2": {"b": 20}, "i": {"b": 20}},
            id="node_inter:node_inter_over_node_inter",
        ),
        pytest.param(
            ({"v": 10, "n": {"a": 20}}, {"v": "${n}"}),
            {"v": {"a": 20}, "n": {"a": 20}},
            id="inter:node_inter_over_data",
        ),
        pytest.param(
            ({"n": {"a": 10}, "i": "${n}"}, {"i": {"b": 20}}),
            {"n": {"a": 10}, "i": {"a": 10, "b": 20}},
            id="inter:node_over_node_interpolation",
        ),
        # Structured configs
        (({"user": User}, {}), {"user": User(name=MISSING, age=MISSING)}),
        (({"user": User}, {"user": {}}), {"user": User(name=MISSING, age=MISSING)}),
        (
            ({"user": User}, {"user": {"name": "Joe"}}),
            {"user": User(name="Joe", age=MISSING)},
        ),
        (
            ({"user": User}, {"user": {"name": "Joe", "age": 10}}),
            {"user": User(name="Joe", age=10)},
        ),
        ([{"users": Users}], {"users": {"name2user": {}}}),
        ([Users], {"name2user": {}}),
        ([Users, {"name2user": {}}], {"name2user": {}}),
        (
            [Users, {"name2user": {"joe": User}}],
            {"name2user": {"joe": {"name": MISSING, "age": MISSING}}},
        ),
        (
            [Users, {"name2user": {"joe": User(name="joe")}}],
            {"name2user": {"joe": {"name": "joe", "age": MISSING}}},
        ),
        pytest.param(
            [Users, {"name2user": {"joe": {"name": "joe"}}}],
            {"name2user": {"joe": {"name": "joe", "age": MISSING}}},
            id="users_merge_with_missing_age",
        ),
        pytest.param(
            [ConfWithMissingDict, {"dict": {"foo": "bar"}}],
            {"dict": {"foo": "bar"}},
            id="conf_missing_dict",
        ),
        pytest.param(
            [{}, ConfWithMissingDict],
            {"dict": "???"},
            id="merge_missing_dict_into_missing_dict",
        ),
        ([{"user": User}, {"user": Group}], pytest.raises(ValidationError)),
        (
            [{"user": DictConfig(ref_type=User, content=User)}, {"user": Group}],
            pytest.raises(ValidationError),
        ),
        ([Plugin, ConcretePlugin], ConcretePlugin),
        pytest.param(
            [{"user": "???"}, {"user": Group}],
            {"user": Group},
            id="merge_into_missing_node",
        ),
        ([{"user": User()}, {"user": {"foo": "bar"}}], pytest.raises(ConfigKeyError)),
        # missing DictConfig
        pytest.param(
            [{"dict": DictConfig(content="???")}, {"dict": {"foo": "bar"}}],
            {"dict": {"foo": "bar"}},
            id="merge_into_missing_DictConfig",
        ),
        # missing Dict[str, str]
        pytest.param(
            [MissingDict, {"dict": {"foo": "bar"}}],
            {"dict": {"foo": "bar"}},
            id="merge_into_missing_Dict[str,str]",
        ),
        # missing ListConfig
        pytest.param(
            [{"list": ListConfig(content="???")}, {"list": [1, 2, 3]}],
            {"list": [1, 2, 3]},
            id="merge_into_missing_ListConfig",
        ),
        # missing List[str]
        pytest.param(
            [MissingList, {"list": ["a", "b", "c"]}],
            {"list": ["a", "b", "c"]},
            id="merge_into_missing_List[str]",
        ),
        # merging compatible dict into MISSING structured config expands it
        # to ensure the resulting node follows the protocol set by the underlying type
        pytest.param(
            [B, {"x": {}}], {"x": {"a": 10}}, id="structured_merge_into_missing"
        ),
        pytest.param(
            [B, {"x": {"a": 20}}], {"x": {"a": 20}}, id="structured_merge_into_missing"
        ),
        pytest.param([C, {"x": A}], {"x": {"a": 10}}, id="structured_merge_into_none"),
        pytest.param([C, C], {"x": None}, id="none_not_expanding"),
        # Merge into list with Structured Config
        pytest.param(
            [ListConfig(content=[], element_type=User), [{}]],
            [User()],
            id="list_sc_element_merge_dict",
        ),
        pytest.param(
            [ListConfig(content=[], element_type=User), [{"name": "Bond", "age": 7}]],
            [User(name="Bond", age=7)],
            id="list_sc_element_merge_dict",
        ),
        pytest.param(
            [ListConfig(content=[], element_type=User), [{"name": "Bond"}]],
            [User(name="Bond", age=MISSING)],
            id="list_sc_element_merge_dict",
        ),
    ],
)
def test_merge(inputs: Any, expected: Any) -> None:
    configs = [OmegaConf.create(c) for c in inputs]

    if isinstance(expected, (MutableMapping, MutableSequence)) or is_structured_config(
        expected
    ):
        merged = OmegaConf.merge(*configs)
        assert merged == expected
        # test input configs are not changed.
        # Note that converting to container without resolving to avoid resolution errors while comparing
        for i in range(len(inputs)):
            input_i = OmegaConf.create(inputs[i])
            orig = OmegaConf.to_container(input_i, resolve=False)
            merged2 = OmegaConf.to_container(configs[i], resolve=False)
            assert orig == merged2
    else:
        with expected:
            OmegaConf.merge(*configs)


def test_merge_error_retains_type() -> None:
    cfg = OmegaConf.structured(ConcretePlugin)
    with pytest.raises(ValidationError):
        cfg.merge_with({"params": {"foo": "error"}})
    assert OmegaConf.get_type(cfg) == ConcretePlugin


def test_primitive_dicts() -> None:
    c1 = {"a": 10}
    c2 = {"b": 20}
    merged = OmegaConf.merge(c1, c2)
    assert merged == {"a": 10, "b": 20}


@pytest.mark.parametrize(  # type: ignore
    "a_, b_, expected", [((1, 2, 3), (4, 5, 6), [4, 5, 6])]
)
def test_merge_no_eq_verify(
    a_: Tuple[int], b_: Tuple[int], expected: Tuple[int]
) -> None:
    a = OmegaConf.create(a_)
    b = OmegaConf.create(b_)
    c = OmegaConf.merge(a, b)
    # verify merge result is expected
    assert expected == c


@pytest.mark.parametrize(  # type: ignore
    "c1,c2,expected",
    [({}, {"a": 1, "b": 2}, {"a": 1, "b": 2}), ({"a": 1}, {"b": 2}, {"a": 1, "b": 2})],
)
def test_merge_with(c1: Any, c2: Any, expected: Any) -> None:
    a = OmegaConf.create(c1)
    b = OmegaConf.create(c2)
    a.merge_with(b)
    assert a == expected


@pytest.mark.parametrize(  # type: ignore
    "c1,c2,expected",
    [({}, {"a": 1, "b": 2}, {"a": 1, "b": 2}), ({"a": 1}, {"b": 2}, {"a": 1, "b": 2})],
)
def test_merge_with_c2_readonly(c1: Any, c2: Any, expected: Any) -> None:
    a = OmegaConf.create(c1)
    b = OmegaConf.create(c2)
    OmegaConf.set_readonly(b, True)
    a.merge_with(b)
    assert a == expected
    assert OmegaConf.is_readonly(a)


def test_3way_dict_merge() -> None:
    c1 = OmegaConf.create("{a: 1, b: 2}")
    c2 = OmegaConf.create("{b: 3}")
    c3 = OmegaConf.create("{a: 2, c: 3}")
    c4 = OmegaConf.merge(c1, c2, c3)
    assert {"a": 2, "b": 3, "c": 3} == c4


def test_merge_list_list() -> None:
    a = OmegaConf.create([1, 2, 3])
    b = OmegaConf.create([4, 5, 6])
    a.merge_with(b)
    assert a == b


@pytest.mark.parametrize(  # type: ignore
    "base, merge, exception",
    [
        ({}, [], TypeError),
        ([], {}, TypeError),
        ([1, 2, 3], None, ValueError),
        ({"a": 10}, None, ValueError),
        (Package, {"modules": [{"foo": "var"}]}, ConfigKeyError),
    ],
)
def test_merge_error(base: Any, merge: Any, exception: Any) -> None:
    base = OmegaConf.create(base)
    merge = None if merge is None else OmegaConf.create(merge)
    with pytest.raises(exception):
        OmegaConf.merge(base, merge)


@pytest.mark.parametrize(  # type: ignore
    "c1, c2",
    [
        pytest.param({"foo": "bar"}, {"zoo": "foo"}, id="dict"),
        pytest.param([1, 2, 3], [4, 5, 6], id="list"),
    ],
)
def test_with_readonly_c1(c1: Any, c2: Any) -> None:
    cfg1 = OmegaConf.create(c1)
    cfg2 = OmegaConf.create(c2)
    OmegaConf.set_readonly(cfg1, True)
    cfg3 = OmegaConf.merge(cfg1, cfg2)
    assert OmegaConf.is_readonly(cfg3)


@pytest.mark.parametrize(  # type: ignore
    "c1, c2",
    [
        pytest.param({"foo": "bar"}, {"zoo": "foo"}, id="dict"),
        pytest.param([1, 2, 3], [4, 5, 6], id="list"),
    ],
)
def test_with_readonly_c2(c1: Any, c2: Any) -> None:
    cfg1 = OmegaConf.create(c1)
    cfg2 = OmegaConf.create(c1)
    OmegaConf.set_readonly(cfg2, True)
    cfg3 = OmegaConf.merge(cfg1, cfg2)
    assert OmegaConf.is_readonly(cfg3)


@pytest.mark.parametrize(  # type: ignore
    "c1, c2", [({"foo": "bar"}, {"zoo": "foo"}), ([1, 2, 3], [4, 5, 6])]
)
def test_into_readonly(c1: Any, c2: Any) -> None:
    cfg = OmegaConf.create(c1)
    OmegaConf.set_readonly(cfg, True)
    with pytest.raises(ReadonlyConfigError):
        cfg.merge_with(c2)


@pytest.mark.parametrize(  # type: ignore
    "c1, c2, expected",
    [
        (
            {"node": {"foo": "bar"}},
            {"node": {"zoo": "foo"}},
            {"node": {"foo": "bar", "zoo": "foo"}},
        ),
    ],
)
def test_dict_merge_readonly_into_readwrite(c1: Any, c2: Any, expected: Any) -> None:
    c1 = OmegaConf.create(c1)
    c2 = OmegaConf.create(c2)
    OmegaConf.set_readonly(c2.node, True)
    with pytest.raises(ReadonlyConfigError):
        c2.node.foo = 10
    assert OmegaConf.merge(c1, c2) == expected
    c1.merge_with(c2)
    assert c1 == expected


@pytest.mark.parametrize(  # type: ignore
    "c1, c2, expected",
    [({"node": [1, 2, 3]}, {"node": [4, 5, 6]}, {"node": [4, 5, 6]})],
)
def test_list_merge_readonly_into_readwrite(c1: Any, c2: Any, expected: Any) -> None:
    c1 = OmegaConf.create(c1)
    c2 = OmegaConf.create(c2)
    OmegaConf.set_readonly(c2.node, True)
    with pytest.raises(ReadonlyConfigError):
        c2.node.append(10)
    assert OmegaConf.merge(c1, c2) == expected
    c1.merge_with(c2)
    assert c1 == expected


def test_parent_maintained() -> None:
    c1 = OmegaConf.create({"a": {"b": 10}})
    c2 = OmegaConf.create({"aa": {"bb": 100}})
    c3 = OmegaConf.merge(c1, c2)
    assert isinstance(c1, DictConfig)
    assert isinstance(c2, DictConfig)
    assert isinstance(c3, DictConfig)
    assert id(c1.a._get_parent()) == id(c1)
    assert id(c2.aa._get_parent()) == id(c2)
    assert id(c3.a._get_parent()) == id(c3)


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


@pytest.mark.parametrize(  # type:ignore
    "dst, other, expected, node",
    [
        pytest.param(
            OmegaConf.structured(InterpolationList),
            OmegaConf.create({"list": [0.1]}),
            {"list": [0.1]},
            "list",
            id="merge_interpolation_list_with_list",
        ),
        pytest.param(
            OmegaConf.structured(InterpolationDict),
            OmegaConf.create({"dict": {"a": 4}}),
            {"dict": {"a": 4}},
            "dict",
            id="merge_interpolation_dict_with_dict",
        ),
    ],
)
def test_merge_with_src_as_interpolation(
    dst: Any, other: Any, expected: Any, node: Any
) -> None:
    res = OmegaConf.merge(dst, other)
    assert res == expected


@pytest.mark.parametrize(  # type:ignore
    "dst, other, node",
    [
        pytest.param(
            OmegaConf.structured(InterpolationDict),
            OmegaConf.structured(InterpolationDict),
            "dict",
            id="merge_interpolation_dict_with_interpolation_dict",
        ),
        pytest.param(
            OmegaConf.structured(InterpolationList),
            OmegaConf.structured(InterpolationList),
            "list",
            id="merge_interpolation_list_with_interpolation_list",
        ),
    ],
)
def test_merge_with_other_as_interpolation(dst: Any, other: Any, node: Any) -> None:
    res = OmegaConf.merge(dst, other)
    assert OmegaConf.is_interpolation(res, node)
