from typing import Any

from pytest import mark, param

from omegaconf import OmegaConf


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
            id="dictconfig",
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
