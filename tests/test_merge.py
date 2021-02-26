import copy
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
)
from omegaconf._utils import is_structured_config
from omegaconf.errors import ConfigKeyError, UnsupportedValueType
from omegaconf.nodes import IntegerNode
from tests import (
    A,
    B,
    C,
    ConcretePlugin,
    ConfWithMissingDict,
    Dataframe,
    Group,
    IllegalType,
    InterpolationDict,
    InterpolationList,
    MissingDict,
    MissingList,
    Package,
    Plugin,
    User,
    Users,
)


@pytest.mark.parametrize(
    ("merge_function", "input_unchanged"),
    [
        pytest.param(OmegaConf.merge, True, id="merge"),
        pytest.param(OmegaConf.unsafe_merge, False, id="unsafe_merge"),
    ],
)
@pytest.mark.parametrize(
    "inputs, expected",
    [
        # dictionaries
        pytest.param([{}, {"a": 1}], {"a": 1}, id="dict"),
        pytest.param(
            [{"a": None}, {"b": None}], {"a": None, "b": None}, id="dict:none"
        ),
        pytest.param([{"a": 1}, {"b": 2}], {"a": 1, "b": 2}, id="dict"),
        pytest.param(
            [
                {"a": {"a1": 1, "a2": 2}},
                {"a": {"a1": 2}},
            ],
            {"a": {"a1": 2, "a2": 2}},
            id="dict",
        ),
        pytest.param([{"a": 1, "b": 2}, {"b": 3}], {"a": 1, "b": 3}, id="dict"),
        pytest.param(
            ({"a": 1}, {"a": {"b": 3}}), {"a": {"b": 3}}, id="dict:merge_dict_into_int"
        ),
        pytest.param(({"b": {"c": 1}}, {"b": 1}), {"b": 1}, id="dict:merge_int_dict"),
        pytest.param(({"list": [1, 2, 3]}, {"list": [4, 5, 6]}), {"list": [4, 5, 6]}),
        pytest.param(({"a": 1}, {"a": IntegerNode(10)}), {"a": 10}),
        pytest.param(({"a": 1}, {"a": IntegerNode(10)}), {"a": IntegerNode(10)}),
        pytest.param(({"a": IntegerNode(10)}, {"a": 1}), {"a": 1}),
        pytest.param(({"a": IntegerNode(10)}, {"a": 1}), {"a": IntegerNode(1)}),
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
            {"a": {"b": 10}},
            id="dict_merge_missing_onto",
        ),
        pytest.param(
            ({"a": {"b": 10}}, {"a": DictConfig(content="???")}),
            {"a": {"b": 10}},
            id="dict_merge_missing_onto",
        ),
        pytest.param(
            ({}, {"a": "???"}),
            {"a": "???"},
            id="dict_merge_missing_onto_no_node",
        ),
        pytest.param(
            (
                {"a": 0, "b": 1},
                {"a": "${b}", "b": "???"},
            ),
            {"a": "${b}", "b": 1},
            id="dict_merge_inter_to_missing",
        ),
        pytest.param(
            (
                {"a": [0], "b": [1]},
                {"a": ListConfig(content="${b}"), "b": "???"},
            ),
            {"a": ListConfig(content="${b}"), "b": [1]},
            id="dict_with_list_merge_inter_to_missing",
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
            {"a": [1, 2, 3]},
            id="list_merge_missing_onto",
        ),
        pytest.param(
            ([1, 2, 3], ListConfig(content=MISSING)),
            ListConfig(content=[1, 2, 3]),
            id="list_merge_missing_onto",
        ),
        pytest.param(
            ({"a": 10, "list": []}, {"list": ["${a}"]}),
            {"a": 10, "list": [10]},
            id="merge_list_with_interpolation",
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
            (
                {"n": {"a": 10}, "i": "${n}"},
                {"i": {"b": 20}},
            ),
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
        pytest.param(
            [{"user": User}, {"user": Group}],
            pytest.raises(ValidationError),
            id="merge_group_onto_user_error",
        ),
        pytest.param(
            [Plugin, ConcretePlugin], ConcretePlugin, id="merge_subclass_on_superclass"
        ),
        pytest.param(
            [{"user": "???"}, {"user": Group}],
            {"user": Group},
            id="merge_into_missing_node",
        ),
        pytest.param(
            [{"admin": {"name": "joe", "age": 42}}, Group(admin=None)],
            {"admin": None},
            id="merge_none_into_existing_node",
        ),
        pytest.param(
            [{"user": User()}, {"user": {"foo": "bar"}}],
            pytest.raises(ConfigKeyError),
            id="merge_unknown_key_into_structured_node",
        ),
        # DictConfig with element_type of Structured Config
        pytest.param(
            (
                DictConfig({}, element_type=User),
                {"user007": {"age": 99}},
            ),
            {"user007": {"name": "???", "age": 99}},
            id="dict:merge_into_sc_element_type:expanding_new_element",
        ),
        pytest.param(
            (
                DictConfig({"user007": "???"}, element_type=User),
                {"user007": {"age": 99}},
            ),
            {"user007": {"name": "???", "age": 99}},
            id="dict:merge_into_sc_element_type:into_missing_element",
        ),
        pytest.param(
            (
                DictConfig({"user007": User("bond", 7)}, element_type=User),
                {"user007": {"age": 99}},
            ),
            {"user007": {"name": "bond", "age": 99}},
            id="dict:merge_into_sc_element_type:merging_with_existing_element",
        ),
        pytest.param(
            (
                DictConfig({"user007": None}, element_type=User),
                {"user007": {"age": 99}},
            ),
            {"user007": {"name": "???", "age": 99}},
            id="dict:merge_into_sc_element_type:merging_into_none",
        ),
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
def test_merge(
    inputs: Any,
    expected: Any,
    merge_function: Any,
    input_unchanged: bool,
) -> None:
    configs = [OmegaConf.create(c) for c in inputs]

    if isinstance(expected, (MutableMapping, MutableSequence)) or is_structured_config(
        expected
    ):
        merged = merge_function(*configs)
        assert merged == expected
        if input_unchanged:
            # test input configs are not changed.
            # Note that converting to container without resolving to avoid resolution errors while comparing
            for i in range(len(inputs)):
                input_i = OmegaConf.create(inputs[i])
                orig = OmegaConf.to_container(input_i, resolve=False)
                merged2 = OmegaConf.to_container(configs[i], resolve=False)
                assert orig == merged2
    else:
        with expected:
            merge_function(*configs)


def test_merge_error_retains_type() -> None:
    cfg = OmegaConf.structured(ConcretePlugin)
    with pytest.raises(ValidationError):
        cfg.merge_with({"params": {"foo": "error"}})
    assert OmegaConf.get_type(cfg) == ConcretePlugin


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
def test_primitive_dicts(merge: Any) -> None:
    c1 = {"a": 10}
    c2 = {"b": 20}
    merged = merge(c1, c2)
    assert merged == {"a": 10, "b": 20}


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize("a_, b_, expected", [((1, 2, 3), (4, 5, 6), [4, 5, 6])])
def test_merge_no_eq_verify(
    merge: Any, a_: Tuple[int], b_: Tuple[int], expected: Tuple[int]
) -> None:
    a = OmegaConf.create(a_)
    b = OmegaConf.create(b_)
    c = merge(a, b)
    # verify merge result is expected
    assert expected == c


@pytest.mark.parametrize(
    "c1,c2,expected",
    [({}, {"a": 1, "b": 2}, {"a": 1, "b": 2}), ({"a": 1}, {"b": 2}, {"a": 1, "b": 2})],
)
def test_merge_with(c1: Any, c2: Any, expected: Any) -> None:
    a = OmegaConf.create(c1)
    b = OmegaConf.create(c2)
    a.merge_with(b)
    assert a == expected


@pytest.mark.parametrize(
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


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
def test_3way_dict_merge(merge: Any) -> None:
    c1 = OmegaConf.create("{a: 1, b: 2}")
    c2 = OmegaConf.create("{b: 3}")
    c3 = OmegaConf.create("{a: 2, c: 3}")
    c4 = merge(c1, c2, c3)
    assert {"a": 2, "b": 3, "c": 3} == c4


def test_merge_list_list() -> None:
    a = OmegaConf.create([1, 2, 3])
    b = OmegaConf.create([4, 5, 6])
    a.merge_with(b)
    assert a == b


@pytest.mark.parametrize("merge_func", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
    "base, merge, exception",
    [
        ({}, [], TypeError),
        ([], {}, TypeError),
        ([1, 2, 3], None, ValueError),
        ({"a": 10}, None, ValueError),
        (Package, {"modules": [{"foo": "var"}]}, ConfigKeyError),
    ],
)
def test_merge_error(merge_func: Any, base: Any, merge: Any, exception: Any) -> None:
    base = OmegaConf.create(base)
    merge = None if merge is None else OmegaConf.create(merge)
    with pytest.raises(exception):
        merge_func(base, merge)


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
    "c1, c2",
    [
        pytest.param({"foo": "bar"}, {"zoo": "foo"}, id="dict"),
        pytest.param([1, 2, 3], [4, 5, 6], id="list"),
    ],
)
def test_with_readonly_c1(merge: Any, c1: Any, c2: Any) -> None:
    cfg1 = OmegaConf.create(c1)
    cfg2 = OmegaConf.create(c2)
    OmegaConf.set_readonly(cfg1, True)
    cfg3 = merge(cfg1, cfg2)
    assert OmegaConf.is_readonly(cfg3)


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
    "c1, c2",
    [
        pytest.param({"foo": "bar"}, {"zoo": "foo"}, id="dict"),
        pytest.param([1, 2, 3], [4, 5, 6], id="list"),
    ],
)
def test_with_readonly_c2(merge: Any, c1: Any, c2: Any) -> None:
    cfg1 = OmegaConf.create(c1)
    cfg2 = OmegaConf.create(c1)
    OmegaConf.set_readonly(cfg2, True)
    cfg3 = merge(cfg1, cfg2)
    assert OmegaConf.is_readonly(cfg3)


@pytest.mark.parametrize(
    "c1, c2", [({"foo": "bar"}, {"zoo": "foo"}), ([1, 2, 3], [4, 5, 6])]
)
def test_into_readonly(c1: Any, c2: Any) -> None:
    cfg = OmegaConf.create(c1)
    OmegaConf.set_readonly(cfg, True)
    with pytest.raises(ReadonlyConfigError):
        cfg.merge_with(c2)


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
    "c1, c2, expected",
    [
        (
            {"node": {"foo": "bar"}},
            {"node": {"zoo": "foo"}},
            {"node": {"foo": "bar", "zoo": "foo"}},
        ),
    ],
)
def test_dict_merge_readonly_into_readwrite(
    merge: Any, c1: Any, c2: Any, expected: Any
) -> None:
    c1 = OmegaConf.create(c1)
    c2 = OmegaConf.create(c2)
    OmegaConf.set_readonly(c2.node, True)
    with pytest.raises(ReadonlyConfigError):
        c2.node.foo = 10
    assert OmegaConf.merge(c1, c2) == expected
    c1.merge_with(c2)
    assert c1 == expected


