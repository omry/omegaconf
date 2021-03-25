from typing import Any

from pytest import mark, param, raises

from omegaconf import ListConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError


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
            {"foo": "${oc.dict.values:{a: 0, b: 1}}"},
            "foo",
            [0, 1],
            id="dict",
        ),
        param(
            {"foo": "${oc.dict.values:${bar}}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            id="dictconfig",
        ),
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            [0, 1],
            id="dictconfig_select",
        ),
        param(
            {
                "foo": "${oc.dict.values:${bar}}",
                "bar": {"x": {"x0": 0, "x1": 1}, "y": {"y0": 0}},
            },
            "foo",
            [{"x0": 0, "x1": 1}, {"y0": 0}],
            id="convert_node_to_list",
        ),
        param(
            {
                "foo": "${oc.dict.values:{key: ${val_ref}}}",
                "val_ref": "value",
            },
            "foo",
            ["value"],
            id="dict_with_interpolated_value",
        ),
    ],
)
def test_dict_values(cfg: Any, key: Any, expected: Any) -> None:

    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected
    assert isinstance(val, ListConfig)
    assert val._parent is cfg


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


@mark.parametrize(
    "cfg",
    [
        param({"x": "${oc.dict.keys:y}", "y": "???"}, id="keys_select_missing"),
        param({"x": "${oc.dict.values:y}", "y": "???"}, id="values_select_missing"),
        param({"x": "${oc.dict.values:y}", "y": {"m": "???"}}, id="missing_value"),
    ],
)
def test_dict_missing(cfg: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(InterpolationResolutionError, match="MissingMandatoryValue"):
        cfg.x
