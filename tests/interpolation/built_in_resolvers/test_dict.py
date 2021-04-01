import re
from typing import Any, List

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.built_in_resolvers import _get_and_validate_dict_input
from omegaconf.errors import (
    InterpolationKeyError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from tests import User, Users


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"foo": "${oc.dict.keys:{a: 0, b: 1}}"},
            "foo",
            ["a", "b"],
            id="dict",
        ),
        param(
            {"foo": "${oc.dict.keys:${bar}}", "bar": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig_interpolation",
        ),
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig_select",
        ),
    ],
)
def test_dict_keys(cfg: Any, key: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected
    assert isinstance(val, ListConfig)
    assert val._parent is cfg


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"x": "${oc.dict.keys_or_values:y}", "y": "???"},
            "x",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "MissingMandatoryValue raised while resolving interpolation: "
                    "Missing mandatory value: y"
                ),
            ),
            id="select_missing",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:${bar}}"},
            "foo",
            raises(
                InterpolationKeyError,
                match=re.escape("Interpolation key 'bar' not found"),
            ),
            id="interpolation_key_error",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:bar}"},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "ConfigKeyError raised while resolving interpolation: "
                    "Key not found: 'bar'"
                ),
            ),
            id="config_key_error",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:${bar}}", "bar": 0},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.dict.keys_or_values` cannot be applied to objects of type: int"
                ),
            ),
            id="type_error",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:${bar}}", "bar": DictConfig(None)},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.dict.keys_or_values` cannot be applied to objects of type: NoneType"
                ),
            ),
            id="type_error_dictconfig",
        ),
        param(
            {"foo": "${oc.dict.keys_or_values:.bar}", "bar": {"x": 0}},
            "foo",
            raises(
                InterpolationResolutionError,
                match=re.escape("NotImplementedError"),
            ),
            id="relative_with_select",
        ),
    ],
)
def test_get_and_validate_dict_input(
    restore_resolvers: Any, cfg: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver(
        "oc.dict.keys_or_values",
        lambda in_dict, _root_: _get_and_validate_dict_input(
            in_dict, root=_root_, resolver_name="oc.dict.keys_or_values"
        ),
    )
    cfg = OmegaConf.create(cfg)
    with expected:
        cfg[key]


@mark.parametrize(
    ("cfg", "key", "expected_val", "expected_content"),
    [
        param(
            {"foo": "${oc.dict.values:{a: 0, b: 1}}"},
            "foo",
            [0, 1],
            [0, 1],
            id="dict",
        ),
        param(
            {"foo": "${oc.dict.values:${bar}}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            ["${bar.a}", "${bar.b}"],
            id="dictconfig",
        ),
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            ["${bar.a}", "${bar.b}"],
            id="dictconfig_select",
        ),
        param(
            {
                "foo": "${oc.dict.values:${bar}}",
                "bar": {"x": {"x0": 0, "x1": 1}, "y": {"y0": 0}},
            },
            "foo",
            [{"x0": 0, "x1": 1}, {"y0": 0}],
            ["${bar.x}", "${bar.y}"],
            id="convert_node_to_list",
        ),
        param(
            {
                "foo": "${oc.dict.values:{key: ${val_ref}}}",
                "val_ref": "value",
            },
            "foo",
            ["value"],
            ["value"],
            id="dict_with_interpolated_value",
        ),
        param(
            {
                "foo": "${oc.dict.values:${bar}}",
                "bar": {"key": "${val_ref}"},
                "val_ref": "value",
            },
            "foo",
            ["value"],
            ["${bar.key}"],
            id="dictconfig_with_interpolated_value",
        ),
        param(
            {
                "foo": "${oc.dict.values:${bar}}",
                "bar": "${boz}",
                "boz": {"a": 0, "b": 1},
            },
            "foo",
            [0, 1],
            ["${boz.a}", "${boz.b}"],
            id="dictconfig_chained_interpolation",
        ),
    ],
)
def test_dict_values(
    cfg: Any, key: Any, expected_val: Any, expected_content: Any
) -> None:

    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected_val
    assert isinstance(val, ListConfig)
    assert val._parent is cfg
    content = val._content
    assert content == expected_content


def test_dict_values_with_missing_value() -> None:
    cfg = OmegaConf.create({"foo": "${oc.dict.values:bar}", "bar": {"missing": "???"}})
    foo = cfg.foo
    with raises(InterpolationToMissingValueError):
        foo[0]
    cfg.bar.missing = 1
    assert foo[0] == 1


@mark.parametrize(
    ("make_resolver", "key", "expected"),
    [
        param(
            lambda _parent_: OmegaConf.create({"x": 1}, parent=_parent_),
            0,
            1,
            id="basic",
        ),
        param(
            lambda _parent_: OmegaConf.create({"x": "${y}", "y": 1}, parent=_parent_),
            0,
            999,  # now referring to the `y` node from the global config
            id="inter_abs",
        ),
        param(
            lambda _parent_: OmegaConf.create({"x": "${.y}", "y": 1}, parent=_parent_),
            0,
            1,
            id="inter_rel",
        ),
    ],
)
def test_dict_values_dictconfig_resolver_output(
    restore_resolvers: Any, make_resolver: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver("make", make_resolver)
    cfg = OmegaConf.create(
        {
            "foo": "${oc.dict.values:${make:}}",
            "bar": "${oc.dict.values:${boz}}",
            "boz": "${make:}",
            "y": 999,
        }
    )

    # Directly using the resolver output without an intermediate node to store the
    # result is not currently supported.
    with raises(InterpolationResolutionError, match=re.escape("NotImplementedError")):
        cfg.foo

    assert cfg.bar[key] == expected


@mark.parametrize(
    ("make_resolver", "key", "expected"),
    [
        param(lambda: OmegaConf.create({"x": 1}), 0, 1, id="basic"),
        param(lambda: OmegaConf.create({"x": "${y}", "y": 1}), 0, 1, id="inter_abs"),
        param(lambda: OmegaConf.create({"x": "${.y}", "y": 1}), 0, 1, id="inter_rel"),
    ],
)
def test_dict_values_dictconfig_resolver_output_no_parent(
    restore_resolvers: Any, make_resolver: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver("make", make_resolver)
    cfg = OmegaConf.create(
        {
            "bar": "${oc.dict.values:${boz}}",
            "boz": "${make:}",
            "y": 999,
        }
    )

    # Using transient nodes whose parent is not set is not currently supported.
    with raises(InterpolationResolutionError, match=re.escape("NotImplementedError")):
        cfg.bar


@mark.parametrize(
    ("make_resolver", "expected_value", "expected_content"),
    [
        param(
            lambda _parent_: OmegaConf.create({"a": 0, "b": 1}, parent=_parent_),
            [0, 1],
            ["${y.a}", "${y.b}"],
            id="dictconfig_with_parent",
        ),
        param(
            lambda: {"a": 0, "b": 1},
            [0, 1],
            ["${y.a}", "${y.b}"],
            id="plain_dict",
        ),
    ],
)
def test_dict_values_transient_interpolation(
    restore_resolvers: Any,
    make_resolver: Any,
    expected_value: Any,
    expected_content: Any,
) -> None:
    OmegaConf.register_new_resolver("make", make_resolver)
    cfg = OmegaConf.create({"x": "${oc.dict.values:y}", "y": "${make:}"})
    assert cfg.x == expected_value
    assert cfg.x._content == expected_content


def test_dict_values_are_typed() -> None:
    cfg = OmegaConf.create(
        {
            "x": "${oc.dict.values:${y.name2user}}",
            "y": Users(
                name2user={
                    "john": User(name="john", age=30),
                    "jane": User(name="jane", age=33),
                }
            ),
        }
    )
    x = cfg.x
    assert x._metadata.ref_type == List[User]
    assert x._metadata.element_type == User


@mark.parametrize(
    ("cfg", "expected"),
    [
        param({"x": "${oc.dict.values:{a: 1, b: 2}}"}, [1, 2], id="values_inline"),
        param({"x": "${oc.dict.keys:{a: 1, b: 2}}"}, ["a", "b"], id="keys_inline"),
        param({"x": "${oc.dict.values:y}", "y": {"a": 1}}, [1], id="values_inter"),
        param({"x": "${oc.dict.keys:y}", "y": {"a": 1}}, ["a"], id="keys_inter"),
    ],
)
def test_readonly_parent(cfg: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    cfg._set_flag("readonly", True)
    assert cfg.x == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        param({"x": "${sum:${oc.dict.values:{one: 1, two: 2}}}"}, 3, id="values"),
        param({"x": "${sum:${oc.dict.keys:{1: one, 2: two}}}"}, 3, id="keys"),
    ],
)
def test_nested_oc_dict(restore_resolvers: Any, cfg: Any, expected: Any) -> None:
    OmegaConf.register_new_resolver("sum", sum)
    cfg = OmegaConf.create(cfg)
    assert cfg.x == expected


@mark.parametrize(
    "cfg",
    [
        param({"x": "${oc.dict.keys:[]}"}, id="list"),
        param({"x": "${oc.dict.keys:${bool}}", "bool": True}, id="bool_interpolation"),
        param({"x": "${oc.dict.keys:int}", "int": 0}, id="int_select"),
    ],
)
def test_dict_keys_invalid_type(cfg: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(InterpolationResolutionError, match="TypeError"):
        cfg.x


@mark.parametrize(
    "cfg",
    [
        param({"x": "${oc.dict.values:[]}"}, id="list"),
        param(
            {"x": "${oc.dict.values:${bool}}", "bool": True}, id="bool_interpolation"
        ),
        param({"x": "${oc.dict.values:int}", "int": 0}, id="int_select"),
    ],
)
def test_dict_values_invalid_type(cfg: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(InterpolationResolutionError, match="TypeError"):
        cfg.x


def test_dict_values_of_root(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("root", lambda _root_: _root_)
    cfg = OmegaConf.create({"x": {"a": "${oc.dict.values:${root:}}"}, "y": 0})
    a = cfg.x.a
    assert a._content == ["${x}", "${y}"]
    assert a[1] == 0
    # We can recurse indefinitely within the first value if we fancy it.
    assert cfg.x.a[0].a[0].a[1] == 0
