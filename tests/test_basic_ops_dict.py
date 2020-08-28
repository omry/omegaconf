# -*- coding: utf-8 -*-
import re
import tempfile
from typing import Any, Dict, List, Optional, Union

import pytest

from omegaconf import (
    DictConfig,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    UnsupportedValueType,
    ValidationError,
    _utils,
    open_dict,
)
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import ConfigKeyError, ConfigTypeError, KeyValidationError

from . import (
    ConcretePlugin,
    Enum1,
    IllegalType,
    Plugin,
    StructuredWithMissing,
    User,
    does_not_raise,
)


def test_setattr_deep_value() -> None:
    c = OmegaConf.create({"a": {"b": {"c": 1}}})
    c.a.b = 9
    assert {"a": {"b": 9}} == c


def test_setattr_deep_from_empty() -> None:
    c = OmegaConf.create()
    # Unfortunately we can't just do c.a.b = 9 here.
    # The reason is that if c.a is being accessed first and it does not exist, so there
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
    assert isinstance(c, DictConfig)
    assert "b" == c.a


def test_getattr_dict() -> None:
    c = OmegaConf.create("a: {b: 1}")
    assert isinstance(c, DictConfig)
    assert {"b": 1} == c.a


def test_mandatory_value() -> None:
    c = OmegaConf.create({"a": "???"})
    with pytest.raises(MissingMandatoryValue, match="a"):
        c.a


def test_nested_dict_mandatory_value() -> None:
    c = OmegaConf.create(dict(a=dict(b="???")))
    with pytest.raises(MissingMandatoryValue):
        c.a.b


def test_subscript_get() -> None:
    c = OmegaConf.create("a: b")
    assert isinstance(c, DictConfig)
    assert "b" == c["a"]


def test_subscript_set() -> None:
    c = OmegaConf.create()
    c["a"] = "b"
    assert {"a": "b"} == c


def test_default_value() -> None:
    c = OmegaConf.create()
    assert c.missing_key or "a default value" == "a default value"


def test_get_default_value() -> None:
    c = OmegaConf.create()
    assert c.get("missing_key", "a default value") == "a default value"


def test_scientific_notation_float() -> None:
    c = OmegaConf.create("a: 10e-3")
    assert isinstance(c, DictConfig)
    assert 10e-3 == c.a


@pytest.mark.parametrize("struct", [None, True, False])  # type: ignore
@pytest.mark.parametrize("default_val", [4, True, False, None])  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "d,select,key",
    [
        ({"hello": {"a": 2}}, "", "missing"),
        ({"hello": {"a": 2}}, "hello", "missing"),
        ({"hello": "???"}, "", "hello"),
        ({"hello": "${foo}", "foo": "???"}, "", "hello"),
        ({"hello": None}, "", "hello"),
        ({"hello": "${foo}"}, "", "hello"),
        ({"hello": "${foo}", "foo": "???"}, "", "hello"),
        ({"hello": DictConfig(is_optional=True, content=None)}, "", "hello"),
        ({"hello": DictConfig(content="???")}, "", "hello"),
        ({"hello": DictConfig(content="${foo}")}, "", "hello"),
        ({"hello": ListConfig(is_optional=True, content=None)}, "", "hello"),
        ({"hello": ListConfig(content="???")}, "", "hello"),
    ],
)
def test_dict_get_with_default(
    d: Any, select: Any, key: Any, default_val: Any, struct: Any
) -> None:
    c = OmegaConf.create(d)
    c = OmegaConf.select(c, select)
    OmegaConf.set_struct(c, struct)
    assert c.get(key, default_val) == default_val


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
    assert isinstance(c, DictConfig)
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
    c = OmegaConf.create({"a": 1, "b": 2})
    m2 = {}
    for key in c:
        m2[key] = c[key]
    assert m2 == c


