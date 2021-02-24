import re
from typing import Any, Optional

import pytest
from _pytest.python_api import RaisesContext
from pytest import raises

from omegaconf import MissingMandatoryValue, OmegaConf
from omegaconf._utils import _ensure_container


@pytest.mark.parametrize("struct", [True, False, None])
def test_select_key_from_empty(struct: Optional[bool]) -> None:
    c = OmegaConf.create()
    OmegaConf.set_struct(c, struct)
    assert OmegaConf.select(c, "not_there") is None


@pytest.mark.parametrize(
    "register_func", [OmegaConf.register_resolver, OmegaConf.register_new_resolver]
)
@pytest.mark.parametrize(
    "cfg, key, expected",
    [
        pytest.param({}, "nope", None, id="dict:none"),
        pytest.param({}, "not.there", None, id="dict:none"),
        pytest.param({}, "still.not.there", None, id="dict:none"),
        pytest.param({"c": 1}, "c", 1, id="dict:int"),
        pytest.param({"a": {"v": 1}}, "a.v", 1, id="dict:int"),
        pytest.param({"a": {"v": 1}}, "a", {"v": 1}, id="dict:dict"),
        pytest.param({"missing": "???"}, "missing", None, id="dict:missing"),
        pytest.param([], "0", None, id="list:oob"),
        pytest.param([1, "2"], "0", 1, id="list:int"),
        pytest.param([1, "2"], "1", "2", id="list:str"),
        pytest.param(["???"], "0", None, id="list:missing"),
        pytest.param([1, {"a": 10, "c": ["foo", "bar"]}], "0", 1),
        pytest.param([1, {"a": 10, "c": ["foo", "bar"]}], "1.a", 10),
        pytest.param([1, {"a": 10, "c": ["foo", "bar"]}], "1.b", None),
        pytest.param([1, {"a": 10, "c": ["foo", "bar"]}], "1.c.0", "foo"),
        pytest.param([1, {"a": 10, "c": ["foo", "bar"]}], "1.c.1", "bar"),
        pytest.param([1, 2, 3], "a", raises(TypeError)),
        pytest.param({"a": {"v": 1}}, "", {"a": {"v": 1}}, id="select_root"),
        pytest.param({"a": {"b": 1}, "c": "one=${a.b}"}, "c", "one=1", id="inter"),
        pytest.param({"a": {"b": "one=${n}"}, "n": 1}, "a.b", "one=1", id="inter"),
        pytest.param({"a": {"b": "one=${func:1}"}}, "a.b", "one=_1_", id="resolver"),
    ],
)
def test_select(
    restore_resolvers: Any, cfg: Any, key: Any, expected: Any, register_func: Any
) -> None:
    register_func("func", lambda x: f"_{x}_")
    cfg = _ensure_container(cfg)
    if isinstance(expected, RaisesContext):
        with expected:
            OmegaConf.select(cfg, key)
    else:
        assert OmegaConf.select(cfg, key) == expected


@pytest.mark.parametrize("struct", [False, True])
@pytest.mark.parametrize("default", [10, None])
@pytest.mark.parametrize(
    "cfg, key",
    [
        pytest.param({}, "not_found", id="empty"),
        pytest.param({"missing": "???"}, "missing", id="missing"),
        pytest.param({"inter": "${bad_key}"}, "inter", id="inter_bad_key"),
    ],
)
def test_select_default(
    cfg: Any,
    struct: bool,
    key: Any,
    default: Any,
) -> None:
    cfg = _ensure_container(cfg)
    OmegaConf.set_struct(cfg, struct)
    assert OmegaConf.select(cfg, key, default=default) == default


@pytest.mark.parametrize("struct", [False, True])
@pytest.mark.parametrize("default", [10, None])
@pytest.mark.parametrize(
    "cfg, key",
    [
        pytest.param({"missing": "???"}, "missing", id="missing_dict"),
        pytest.param(["???"], "0", id="missing_list"),
    ],
)
def test_select_default_throw_on_missing(
    cfg: Any,
    struct: bool,
    key: Any,
    default: Any,
) -> None:
    cfg = _ensure_container(cfg)
    OmegaConf.set_struct(cfg, struct)

    # throw on missing still throws if default is provided
    with pytest.raises(MissingMandatoryValue):
        OmegaConf.select(cfg, key, default=default, throw_on_missing=True)


@pytest.mark.parametrize(
    ("cfg", "node_key", "expected"),
    [
        pytest.param({"foo": "${bar}", "bar": 10}, "foo", 10, id="simple"),
        pytest.param({"foo": "${bar}"}, "foo", None, id="no_key"),
        pytest.param({"foo": "${bar}", "bar": "???"}, "foo", None, id="key_missing"),
        pytest.param(
            {"foo": "${bar}", "bar": "${zoo}", "zoo": "???"},
            "foo",
            None,
            id="key_missing_indirect",
        ),
    ],
)
def test_select_invalid_interpolation(cfg: Any, node_key: str, expected: Any) -> None:
    cfg = _ensure_container(cfg)
    resolved = OmegaConf.select(
        cfg,
        node_key,
        throw_on_missing=False,
        throw_on_resolution_failure=False,
    )
    assert resolved == expected


def test_select_from_dict() -> None:
    c = OmegaConf.create({"missing": "???"})
    with pytest.raises(MissingMandatoryValue):
        OmegaConf.select(c, "missing", throw_on_missing=True)
    assert OmegaConf.select(c, "missing", throw_on_missing=False) is None
    assert OmegaConf.select(c, "missing") is None


def test_select_deprecated() -> None:
    c = OmegaConf.create({"foo": "bar"})
    with pytest.warns(
        expected_warning=UserWarning,
        match=re.escape("select() is deprecated, use OmegaConf.select(). (Since 2.0)"),
    ):
        c.select("foo")
