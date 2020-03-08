# -*- coding: utf-8 -*-
import re
import tempfile
from enum import Enum
from typing import Any, Dict, List, Union

import pytest

from omegaconf import (
    DictConfig,
    KeyValidationError,
    MissingMandatoryValue,
    OmegaConf,
    UnsupportedValueType,
)
from omegaconf.basecontainer import BaseContainer

from . import IllegalType, StructuredWithMissing, does_not_raise


class Enum1(Enum):
    FOO = 1
    BAR = 2


def test_setattr_deep_value() -> None:
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    c.a.b = 9
    assert {"a": {"b": 9}} == c


def test_setattr_deep_from_empty() -> None:
    c = OmegaConf.create()
    # Unfortunately we can't just do c.a.b = 9 here.
    # The reason is that if c.a is being resolved first and it does not exist, so there
    # is nothing to call .b = 9 on.
    # The alternative is to auto-create fields as they are being accessed, but this is opening
    # a whole new can of worms, and is also breaking map semantics.
    c.a = {}
    c.a.b = 9  # type: ignore
    assert {"a": {"b": 9}} == c


def test_setattr_deep_map() -> None:
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    c.a.b = {"z": 10}
    assert {"a": {"b": {"z": 10}}} == c


def test_getattr() -> None:
    c = OmegaConf.create("a: b")
    assert "b" == c.a


def test_getattr_dict() -> None:
    c = OmegaConf.create("a: {b: 1}")
    assert {"b": 1} == c.a


def test_mandatory_value() -> None:
    c = OmegaConf.create(dict(a="???"))
    with pytest.raises(MissingMandatoryValue, match="a"):
        c.a


def test_nested_dict_mandatory_value() -> None:
    c = OmegaConf.create(dict(a=dict(b="???")))
    with pytest.raises(MissingMandatoryValue):
        c.a.b


def test_mandatory_with_default() -> None:
    c = OmegaConf.create(dict(name="???"))
    assert c.get("name", "default value") == "default value"


def test_subscript_get() -> None:
    c = OmegaConf.create("a: b")
    assert isinstance(c, DictConfig)
    assert "b" == c["a"]


def test_subscript_set() -> None:
    c = OmegaConf.create()
    c["a"] = "b"
    assert {"a": "b"} == c


def test_pretty_dict() -> None:
    c = OmegaConf.create(dict(hello="world", list=[1, 2]))
    expected = """hello: world
list:
- 1
- 2
"""
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_pretty_sort_keys() -> None:
    c = OmegaConf.create({"b": 2, "a": 1})
    # keys are not sorted by default
    assert c.pretty() == "b: 2\na: 1\n"
    c = OmegaConf.create({"b": 2, "a": 1})
    assert c.pretty(sort_keys=True) == "a: 1\nb: 2\n"


def test_pretty_dict_unicode() -> None:
    c = OmegaConf.create(dict(你好="世界", list=[1, 2]))
    expected = """你好: 世界
list:
- 1
- 2
"""
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_default_value() -> None:
    c = OmegaConf.create()
    assert c.missing_key or "a default value" == "a default value"


def test_get_default_value() -> None:
    c = OmegaConf.create()
    assert c.get("missing_key", "a default value") == "a default value"


def test_scientific_notation_float() -> None:
    c = OmegaConf.create("a: 10e-3")
    assert 10e-3 == c.a


def test_dict_get_with_default() -> None:
    s = "{hello: {a : 2}}"
    c = OmegaConf.create(s)
    assert isinstance(c, DictConfig)
    assert c.get("missing", 4) == 4
    assert c.hello.get("missing", 5) == 5


def test_map_expansion() -> None:
    c = OmegaConf.create("{a: 2, b: 10}")
    assert isinstance(c, DictConfig)

    def foo(a: int, b: int) -> int:
        return a + b

    assert 12 == foo(**c)


def test_items() -> None:
    c = OmegaConf.create(dict(a=2, b=10))
    assert sorted([("a", 2), ("b", 10)]) == sorted(list(c.items()))

    items = c.items()
    for x in [("a", 2), ("b", 10)]:
        assert x in items

    items2 = iter(c.items())
    assert next(items2) == ("a", 2)
    assert next(items2) == ("b", 10)
    with pytest.raises(StopIteration):
        next(items2)


def test_items2() -> None:
    c = OmegaConf.create(dict(a=dict(v=1), b=dict(v=1)))
    for k, v in c.items():
        v.v = 2

    assert c.a.v == 2
    assert c.b.v == 2


def test_items_with_interpolation() -> None:
    c = OmegaConf.create(dict(a=2, b="${a}"))
    r = {}
    for k, v in c.items():
        r[k] = v
    assert r["a"] == 2
    assert r["b"] == 2