def test_iterate_dict_with_interpolation() -> None:
    c = OmegaConf.create({"a": "${b}", "b": 2})
    expected = [("a", 2), ("b", 2)]
    i = 0
    for k, v in c.items():
        assert k == expected[i][0]
        assert v == expected[i][1]
        i = i + 1


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, default_, expected",
    [
        pytest.param({"a": 1, "b": 2}, "a", "__NO_DEFAULT__", 1, id="no_default"),
        pytest.param({"a": 1, "b": 2}, "not_found", None, None, id="none_default"),
        pytest.param(
            {"a": 1, "b": 2}, "not_found", "default", "default", id="with_default"
        ),
        # Interpolations
        pytest.param(
            {"a": "${b}", "b": 2}, "a", "__NO_DEFAULT__", 2, id="interpolation"
        ),
        pytest.param(
            {"a": "${b}"}, "a", "default", "default", id="interpolation_with_default"
        ),
        # enum key
        pytest.param(
            {Enum1.FOO: "bar"},
            Enum1.FOO,
            "__NO_DEFAULT__",
            "bar",
            id="enum_key_no_default",
        ),
        pytest.param(
            {Enum1.FOO: "bar"}, Enum1.BAR, None, None, id="enum_key_with_none_default"
        ),
        pytest.param(
            {Enum1.FOO: "bar"},
            Enum1.BAR,
            "default",
            "default",
            id="enum_key_with_default",
        ),
    ],
)
def test_dict_pop(cfg: Dict[Any, Any], key: Any, default_: Any, expected: Any) -> None:
    c = OmegaConf.create(cfg)

    if default_ != "__NO_DEFAULT__":
        val = c.pop(key, default_)
    else:
        val = c.pop(key)

    assert val == expected
    assert type(val) == type(expected)


def test_dict_struct_mode_pop() -> None:
    cfg = OmegaConf.create({"name": "Bond", "age": 7})
    cfg._set_flag("struct", True)
    with pytest.raises(ConfigTypeError):
        cfg.pop("name")

    with pytest.raises(ConfigTypeError):
        cfg.pop("bar")

    with pytest.raises(ConfigTypeError):
        cfg.pop("bar", "not even with default")


def test_dict_structured_mode_pop() -> None:
    cfg = OmegaConf.create({"user": User(name="Bond")})
    with pytest.raises(ConfigTypeError):
        cfg.user.pop("name")

    with pytest.raises(ConfigTypeError):
        cfg.user.pop("bar")

    with pytest.raises(ConfigTypeError):
        cfg.user.pop("bar", "not even with default")

    # Unlocking the top level node is not enough.
    with pytest.raises(ConfigTypeError):
        with open_dict(cfg):
            cfg.user.pop("name")

    # You need to unlock the specified structured node to pop a field from it.
    with open_dict(cfg.user):
        cfg.user.pop("name")
    assert "name" not in cfg.user


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, expectation",
    [
        ({"a": 1, "b": 2}, "not_found", pytest.raises(KeyError)),
        # Interpolations
        ({"a": "???", "b": 2}, "a", pytest.raises(MissingMandatoryValue)),
        ({"a": "${b}", "b": "???"}, "a", pytest.raises(MissingMandatoryValue)),
        # enum key
        ({Enum1.FOO: "bar"}, Enum1.BAR, pytest.raises(KeyError)),
    ],
)
def test_dict_pop_error(cfg: Dict[Any, Any], key: Any, expectation: Any) -> None:
    c = OmegaConf.create(cfg)
    with expectation:
        c.pop(key)
    assert c == cfg


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
    assert (key in conf) == expected


def test_get_root() -> None:
    c = OmegaConf.create(dict(a=123, b=dict(bb=456, cc=7)))
    assert c._get_root() == c
    assert c.b._get_root() == c


def test_get_root_of_merged() -> None:
    c1 = OmegaConf.create(dict(a=dict(a1=1, a2=2)))

    c2 = OmegaConf.create(dict(b=dict(b1="???", b2=4, bb=dict(bb1=3, bb2=4))))
    c3 = OmegaConf.merge(c1, c2)
    assert isinstance(c3, DictConfig)

    assert c3._get_root() == c3
    assert c3.a._get_root() == c3
    assert c3.b._get_root() == c3
    assert c3.b.bb._get_root() == c3


def test_dict_config() -> None:
    c = OmegaConf.create(dict())
    assert isinstance(c, DictConfig)


def test_dict_delitem() -> None:
    src = {"a": 10, "b": 11}
    c = OmegaConf.create(src)
    assert c == src
    del c["a"]
    assert c == {"b": 11}
    with pytest.raises(KeyError):
        del c["not_found"]


