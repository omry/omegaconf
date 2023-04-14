import re
from typing import Any, List

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import (
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from omegaconf.resolvers.oc.dict import _get_and_validate_dict_input
from tests import User, Users


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig",
        ),
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": "${boz}", "boz": {"a": 0, "b": 1}},
            "foo",
            ["a", "b"],
            id="dictconfig_chained_interpolation",
        ),
        param(
            {"a": "${oc.dict.keys:''}", "b": 10},
            "a",
            ["a", "b"],
            id="select_keys_of_root",
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
            {"foo": "${oc.dict.keys_or_values:bar}", "bar": 0},
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
            {"foo": "${oc.dict.keys_or_values:bar}", "bar": DictConfig(None)},
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
    ],
)
def test_get_and_validate_dict_input(
    restore_resolvers: Any, cfg: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver(
        "oc.dict.keys_or_values",
        lambda in_dict, _parent_: _get_and_validate_dict_input(
            in_dict, parent=_parent_, resolver_name="oc.dict.keys_or_values"
        ),
    )
    cfg = OmegaConf.create(cfg)
    with expected:
        cfg[key]


@mark.parametrize(
    ("cfg", "key", "expected_val", "expected_content"),
    [
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            ["${bar.a}", "${bar.b}"],
            id="dictconfig",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
                "bar": {"a": {"x": 0, "y": 1}, "b": {"x": 0}},
            },
            "foo",
            [{"x": 0, "y": 1}, {"x": 0}],
            ["${bar.a}", "${bar.b}"],
            id="dictconfig_deep",
        ),
        param(
            {
                "foo": "${oc.dict.values:bar}",
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
                "foo": "${oc.dict.values:bar}",
                "bar": "${boz}",
                "boz": {"a": 0, "b": 1},
            },
            "foo",
            [0, 1],
            ["${bar.a}", "${bar.b}"],
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
            999,  # referring to the `y` node from the global config
            id="inter_abs",
        ),
        param(
            lambda _parent_: OmegaConf.create({"x": "${.y}", "y": 1}, parent=_parent_),
            0,
            1,
            id="inter_rel",
        ),
        param(lambda: OmegaConf.create({"x": 1}), 0, 1, id="basic_no_parent"),
        param(
            lambda: OmegaConf.create({"x": "${y}", "y": 1}),
            0,
            1,  # no parent => referring to the local `y` node in the generated config
            id="inter_abs_no_parent",
        ),
        param(
            lambda: OmegaConf.create({"x": "${.y}", "y": 1}),
            0,
            1,
            id="inter_rel_no_parent",
        ),
    ],
)
def test_dict_values_dictconfig_resolver_output(
    restore_resolvers: Any, make_resolver: Any, key: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver("make", make_resolver)
    cfg = OmegaConf.create(
        {
            "foo": "${oc.dict.values:bar}",
            "bar": "${make:}",
            "y": 999,
        }
    )

    assert cfg.foo[key] == expected


def test_dict_values_are_typed() -> None:
    cfg = OmegaConf.create(
        {
            "x": "${oc.dict.values: y.name2user}",
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
        param({"x": "${oc.dict.values:y}", "y": {"a": 1}}, [1], id="values_inter"),
        param({"x": "${oc.dict.keys:y}", "y": {"a": 1}}, ["a"], id="keys_inter"),
    ],
)
def test_readonly_parent(cfg: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_readonly(cfg, True)
    assert cfg.x == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        param(
            {"outer": {"x": "${oc.dict.values:.y}", "y": {"a": 1}}},
            [1],
            id="values_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.keys:.y}", "y": {"a": 1}}},
            ["a"],
            id="keys_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.values:..y}"}, "y": {"a": 1}},
            [1],
            id="parent_values_inter",
        ),
        param(
            {"outer": {"x": "${oc.dict.keys:..y}"}, "y": {"a": 1}},
            ["a"],
            id="parent_keys_inter",
        ),
    ],
)
def test_relative_path(cfg: Any, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    assert cfg.outer.x == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        param(
            {"x": "${sum:${oc.dict.values:y}}", "y": {"one": 1, "two": 2}},
            3,
            id="values",
        ),
        param(
            {"x": "${sum:${oc.dict.keys:y}}", "y": {1: "one", 2: "two"}},
            3,
            id="keys",
        ),
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