def test_dict_keys() -> None:
    c = OmegaConf.create("{a: 2, b: 10}")
    assert {"a": 2, "b": 10}.keys() == c.keys()


def test_pickle_get_root() -> None:
    # Test that get_root() is reconstructed correctly for pickle loaded files.
    with tempfile.TemporaryFile() as fp:
        c1 = OmegaConf.create(dict(a=dict(a1=1, a2=2)))

        c2 = OmegaConf.create(dict(b=dict(b1="${a.a1}", b2=4, bb=dict(bb1=3, bb2=4))))
        c3 = OmegaConf.merge(c1, c2)
        assert isinstance(c3, DictConfig)

        import pickle

        pickle.dump(c3, fp)
        fp.flush()
        fp.seek(0)
        loaded_c3 = pickle.load(fp)

        def test(conf: DictConfig) -> None:
            assert conf._get_root() == conf
            assert conf.a._get_root() == conf
            assert conf.b._get_root() == conf
            assert conf.b.bb._get_root() == conf

        assert c3 == loaded_c3
        test(c3)
        test(loaded_c3)


def test_iterate_dictionary() -> None:
    c = OmegaConf.create(dict(a=1, b=2))
    m2 = {}
    for key in c:
        m2[key] = c[key]
    assert m2 == c


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, default_, expected, expectation",
    [
        (dict(a=1, b=2), "a", None, 1, does_not_raise()),
        (dict(a=1, b=2), "not_found", "default", "default", does_not_raise()),
        (dict(a=1, b=2), "not_found", None, None, pytest.raises(KeyError)),
        # Interpolations
        (dict(a="${b}", b=2), "a", None, 2, does_not_raise()),
        (dict(a="???", b=2), "a", None, None, pytest.raises(KeyError)),
        (
            dict(a="${b}", b="???"),
            "a",
            None,
            None,
            pytest.raises(MissingMandatoryValue),
        ),
        # enum key
        ({Enum1.FOO: "bar"}, Enum1.FOO, None, "bar", does_not_raise()),
        ({Enum1.FOO: "bar"}, Enum1.BAR, "default", "default", does_not_raise()),
        ({Enum1.FOO: "bar"}, Enum1.BAR, None, None, pytest.raises(KeyError)),
    ],
)
def test_dict_pop(
    cfg: Dict[Any, Any], key: Any, default_: Any, expected: Any, expectation: Any
) -> None:
    c = OmegaConf.create(cfg)
    with expectation:
        if default_ is not None:
            val = c.pop(key, default_)
        else:
            val = c.pop(key)

        assert val == expected
        assert type(val) == type(expected)


@pytest.mark.parametrize(  # type: ignore
    "conf,key,expected",
    [
        ({"a": 1, "b": {}}, "a", True),
        ({"a": 1, "b": {}}, "b", True),
        ({"a": 1, "b": {}}, "c", False),
        ({"a": 1, "b": "${a}"}, "b", True),
        ({"a": 1, "b": "???"}, "b", False),
        ({"a": 1, "b": "???", "c": "${b}"}, "c", False),
        ({"a": 1, "b": "${not_found}"}, "b", False),
        ({"a": "${unknown_resolver:bar}"}, "a", True),
        ({"a": None, "b": "${a}"}, "b", True),
        ({"a": "cat", "b": "${a}"}, "b", True),
        ({Enum1.FOO: 1, "b": {}}, Enum1.FOO, True),
    ],
)
def test_in_dict(conf: Any, key: str, expected: Any) -> None:
    conf = OmegaConf.create(conf)
    ret = key in conf
    assert ret == expected


def test_get_root() -> None:
    c = OmegaConf.create(dict(a=123, b=dict(bb=456, cc=7)))
    assert c._get_root() == c
    assert c.b._get_root() == c


def test_get_root_of_merged() -> None:
    c1 = OmegaConf.create(dict(a=dict(a1=1, a2=2)))

    c2 = OmegaConf.create(dict(b=dict(b1="???", b2=4, bb=dict(bb1=3, bb2=4))))
    c3 = OmegaConf.merge(c1, c2)

    assert c3._get_root() == c3
    assert c3.a._get_root() == c3
    assert c3.b._get_root() == c3
    assert c3.b.bb._get_root() == c3


def test_dict_config() -> None:
    c = OmegaConf.create(dict())
    assert isinstance(c, DictConfig)


def test_dict_delitem() -> None:
    c = OmegaConf.create(dict(a=10, b=11))
    assert c == dict(a=10, b=11)
    del c["a"]
    assert c == dict(b=11)
    with pytest.raises(KeyError):
        del c["not_found"]


def test_dict_len() -> None:
    c = OmegaConf.create(dict(a=10, b=11))
    assert len(c) == 2


def test_dict_assign_illegal_value() -> None:
    c = OmegaConf.create(dict())
    with pytest.raises(UnsupportedValueType, match=re.escape("key a")):
        c.a = IllegalType()