def test_dict_struct_delitem() -> None:
    src = {"a": 10, "b": 11}
    c = OmegaConf.create(src)
    OmegaConf.set_struct(c, True)
    with pytest.raises(ConfigTypeError):
        del c["a"]
    with open_dict(c):
        del c["a"]
    assert "a" not in c


def test_dict_structured_delitem() -> None:
    c = OmegaConf.structured(User(name="Bond"))
    with pytest.raises(ConfigTypeError):
        del c["name"]

    with open_dict(c):
        del c["name"]
    assert "name" not in c


def test_dict_nested_structured_delitem() -> None:
    c = OmegaConf.create({"user": User(name="Bond")})
    with pytest.raises(ConfigTypeError):
        del c.user["name"]

    # Unlocking the top level node is not enough.
    with pytest.raises(ConfigTypeError):
        with open_dict(c):
            del c.user["name"]

    # You need to unlock the specified structured node to delete a field from it.
    with open_dict(c.user):
        del c.user["name"]
    assert "name" not in c.user


@pytest.mark.parametrize(  # type: ignore
    "d, expected", [({}, 0), ({"a": 10, "b": 11}, 2)]
)
def test_dict_len(d: Any, expected: Any) -> None:
    c = OmegaConf.create(d)
    assert len(c) == expected


def test_dict_assign_illegal_value() -> None:
    c = OmegaConf.create()
    with pytest.raises(UnsupportedValueType, match=re.escape("key: a")):
        c.a = IllegalType()


def test_dict_assign_illegal_value_nested() -> None:
    c = OmegaConf.create({"a": {}})
    with pytest.raises(UnsupportedValueType, match=re.escape("key: a.b")):
        c.a.b = IllegalType()


def test_assign_dict_in_dict() -> None:
    c = OmegaConf.create({})
    c.foo = {"foo": "bar"}
    assert c.foo == {"foo": "bar"}
    assert isinstance(c.foo, DictConfig)


def test_instantiate_config_fails() -> None:
    with pytest.raises(TypeError):
        BaseContainer()  # type: ignore


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, expected",
    [
        ({"a": 1, "b": 2, "c": 3}, None, ["a", "b", "c"]),
        ({"a": {}}, "a", []),
        (StructuredWithMissing, "dict", []),
    ],
)
def test_dir(cfg: Any, key: Any, expected: Any) -> None:
    c = OmegaConf.create(cfg)
    if key is None:
        assert dir(c) == expected
    else:
        assert dir(c._get_node(key)) == expected


def test_hash() -> None:
    c1 = OmegaConf.create(dict(a=10))
    c2 = OmegaConf.create(dict(a=10))
    assert hash(c1) == hash(c2)
    c2.a = 20
    assert hash(c1) != hash(c2)


@pytest.mark.parametrize("default", ["default", 0, None])  # type: ignore
def test_get_with_default_from_struct_not_throwing(default: Any) -> None:
    c = OmegaConf.create({"a": 10, "b": 20})
    OmegaConf.set_struct(c, True)
    assert c.get("z", default) == default


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


def test_get_type() -> None:

    cfg = OmegaConf.structured(User)
    assert OmegaConf.get_type(cfg) == User

    cfg = OmegaConf.structured(User(name="bond"))
    assert OmegaConf.get_type(cfg) == User

    cfg = OmegaConf.create({"user": User, "inter": "${user}"})
    assert OmegaConf.get_type(cfg.user) == User
    assert OmegaConf.get_type(cfg.inter) == User


@pytest.mark.parametrize(  # type: ignore
    "cfg, expected_ref_type",
    [
        (
            OmegaConf.create(
                {"plugin": DictConfig(ref_type=Plugin, content=ConcretePlugin)}
            ),
            Optional[Plugin],
        ),
        (
            OmegaConf.create(
                {
                    "plugin": DictConfig(
                        ref_type=Plugin, content=ConcretePlugin, is_optional=False
                    )
                }
            ),
            Plugin,
        ),
    ],
)
def test_get_ref_type(cfg: Any, expected_ref_type: Any) -> None:
    assert _utils.get_ref_type(cfg.plugin) == expected_ref_type


