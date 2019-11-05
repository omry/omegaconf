import re

import pytest

from omegaconf import OmegaConf


def test_struct_default():
    c = OmegaConf.create()
    assert OmegaConf.is_struct(c) is False
    assert c.not_found is None


def test_struct_set_on_dict():
    c = OmegaConf.create(dict(a=dict()))
    OmegaConf.set_struct(c, True)
    # Throwing when it hits foo, so exception key is a.foo and not a.foo.bar
    with pytest.raises(KeyError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo.bar


def test_struct_set_on_nested_dict():
    c = OmegaConf.create(dict(a=dict(b=10)))
    OmegaConf.set_struct(c, True)
    with pytest.raises(KeyError):
        # noinspection PyStatementEffect
        c.foo

    assert "a" in c
    assert c.a.b == 10
    with pytest.raises(KeyError, match=re.escape("a.foo")):
        # noinspection PyStatementEffect
        c.a.foo


def test_merge_dotlist_into_struct():
    c = OmegaConf.create(dict(a=dict(b=10)))
    OmegaConf.set_struct(c, True)
    with pytest.raises(KeyError, match=re.escape("foo")):
        c.merge_with_dotlist(["foo=1"])


@pytest.mark.parametrize("base, merged", [(dict(), dict(a=10))])
def test_merge_config_with_struct(base, merged):
    base = OmegaConf.create(base)
    merged = OmegaConf.create(merged)
    OmegaConf.set_struct(base, True)
    with pytest.raises(KeyError):
        OmegaConf.merge(base, merged)