@pytest.mark.parametrize(
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
    # only test OmegaConf.merge. unsafe_merge is failing this test by design
    c3 = OmegaConf.merge(c1, c2)
    assert isinstance(c1, DictConfig)
    assert isinstance(c2, DictConfig)
    assert isinstance(c3, DictConfig)
    assert c1.a._get_parent() is c1
    assert c2.aa._get_parent() is c2
    assert c3.a._get_parent() is c3


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
    "dotlist, expected",
    [([], {}), (["foo=1"], {"foo": 1}), (["foo=1", "bar"], {"foo": 1, "bar": None})],
)
def test_merge_empty_with_dotlist(dotlist: List[str], expected: Dict[str, Any]) -> None:
    c = OmegaConf.create()
    c.merge_with_dotlist(dotlist)
    assert c == expected


@pytest.mark.parametrize("dotlist", ["foo=10", ["foo=1", 10]])
def test_merge_with_dotlist_errors(dotlist: List[str]) -> None:
    c = OmegaConf.create()
    with pytest.raises(ValueError):
        c.merge_with_dotlist(dotlist)


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
def test_merge_allow_objects(merge: Any) -> None:
    iv = IllegalType()
    cfg = OmegaConf.create({"a": 10})
    with pytest.raises(UnsupportedValueType):
        merge(cfg, {"foo": iv})

    cfg._set_flag("allow_objects", True)
    ret = merge(cfg, {"foo": iv})
    assert ret == {"a": 10, "foo": iv}


