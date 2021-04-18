from typing import Any

from pytest import mark

from omegaconf import OmegaConf


def test_oc_select_abs() -> None:
    cfg = OmegaConf.create(
        {
            "a0": "${k}",
            "a1": "${oc.select:k}",
            "a2": "${oc.select:k, zzz}",
            "k": 10,
        },
    )
    assert cfg.a0 == cfg.a1 == cfg.a2 == 10


def test_oc_select_missing() -> None:
    cfg = OmegaConf.create(
        {
            "a": "${oc.select:missing}",
            "b": "${oc.select:missing, default value}",
            "missing": "???",
        },
    )
    assert cfg.a is None
    assert cfg.b == "default value"


def test_oc_select_none() -> None:
    cfg = OmegaConf.create(
        {
            "a": "${oc.select:none}",
            "b": "${oc.select:none, default value}",
            "none": None,
        },
    )
    assert cfg.a is None
    assert cfg.b is None


def test_oc_select_relative() -> None:
    cfg = OmegaConf.create(
        {
            "a0": "${.k}",
            "a1": "${oc.select:.k}",
            "a2": "${oc.select:.k, zzz}",
            "k": 10,
        },
    )
    assert cfg.a0 == cfg.a1 == cfg.a2 == 10


def test_oc_nested_select_abs() -> None:
    cfg = OmegaConf.create(
        {
            "nested": {
                "a0": "${k}",
                "a1": "${oc.select:k}",
                "a2": "${oc.select:k,zzz}",
            },
            "k": 10,
        },
    )

    n = cfg.nested
    assert n.a0 == n.a1 == n.a2 == 10


def test_oc_nested_select_relative_same_level() -> None:
    cfg = OmegaConf.create(
        {
            "nested": {
                "a0": "${.k}",
                "a1": "${oc.select:.k}",
                "a2": "${oc.select:.k, zzz}",
                "k": 20,
            },
        },
    )

    n = cfg.nested
    assert n.a0 == n.a1 == n.a2 == 20


def test_oc_nested_select_relative_level_up() -> None:
    cfg = OmegaConf.create(
        {
            "nested": {
                "a0": "${..k}",
                "a1": "${oc.select:..k}",
                "a2": "${oc.select:..k, zzz}",
                "k": 20,
            },
            "k": 10,
        },
    )

    n = cfg.nested
    assert n.a0 == n.a1 == n.a2 == 10


@mark.parametrize(
    ("key", "expected"),
    [
        ("a0", 10),
        ("a1", 11),
        ("a2", None),
        ("a3", 20),
    ],
)
def test_oc_select_using_default(key: str, expected: Any) -> None:
    cfg = OmegaConf.create(
        {
            "a0": "${oc.select:zz, 10}",
            "a1": "${oc.select:.zz, 11}",
            "a2": "${oc.select:zz, null}",
            "a3": "${oc.select:zz, ${value}}",
            "value": 20,
        },
    )
    assert cfg[key] == expected