def test_dict_assign_illegal_value_nested() -> None:
    c = OmegaConf.create(dict(a=dict()))
    with pytest.raises(UnsupportedValueType, match=re.escape("key a.b")):
        c.a.b = IllegalType()


def test_assign_dict_in_dict() -> None:
    c = OmegaConf.create(dict())
    c.foo = dict(foo="bar")
    assert c.foo == dict(foo="bar")
    assert isinstance(c.foo, DictConfig)


@pytest.mark.parametrize(  # type: ignore
    "src",
    [
        dict(a=1, b=2, c=dict(aa=10)),
        [1, 2, 3],
        {"a": 1, "b": 2, "c": {"aa": 10, "lst": [1, 2, 3]}},
    ],
)
def test_to_container(src: Any) -> None:
    c = OmegaConf.create(src)
    result = OmegaConf.to_container(c)
    assert type(result) == type(src)
    assert result == src


def test_pretty_without_resolve() -> None:
    c = OmegaConf.create(dict(a1="${ref}", ref="bar"))
    # without resolve, references are preserved
    c2 = OmegaConf.create(c.pretty(resolve=False))
    assert isinstance(c2, DictConfig)
    assert c2.a1 == "bar"
    c2.ref = "changed"
    assert c2.a1 == "changed"


def test_pretty_with_resolve() -> None:
    c = OmegaConf.create(dict(a1="${ref}", ref="bar"))
    c2 = OmegaConf.create(c.pretty(resolve=True))
    assert isinstance(c2, DictConfig)
    assert c2.a1 == "bar"
    c2.ref = "changed"
    assert c2.a1 == "bar"


def test_instantiate_config_fails() -> None:
    with pytest.raises(TypeError):
        BaseContainer(element_type=Any, parent=None)  # type: ignore


def test_dir() -> None:
    c1 = OmegaConf.create(dict(a=1, b=2, c=3))
    assert dir(c1) == ["a", "b", "c"]
    c2 = OmegaConf.structured(StructuredWithMissing)
    assert dir(c2.get_node("dict")) == []


def test_hash() -> None:
    c1 = OmegaConf.create(dict(a=10))
    c2 = OmegaConf.create(dict(a=10))
    assert hash(c1) == hash(c2)
    c2.a = 20
    assert hash(c1) != hash(c2)


def test_get_with_default_from_struct_not_throwing() -> None:
    c = OmegaConf.create(dict(a=10, b=20))
    OmegaConf.set_struct(c, True)
    assert c.get("z", "default") == "default"


def test_members() -> None:
    # Make sure accessing __members__ does not return None or throw.
    c = OmegaConf.create({"foo": {}})
    with pytest.raises(AttributeError):
        c.__members__


@pytest.mark.parametrize(  # type: ignore
    "in_cfg, mask_keys, expected",
    [
        ({}, [], {}),
        ({"a": 1}, "a", {"a": 1}),
        ({"a": 1}, ["b"], {}),
        ({"a": 1, "b": 2}, "b", {"b": 2}),
        ({"a": 1, "b": 2}, ["a", "b"], {"a": 1, "b": 2}),
    ],
)
def test_masked_copy(
    in_cfg: Dict[str, Any], mask_keys: Union[str, List[str]], expected: Any
) -> None:
    cfg = OmegaConf.create(in_cfg)
    masked = OmegaConf.masked_copy(cfg, keys=mask_keys)
    assert masked == expected


def test_masked_copy_is_deep() -> None:
    cfg = OmegaConf.create({"a": {"b": 1, "c": 2}})
    expected = {"a": {"b": 1, "c": 2}}
    masked = OmegaConf.masked_copy(cfg, keys=["a"])
    assert masked == expected
    cfg.a.b = 2
    assert cfg != expected

    with pytest.raises(ValueError):
        OmegaConf.masked_copy("fail", [])  # type: ignore


def test_creation_with_invalid_key() -> None:
    with pytest.raises(KeyValidationError):
        OmegaConf.create({1: "a"})  # type: ignore


def test_set_with_invalid_key() -> None:
    cfg = OmegaConf.create()
    with pytest.raises(KeyValidationError):
        cfg[1] = "a"  # type: ignore


def test_get_with_invalid_key() -> None:
    cfg = OmegaConf.create()
    with pytest.raises(KeyValidationError):
        cfg[1]  # type: ignore


def test_hasattr() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    assert hasattr(cfg, "foo")
    assert not hasattr(cfg, "buz")


def test_struct_mode_missing_key_getitem() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    with pytest.raises(KeyError):
        cfg.__getitem__("zoo")


def test_struct_mode_missing_key_setitem() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    with pytest.raises(KeyError):
        cfg.__setitem__("zoo", 10)