def test_get_ref_type_with_conflict() -> None:
    cfg = OmegaConf.create(
        {"user": User, "inter": DictConfig(ref_type=Plugin, content="${user}")}
    )

    assert OmegaConf.get_type(cfg.user) == User
    assert _utils.get_ref_type(cfg.user) == Optional[User]

    # Interpolation inherits both type and ref type from the target
    assert OmegaConf.get_type(cfg.inter) == User
    assert _utils.get_ref_type(cfg.inter) == Optional[User]


def test_is_missing() -> None:
    cfg = OmegaConf.create(
        {
            "missing_node": DictConfig(content="???"),
            "foo": "???",
            "inter": "${foo}",
            "str_inter": "zoo_${foo}",
            "missing_node_inter": "${missing_node}",
        }
    )
    assert cfg._get_node("foo")._is_missing()  # type:ignore
    assert cfg._get_node("inter")._is_missing()  # type:ignore
    assert cfg._get_node("str_inter")._is_missing()  # type:ignore
    assert cfg._get_node("missing_node")._is_missing()  # type:ignore
    assert cfg._get_node("missing_node_inter")._is_missing()  # type:ignore


@pytest.mark.parametrize("ref_type", [None, Any])  # type: ignore
@pytest.mark.parametrize("assign", [None, {}, {"foo": "bar"}, [1, 2, 3]])  # type: ignore
def test_assign_to_reftype_none_or_any(ref_type: Any, assign: Any) -> None:
    cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content={})})
    cfg.foo = assign
    assert cfg.foo == assign


@pytest.mark.parametrize(  # type: ignore
    "ref_type,values,assign,expectation",
    [
        (Plugin, [None, "???", Plugin], None, does_not_raise),
        (Plugin, [None, "???", Plugin], Plugin, does_not_raise),
        (Plugin, [None, "???", Plugin], Plugin(), does_not_raise),
        (Plugin, [None, "???", Plugin], ConcretePlugin, does_not_raise),
        (Plugin, [None, "???", Plugin], ConcretePlugin(), does_not_raise),
        (Plugin, [None, "???", Plugin], 10, lambda: pytest.raises(ValidationError)),
        (ConcretePlugin, [None, "???", ConcretePlugin], None, does_not_raise),
        (
            ConcretePlugin,
            [None, "???", ConcretePlugin],
            Plugin,
            lambda: pytest.raises(ValidationError),
        ),
        (
            ConcretePlugin,
            [None, "???", ConcretePlugin],
            Plugin(),
            lambda: pytest.raises(ValidationError),
        ),
        (
            ConcretePlugin,
            [None, "???", ConcretePlugin],
            ConcretePlugin,
            does_not_raise,
        ),
        (
            ConcretePlugin,
            [None, "???", ConcretePlugin],
            ConcretePlugin(),
            does_not_raise,
        ),
    ],
)
def test_assign_to_reftype_plugin(
    ref_type: Any, values: List[Any], assign: Any, expectation: Any
) -> None:
    for value in values:
        cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content=value)})
        with expectation():
            assert _utils.get_ref_type(cfg, "foo") == Optional[ref_type]
            cfg.foo = assign
            assert cfg.foo == assign
            # validate assignment does not change ref type.
            assert _utils.get_ref_type(cfg, "foo") == Optional[ref_type]

        if value is not None:
            cfg = OmegaConf.create(
                {"foo": DictConfig(ref_type=ref_type, content=value)}
            )
            with expectation():
                cfg2 = OmegaConf.merge(cfg, {"foo": assign})
                assert isinstance(cfg2, DictConfig)
                assert cfg2.foo == assign


def test_setdefault() -> None:
    cfg = OmegaConf.create({})
    assert cfg.setdefault("foo", 10) == 10
    assert cfg["foo"] == 10
    assert cfg.setdefault("foo", 20) == 10
    assert cfg["foo"] == 10

    cfg = OmegaConf.create({})
    OmegaConf.set_struct(cfg, True)
    with pytest.raises(ConfigKeyError):
        assert cfg.setdefault("foo", 10) == 10
    assert cfg == {}
    with open_dict(cfg):
        assert cfg.setdefault("foo", 10) == 10

    assert cfg.setdefault("foo", 20) == 10
    assert cfg["foo"] == 10

    assert cfg["foo"] == 10
