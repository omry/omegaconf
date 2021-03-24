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
            OmegaConf.create(["a", "b"]),
            id="dict",
        ),
        param(
            {"foo": "${oc.dict.keys:${bar}}", "bar": {"a": 0, "b": 1}},
            "foo",
            OmegaConf.create(["a", "b"]),
            id="dictconfig_interpolation",
        ),
        param(
            {"foo": "${oc.dict.keys:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            OmegaConf.create(["a", "b"]),
            id="dictconfig_select",
        ),
        param(
            {"foo": "${sum:${oc.dict.keys:{1: one, 2: two}}}"},
            "foo",
            3,
            id="nested",
        ),
    ],
)
def test_dict_keys(restore_resolvers: Any, cfg: Any, key: Any, expected: Any) -> None:
    OmegaConf.register_new_resolver("sum", lambda x: sum(x))

    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected
    assert type(val) is type(expected)

    if isinstance(val, ListConfig):
        assert val._parent is cfg


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param(
            {"foo": "${oc.dict.values:{a: 0, b: 1}}"},
            "foo",
            OmegaConf.create([0, 1]),
            id="dict",
        ),
        param(
            {"foo": "${oc.dict.values:${bar}}", "bar": {"a": 0, "b": 1}},
            "foo",
            OmegaConf.create([0, 1]),
            id="dictconfig",
        ),
        param(
            {"foo": "${oc.dict.values:bar}", "bar": {"a": 0, "b": 1}},
            "foo",
            OmegaConf.create([0, 1]),
            id="dictconfig_select",
        ),
        param(
            {"foo": "${sum:${oc.dict.values:{one: 1, two: 2}}}"},
            "foo",
            3,
            id="nested",
        ),
        param(
            {
                "foo": "${oc.dict.values:${bar}}",
                "bar": {"x": {"x0": 0, "x1": 1}, "y": {"y0": 0}},
            },
            "foo",
            OmegaConf.create([{"x0": 0, "x1": 1}, {"y0": 0}]),
            id="convert_node_to_list",
        ),
        param(
            {
                "foo": "${oc.dict.values:{key: ${val_ref}}}",
                "val_ref": "value",
            },
            "foo",
            OmegaConf.create(["value"]),
            id="dict_with_interpolated_value",
        ),
    ],
)
def test_dict_values(restore_resolvers: Any, cfg: Any, key: Any, expected: Any) -> None:
    OmegaConf.register_new_resolver("sum", lambda x: sum(x))

    cfg = OmegaConf.create(cfg)
    val = cfg[key]
    assert val == expected
    assert type(val) is type(expected)

    if isinstance(val, ListConfig):
        assert val._parent is cfg


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
