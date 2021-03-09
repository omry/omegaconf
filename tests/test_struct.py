import re
from typing import Any, Dict

from pytest import mark, raises

from omegaconf import OmegaConf
from omegaconf.errors import ConfigKeyError


def test_struct_default() -> None:
    c = OmegaConf.create()
    assert OmegaConf.is_struct(c) is None


def test_struct_set_on_dict() -> None:
    c = OmegaConf.create({"a": {}})
    OmegaConf.set_struct(c, True)
    # Throwing when it hits foo, so exception key is a.foo and not a.foo.bar
    with raises(AttributeError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo.bar


def test_struct_set_on_nested_dict() -> None:
    c = OmegaConf.create({"a": {"b": 10}})
    OmegaConf.set_struct(c, True)
    with raises(AttributeError):
        # noinspection PyStatementEffect
        c.foo

    assert "a" in c
    assert c.a.b == 10
    with raises(AttributeError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo


def test_merge_dotlist_into_struct() -> None:
    c = OmegaConf.create({"a": {"b": 10}})
    OmegaConf.set_struct(c, True)
    with raises(AttributeError, match=re.escape("foo")):
        c.merge_with_dotlist(["foo=1"])


@mark.parametrize("in_base, in_merged", [({}, {"a": 10})])
def test_merge_config_with_struct(
    in_base: Dict[str, Any], in_merged: Dict[str, Any]
) -> None:
    base = OmegaConf.create(in_base)
    merged = OmegaConf.create(in_merged)
    OmegaConf.set_struct(base, True)
    with raises(ConfigKeyError):
        OmegaConf.merge(base, merged)


def test_struct_contain_missing() -> None:
    c = OmegaConf.create()
    OmegaConf.set_struct(c, True)
    assert "foo" not in c


@mark.parametrize("cfg", [{}, OmegaConf.create({}, flags={"struct": True})])
def test_struct_dict_get(cfg: Any) -> None:
    assert cfg.get("z") is None


def test_struct_dict_assign() -> None:
    cfg = OmegaConf.create({"a": {}})
    OmegaConf.set_struct(cfg, True)
    cfg.a = {"b": 10}
    assert cfg.a == {"b": 10}
