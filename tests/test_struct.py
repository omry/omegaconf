import re
from typing import Any, Dict

import pytest

from omegaconf import OmegaConf
from omegaconf.errors import ConfigKeyError


def test_struct_default() -> None:
    c = OmegaConf.create()
    assert c.not_found is None
    assert OmegaConf.is_struct(c) is None


def test_struct_set_on_dict() -> None:
    c = OmegaConf.create({"a": {}})
    OmegaConf.set_struct(c, True)
    # Throwing when it hits foo, so exception key is a.foo and not a.foo.bar
    with pytest.raises(AttributeError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo.bar


def test_struct_set_on_nested_dict() -> None:
    c = OmegaConf.create(dict(a=dict(b=10)))
    OmegaConf.set_struct(c, True)
    with pytest.raises(AttributeError):
        # noinspection PyStatementEffect
        c.foo

    assert "a" in c
    assert c.a.b == 10
    with pytest.raises(AttributeError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo


def test_merge_dotlist_into_struct() -> None:
    c = OmegaConf.create(dict(a=dict(b=10)))
    OmegaConf.set_struct(c, True)
    with pytest.raises(AttributeError, match=re.escape("foo")):
        c.merge_with_dotlist(["foo=1"])


@pytest.mark.parametrize("in_base, in_merged", [(dict(), dict(a=10))])  # type: ignore
def test_merge_config_with_struct(
    in_base: Dict[str, Any], in_merged: Dict[str, Any]
) -> None:
    base = OmegaConf.create(in_base)
    merged = OmegaConf.create(in_merged)
    OmegaConf.set_struct(base, True)
    with pytest.raises(ConfigKeyError):
        OmegaConf.merge(base, merged)


def test_struct_contain_missing() -> None:
    c = OmegaConf.create(dict())
    OmegaConf.set_struct(c, True)
    assert "foo" not in c