def test_merge_with_allow_Dataframe() -> None:
    cfg = OmegaConf.create({"a": Dataframe()}, flags={"allow_objects": True})
    ret = OmegaConf.merge({}, cfg)
    assert isinstance(ret.a, Dataframe)


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
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
    merge: Any, dst: Any, other: Any, expected: Any, node: Any
) -> None:
    res = merge(dst, other)
    assert res == expected


@pytest.mark.parametrize("merge", [OmegaConf.merge, OmegaConf.unsafe_merge])
@pytest.mark.parametrize(
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
def test_merge_with_other_as_interpolation(
    merge: Any, dst: Any, other: Any, node: Any
) -> None:
    res = merge(dst, other)
    assert OmegaConf.is_interpolation(res, node)


@pytest.mark.parametrize(
    ("c1", "c2"),
    [
        pytest.param(
            ListConfig(content=[1, 2, 3], element_type=int),
            ["a", "b", "c"],
            id="merge_with_list",
        ),
    ],
)
def test_merge_with_error_not_changing_target(c1: Any, c2: Any) -> Any:
    backup = copy.deepcopy(c1)
    with pytest.raises(ValidationError):
        c1.merge_with(c2)
    assert c1 == backup


@pytest.mark.parametrize(
    "register_func", [OmegaConf.register_resolver, OmegaConf.register_new_resolver]
)
def test_into_custom_resolver_that_throws(
    restore_resolvers: Any, register_func: Any
) -> None:
    def fail() -> None:
        raise ValueError()

    register_func("fail", fail)

    configs = (
        {"d": 20, "i": "${fail:}"},
        {"i": "zzz"},
    )
    expected = {"d": 20, "i": "zzz"}
    assert OmegaConf.merge(*configs) == expected
