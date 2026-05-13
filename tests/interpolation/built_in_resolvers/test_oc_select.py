from dataclasses import dataclass
from typing import Any

from pytest import mark, raises

from omegaconf import SI, OmegaConf
from omegaconf.errors import InterpolationKeyError


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


def test_oc_select_default_for_relative_key_above_root() -> None:
    cfg = OmegaConf.create({"a": "${oc.select:..member, 5}"})
    assert cfg.a == 5


def test_oc_select_default_for_relative_key_above_root_in_structured_config() -> None:
    @dataclass
    class Config:
        a: int = SI("${oc.select:..member, 5}")

    cfg = OmegaConf.structured(Config)
    assert cfg.a == 5


def test_oc_select_default_in_dynamic_interpolation() -> None:
    cfg = OmegaConf.create(
        {
            "fallback": 123,
            "ok": "${${oc.select:..member, fallback}}",
            "bad": "${${oc.select:..member, nowhere}}",
        }
    )

    assert cfg.ok == 123
    with raises(InterpolationKeyError):
        cfg.bad


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
