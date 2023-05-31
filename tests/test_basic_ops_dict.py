# -*- coding: utf-8 -*-
import copy
import re
import tempfile
from typing import Any, Dict, List, Optional, Union

from pytest import mark, param, raises

from omegaconf import (
    MISSING,
    AnyNode,
    DictConfig,
    DictKeyType,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    UnsupportedValueType,
    ValidationError,
    _utils,
    flag_override,
    open_dict,
)
from omegaconf._utils import _ensure_container
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import (
    ConfigAttributeError,
    ConfigKeyError,
    ConfigTypeError,
    InterpolationKeyError,
    InterpolationToMissingValueError,
    KeyValidationError,
)
from tests import (
    ConcretePlugin,
    Enum1,
    IllegalType,
    Plugin,
    StructuredWithMissing,
    SubscriptedDict,
    User,
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


def test_setattr_dict_nested() -> None:
    c = OmegaConf.create({"a": {"b": {"c": 1}}})
    c.a.b = {"z": 10}
    assert c == {"a": {"b": {"z": 10}}}


def test_getattr() -> None:
    c = OmegaConf.create("a: b")
    assert isinstance(c, DictConfig)
    assert "b" == c.a


def test_getattr_dict() -> None:
    c = OmegaConf.create("a: {b: 1}")
    assert isinstance(c, DictConfig)
    assert {"b": 1} == c.a


@mark.parametrize("struct", [False, True])
@mark.parametrize(
    "cfg",
    [
        param({"name": "alice", "age": 1}, id="dict"),
        param(User(name="alice", age=1), id="structured_config"),
    ],
)
def test_delattr(cfg: Any, struct: bool) -> None:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_struct(cfg, struct)
    delattr(cfg, "name")
    assert cfg == {"age": 1}
    with raises(ConfigAttributeError):
        delattr(cfg, "c")


@mark.parametrize(
    "key,match",
    [
        param("a", "a", id="str"),
        param(b"binary", "binary", id="bytes"),
        param(1, "1", id="int"),
        param(123.45, "123.45", id="float"),
        param(True, "True", id="bool-T"),
        param(False, "False", id="bool-F"),
        param(Enum1.FOO, "FOO", id="enum"),
    ],
)
class TestDictKeyTypes:
    def test_mandatory_value(self, key: DictKeyType, match: str) -> None:
        c = OmegaConf.create({key: "???"})
        with raises(MissingMandatoryValue, match=match):
            c[key]
        if isinstance(key, str):
            with raises(MissingMandatoryValue, match=match):
                getattr(c, key)

    def test_nested_dict_mandatory_value_inner(
        self, key: DictKeyType, match: str
    ) -> None:
        c = OmegaConf.create({"b": {key: "???"}})
        with raises(MissingMandatoryValue, match=match):
            c.b[key]
        if isinstance(key, str):
            with raises(MissingMandatoryValue, match=match):
                getattr(c.b, key)

    def test_nested_dict_mandatory_value_outer(
        self, key: DictKeyType, match: str
    ) -> None:
        c = OmegaConf.create({key: {"b": "???"}})
        with raises(MissingMandatoryValue, match=match):
            c[key].b
        if isinstance(key, str):
            with raises(MissingMandatoryValue, match=match):
                getattr(c, key).b

    def test_subscript_get(self, key: DictKeyType, match: str) -> None:
        c = OmegaConf.create({key: "b"})
        assert isinstance(c, DictConfig)
        assert "b" == c[key]

    def test_subscript_set(self, key: DictKeyType, match: str) -> None:
        c = OmegaConf.create()
        c[key] = "b"
        assert {key: "b"} == c


@mark.parametrize(
    "src,key,expected",
    [
        ({"a": 10, "b": 11}, "a", {"b": 11}),
        ({b"abc": 10, b"def": 11}, b"abc", {b"def": 11}),
        ({1: "a", 2: "b"}, 1, {2: "b"}),
        ({123.45: "a", 67.89: "b"}, 67.89, {123.45: "a"}),
        ({True: "a", False: "b"}, False, {True: "a"}),
        ({Enum1.FOO: "foo", Enum1.BAR: "bar"}, Enum1.FOO, {Enum1.BAR: "bar"}),
    ],
)
class TestDelitemKeyTypes:
    def test_dict_delitem(self, src: Any, key: DictKeyType, expected: Any) -> None:
        c = OmegaConf.create(src)
        assert c == src
        del c[key]
        assert c == expected

    def test_dict_delitem_KeyError(
        self, src: Any, key: DictKeyType, expected: Any
    ) -> None:
        c = OmegaConf.create(expected)
        assert c == expected
        with raises(KeyError):
            del c[key]

    def test_dict_struct_delitem(
        self, src: Any, key: DictKeyType, expected: Any
    ) -> None:
        c = OmegaConf.create(src)
        OmegaConf.set_struct(c, True)
        with raises(ConfigTypeError):
            del c[key]
        with open_dict(c):
            del c[key]
        assert key not in c


def test_attribute_error() -> None:
    c = OmegaConf.create()
    with raises(ConfigAttributeError):
        assert c.missing_key


@mark.parametrize("c", [{}, OmegaConf.create()])
def test_get_default_value(c: Any) -> None:
    assert c.get("missing_key", "a default value") == "a default value"


def test_scientific_notation_float() -> None:
    c = OmegaConf.create("a: 10e-3")
    assert isinstance(c, DictConfig)
    assert 10e-3 == c.a


@mark.parametrize("struct", [None, True, False])
@mark.parametrize("default_val", [4, True, False, None])
class TestGetWithDefault:
    @mark.parametrize(
        "d,select,key",
        [
            ({"key": {"subkey": 2}}, "", "missing"),
            ({"key": {"subkey": 2}}, "key", "missing"),
            ({"key": "???"}, "", "key"),
            ({"key": DictConfig(content="???")}, "", "key"),
            ({"key": ListConfig(content="???")}, "", "key"),
        ],
    )
    def test_dict_get_with_default(
        self, d: Any, select: Any, key: Any, default_val: Any, struct: Optional[bool]
    ) -> None:
        c = OmegaConf.create(d)
        c = OmegaConf.select(c, select)
        OmegaConf.set_struct(c, struct)
        assert c.get(key, default_val) == default_val

    @mark.parametrize(
        ("d", "select", "key", "expected"),
        [
            ({"key": "value"}, "", "key", "value"),
            ({"key": None}, "", "key", None),
            ({"key": {"subkey": None}}, "key", "subkey", None),
            ({"key": DictConfig(is_optional=True, content=None)}, "", "key", None),
            ({"key": ListConfig(is_optional=True, content=None)}, "", "key", None),
        ],
    )
    def test_dict_get_not_returning_default(
        self,
        d: Any,
        select: Any,
        key: Any,
        expected: Any,
        default_val: Any,
        struct: Optional[bool],
    ) -> None:
        c = OmegaConf.create(d)
        c = OmegaConf.select(c, select)
        OmegaConf.set_struct(c, struct)
        assert c.get(key, default_val) == expected

    @mark.parametrize(
        "d,exc",
        [
            ({"key": "${foo}"}, InterpolationKeyError),
            (
                {"key": "${foo}", "foo": "???"},
                InterpolationToMissingValueError,
            ),
            ({"key": DictConfig(content="${foo}")}, InterpolationKeyError),
        ],
    )
    def test_dict_get_with_default_errors(
        self, d: Any, exc: type, struct: Optional[bool], default_val: Any
    ) -> None:
        c = OmegaConf.create(d)
        OmegaConf.set_struct(c, struct)
        with raises(exc):
            c.get("key", default_value=123)


def test_map_expansion() -> None:
    c = OmegaConf.create("{a: 2, b: 10}")
    assert isinstance(c, DictConfig)

    def foo(a: int, b: int) -> int:
        return a + b

    assert 12 == foo(**c)  # type: ignore[misc] # (known mypi error with dict unpacking)


def test_items_iterator_behavior() -> None:
    c = OmegaConf.create({"a": 2, "b": 10})
    assert list(c.items()) == [("a", 2), ("b", 10)]

    # This is actually not compatible with native dict:
    # Due to implementation considerations, DictConfig items() returns a list.
    # If that can be fixed, feel free to remove this block
    items = c.items()
    for x in [("a", 2), ("b", 10)]:
        assert x in items

    items2 = iter(c.items())
    assert next(items2) == ("a", 2)
    assert next(items2) == ("b", 10)
    with raises(StopIteration):
        next(items2)


def test_mutate_config_via_items_iteration() -> None:
    c = OmegaConf.create({"a": {"v": 1}, "b": {"v": 1}})
    for k, v in c.items():
        v.v = 2

    assert c == {"a": {"v": 2}, "b": {"v": 2}}


def test_items_with_interpolation() -> None:
    c = OmegaConf.create({"a": 2, "b": "${a}"})
    r = {}
    for k, v in c.items():
        r[k] = v
    assert r["a"] == 2
    assert r["b"] == 2


@mark.parametrize(
    ("cfg", "expected", "expected_no_resolve"),
    [
        param({}, [], [], id="empty"),
        param({"a": 10}, [("a", 10)], [("a", 10)], id="simple"),
        param(
            {"a": 2, "b": "${a}"},
            [("a", 2), ("b", 2)],
            [("a", 2), ("b", "${a}")],
            id="interpolation_in_value",
        ),
        param(
            {"a": "???"},
            raises(MissingMandatoryValue),
            [("a", "???")],
            id="missing_value",
        ),
        # Special DictConfigs
        param(DictConfig(None), raises(TypeError), raises(TypeError), id="none"),
        param(
            DictConfig("???"),
            raises(MissingMandatoryValue),
            raises(MissingMandatoryValue),
            id="missing",
        ),
        param(DictConfig("${missing}"), [], [], id="missing_interpolation"),
        param(
            DictConfig("${a}", parent=DictConfig({"a": {"b": 10}})),
            [],
            [],
            id="missing_interpolation",
        ),
    ],
)
def test_items(cfg: Any, expected: Any, expected_no_resolve: Any) -> None:
    cfg = _ensure_container(cfg)

    if isinstance(expected, list):
        assert list(cfg.items()) == expected
    else:
        with expected:
            cfg.items()

    if isinstance(expected_no_resolve, list):
        pairs = list(cfg.items_ex(resolve=False))
        assert pairs == expected_no_resolve
        for idx in range(len(expected_no_resolve)):
            assert type(pairs[idx][0]) == type(expected_no_resolve[idx][0])  # noqa
            assert type(pairs[idx][1]) == type(expected_no_resolve[idx][1])  # noqa
    else:
        with expected_no_resolve:
            cfg.items_ex(resolve=False)


@mark.parametrize(
    ("cfg", "expected"),
    [
        param({}, [], id="empty"),
        param({"a": 10}, ["a"], id="full"),
        param({"a": "???"}, ["a"], id="missing_value"),
        param({"a": "${missing}}"}, ["a"], id="missing_interpolation"),
        param({"a": "${b}}", "b": 10}, ["a", "b"], id="interpolation"),
        param(DictConfig(None), [], id="none_dictconfig"),
        param(DictConfig("???"), [], id="missing_dictconfig"),
        param(DictConfig("${missing}"), [], id="missing_interpolation_dictconfig"),
        param(
            DictConfig("${a}", parent=OmegaConf.create({"a": {"b": 10}})),
            [],
            id="interpolation_dictconfig",
        ),
    ],
)
def test_dict_keys(cfg: Any, expected: Any) -> None:
    c = _ensure_container(cfg)
    assert list(c.keys()) == expected


def test_pickle_get_root() -> None:
    # Test that get_root() is reconstructed correctly for pickle loaded files.
    with tempfile.TemporaryFile() as fp:
        c1 = OmegaConf.create({"a": {"a1": 1, "a2": 2}})

        c2 = OmegaConf.create(
            {"b": {"b1": "${a.a1}", "b2": 4, "bb": {"bb1": 3, "bb2": 4}}}
        )
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


@mark.parametrize(
    "cfg, key, default_, expected",
    [
        # string key
        param({"a": 1, "b": 2}, "a", "__NO_DEFAULT__", 1, id="no_default"),
        param({"a": 1, "b": 2}, "not_found", None, None, id="none_default"),
        param({"a": 1, "b": 2}, "not_found", "default", "default", id="with_default"),
        param({"a": None}, "a", "default", None, id="none_value"),
        param({"a": "???"}, "a", "default", "default", id="missing_value"),
        # Interpolations
        param({"a": "${b}", "b": 2}, "a", "__NO_DEFAULT__", 2, id="interpolation"),
        # enum key
        param(
            {Enum1.FOO: "bar"},
            Enum1.FOO,
            "__NO_DEFAULT__",
            "bar",
            id="enum_key_no_default",
        ),
        param(
            {Enum1.FOO: "bar"}, Enum1.BAR, None, None, id="enum_key_with_none_default"
        ),
        param(
            {Enum1.FOO: "bar"},
            Enum1.BAR,
            "default",
            "default",
            id="enum_key_with_default",
        ),
        # bytes keys
        param(
            {b"123": "a", b"42": "b"},
            b"42",
            "__NO_DEFAULT__",
            "b",
            id="bytes_key_no_default",
        ),
        param(
            {b"123": "a", b"42": "b"},
            "not found",
            None,
            None,
            id="bytes_key_with_default",
        ),
        # other key types
        param(
            {123.45: "a", 67.89: "b"},
            67.89,
            "__NO_DEFAULT__",
            "b",
            id="float_key_no_default",
        ),
        param(
            {123.45: "a", 67.89: "b"},
            "not found",
            None,
            None,
            id="float_key_with_default",
        ),
        param(
            {True: "a", False: "b"},
            False,
            "__NO_DEFAULT__",
            "b",
            id="bool_key_no_default",
        ),
        param(
            {True: "a", False: "b"}, "not found", None, None, id="bool_key_with_default"
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
    with raises(ConfigTypeError):
        cfg.pop("name")

    with raises(ConfigTypeError):
        cfg.pop("bar")

    with raises(ConfigTypeError):
        cfg.pop("bar", "not even with default")


def test_dict_structured_mode_pop() -> None:
    cfg = OmegaConf.create({"user": User(name="Bond")})
    with raises(ConfigTypeError):
        cfg.user.pop("name")

    with raises(ConfigTypeError):
        cfg.user.pop("bar")

    with raises(ConfigTypeError):
        cfg.user.pop("bar", "not even with default")

    # Unlocking the top level node is not enough.
    with raises(ConfigTypeError):
        with open_dict(cfg):
            cfg.user.pop("name")

    # You need to unlock the specified structured node to pop a field from it.
    with open_dict(cfg.user):
        cfg.user.pop("name")
    assert "name" not in cfg.user


@mark.parametrize(
    "cfg, key, expectation",
    [
        # key not found
        ({"a": 1, "b": 2}, "not_found", raises(KeyError)),
        ({b"abc": 1, b"def": 2}, b"ghi", raises(KeyError)),
        ({1: "a", 2: "b"}, 3, raises(KeyError)),
        ({123.45: "a", 67.89: "b"}, 10.11, raises(KeyError)),
        ({True: "a"}, False, raises(KeyError)),
        ({Enum1.FOO: "bar"}, Enum1.BAR, raises(KeyError)),
        # Interpolations
        ({"a": "???", "b": 2}, "a", raises(MissingMandatoryValue)),
        ({1: "???", 2: "b"}, 1, raises(MissingMandatoryValue)),
        ({123.45: "???", 67.89: "b"}, 123.45, raises(MissingMandatoryValue)),
        ({"a": "${b}"}, "a", raises(InterpolationKeyError)),
        ({True: "???", False: "b"}, True, raises(MissingMandatoryValue)),
        (
            {Enum1.FOO: "???", Enum1.BAR: "bar"},
            Enum1.FOO,
            raises(MissingMandatoryValue),
        ),
        (
            {"a": "${b}", "b": "???"},
            "a",
            raises(InterpolationToMissingValueError),
        ),
    ],
)
def test_dict_pop_error(cfg: Dict[Any, Any], key: Any, expectation: Any) -> None:
    c = OmegaConf.create(cfg)
    with expectation:
        c.pop(key)
    assert c == cfg


@mark.parametrize(
    "conf,key,expected",
    [
        # str key type
        ({"a": 1, "b": {}}, "a", True),
        ({"a": 1, "b": {}}, "b", True),
        ({"a": 1, "b": {}}, "c", False),
        ({"a": 1, "b": "${a}"}, "b", True),
        ({"a": 1, "b": "???"}, "b", False),
        ({"a": 1, "b": "???", "c": "${b}"}, "c", True),
        ({"a": 1, "b": "${not_found}"}, "b", True),
        ({"a": "${unknown_resolver:bar}"}, "a", True),
        ({"a": None, "b": "${a}"}, "b", True),
        ({"a": "cat", "b": "${a}"}, "b", True),
        # Enum key type
        ({Enum1.FOO: 1, "b": {}}, Enum1.FOO, True),
        ({Enum1.FOO: 1, "b": {}}, "aaa", False),
        ({Enum1.FOO: 1, "b": {}}, "FOO", False),
        (
            DictConfig(content={Enum1.FOO: "foo"}, key_type=Enum1, element_type=str),
            Enum1.FOO,
            True,
        ),
        (
            DictConfig(content={Enum1.FOO: "foo"}, key_type=Enum1, element_type=str),
            "incompatible_key_type",
            False,
        ),
        (
            DictConfig(content={Enum1.FOO: "foo"}, key_type=Enum1, element_type=str),
            "FOO",
            True,
        ),
        (
            DictConfig(content={Enum1.FOO: "foo"}, key_type=Enum1, element_type=str),
            None,
            False,
        ),
        # int key type
        ({1: "a", 2: {}}, 1, True),
        ({1: "a", 2: {}}, 2, True),
        ({1: "a", 2: {}}, 3, False),
        ({1: "a", 2: "???"}, 2, False),
        ({1: "a", 2: "???"}, None, False),
        ({1: "a", 2: "???"}, "1", False),
        (DictConfig({1: "a", 2: "???"}, key_type=int), "1", False),
        # float key type
        ({1.1: "a", 2.2: {}}, 1.1, True),
        ({1.1: "a", 2.2: {}}, "1.1", False),
        (DictConfig({1.1: "a", 2.2: {}}, key_type=float), "1.1", False),
        ({1.1: "a", 2.2: {}}, 2.2, True),
        ({1.1: "a", 2.2: {}}, 3.3, False),
        ({1.1: "a", 2.2: "???"}, 2.2, False),
        ({1.1: "a", 2.2: "???"}, None, False),
        # bool key type
        ({True: "a", False: {}}, True, True),
        ({True: "a", False: {}}, False, True),
        ({True: "a", False: {}}, "no", False),
        ({True: "a", False: {}}, 1, True),
        ({True: "a", False: {}}, None, False),
        ({True: "a", False: "???"}, False, False),
        # bytes key type
        ({b"1": "a", b"2": {}}, b"1", True),
        ({b"1": "a", b"2": {}}, b"2", True),
        ({b"1": "a", b"2": {}}, b"3", False),
        ({b"1": "a", b"2": "???"}, b"2", False),
        ({b"1": "a", b"2": "???"}, None, False),
        ({b"1": "a", b"2": "???"}, "1", False),
    ],
)
def test_in_dict(conf: Any, key: str, expected: Any) -> None:
    conf = OmegaConf.create(conf)
    assert (key in conf) == expected


def test_get_root() -> None:
    c = OmegaConf.create({"a": 123, "b": {"bb": 456, "cc": 7}})
    assert c._get_root() == c
    assert c.b._get_root() == c


def test_get_root_of_merged() -> None:
    c1 = OmegaConf.create({"a": {"a1": 1, "a2": 2}})

    c2 = OmegaConf.create({"b": {"b1": "???", "b2": 4, "bb": {"bb1": 3, "bb2": 4}}})
    c3 = OmegaConf.merge(c1, c2)
    assert isinstance(c3, DictConfig)

    assert c3._get_root() == c3
    assert c3.a._get_root() == c3
    assert c3.b._get_root() == c3
    assert c3.b.bb._get_root() == c3


def test_dict_config() -> None:
    c = OmegaConf.create({})
    assert isinstance(c, DictConfig)


def test_dict_structured_delitem() -> None:
    c = OmegaConf.structured(User(name="Bond"))
    with raises(ConfigTypeError):
        del c["name"]

    with open_dict(c):
        del c["name"]
    assert "name" not in c


def test_dict_nested_structured_delitem() -> None:
    c = OmegaConf.create({"user": User(name="Bond")})
    with raises(ConfigTypeError):
        del c.user["name"]

    # Unlocking the top level node is not enough.
    with raises(ConfigTypeError):
        with open_dict(c):
            del c.user["name"]

    # You need to unlock the specified structured node to delete a field from it.
    with open_dict(c.user):
        del c.user["name"]
    assert "name" not in c.user


@mark.parametrize(
    "d, expected",
    [
        param(DictConfig({}), 0, id="empty"),
        param(DictConfig({"a": 10}), 1, id="full"),
        param(DictConfig(None), 0, id="none"),
        param(DictConfig("???"), 0, id="missing"),
        param(
            DictConfig("${foo}", parent=OmegaConf.create({"foo": {"a": 10}})),
            0,
            id="interpolation",
        ),
        param(DictConfig("${foo}"), 0, id="broken_interpolation"),
    ],
)
def test_dict_len(d: DictConfig, expected: Any) -> None:
    assert d.__len__() == expected


def test_dict_assign_illegal_value() -> None:
    c = OmegaConf.create()
    iv = IllegalType()
    with raises(UnsupportedValueType, match=re.escape("key: a")):
        c.a = iv

    with flag_override(c, "allow_objects", True):
        c.a = iv
    assert c.a == iv


def test_dict_assign_illegal_value_nested() -> None:
    c = OmegaConf.create({"a": {}})
    iv = IllegalType()
    with raises(UnsupportedValueType, match=re.escape("key: a.b")):
        c.a.b = iv

    with flag_override(c, "allow_objects", True):
        c.a.b = iv
    assert c.a.b == iv


def test_assign_dict_in_dict() -> None:
    c = OmegaConf.create({})
    c.foo = {"foo": "bar"}
    assert c.foo == {"foo": "bar"}
    assert isinstance(c.foo, DictConfig)


def test_instantiate_config_fails() -> None:
    with raises(TypeError):
        BaseContainer()  # type: ignore


@mark.parametrize(
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
    c1 = OmegaConf.create({"a": 10})
    c2 = OmegaConf.create({"a": 10})
    assert hash(c1) == hash(c2)
    c2.a = 20
    assert hash(c1) != hash(c2)


@mark.parametrize("default", ["default", 0, None])
def test_get_with_default_from_struct_not_throwing(default: Any) -> None:
    c = OmegaConf.create({"a": 10, "b": 20})
    OmegaConf.set_struct(c, True)
    assert c.get("z", default) == default


@mark.parametrize("cfg", [{"foo": {}}, [1, 2, 3]])
def test_members(cfg: Any) -> None:
    # Make sure accessing __members__ does not return None or throw.
    c = OmegaConf.create(cfg)
    with raises(AttributeError):
        c.__members__


@mark.parametrize(
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

    with raises(ValueError):
        OmegaConf.masked_copy("fail", [])  # type: ignore


def test_shallow_copy() -> None:
    cfg = OmegaConf.create({"a": 1, "b": 2})
    c = cfg.copy()
    cfg.a = 42
    assert cfg.a == 42
    assert c.a == 1


def test_shallow_copy_missing() -> None:
    cfg = DictConfig(content=MISSING)
    c = cfg.copy()
    c._set_value({"foo": 1})
    assert c.foo == 1
    assert cfg._is_missing()


def test_shallow_copy_none() -> None:
    cfg = DictConfig(content=None)
    c = cfg.copy()
    c._set_value({"foo": 1})
    assert c.foo == 1
    assert cfg._is_none()


@mark.parametrize(
    "copy_method",
    [
        param(copy.copy),
        param(lambda x: x.copy(), id="obj.copy"),
    ],
)
def test_dict_shallow_copy_is_deepcopy(copy_method: Any) -> None:
    cfg = OmegaConf.create({"a": {"b": 10}})
    cp = copy_method(cfg)
    assert cfg is not cp
    assert cfg._get_node("a") is not cp._get_node("a")


def test_creation_with_invalid_key() -> None:
    with raises(KeyValidationError):
        OmegaConf.create({object(): "a"})


def test_setitem_with_invalid_key() -> None:
    cfg = OmegaConf.create()
    with raises(KeyValidationError):
        cfg.__setitem__(object(), "a")  # type: ignore


def test_getitem_with_invalid_key() -> None:
    cfg = OmegaConf.create()
    with raises(KeyValidationError):
        cfg.__getitem__(object())  # type: ignore


def test_hasattr() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    assert hasattr(cfg, "foo")
    assert not hasattr(cfg, "buz")


def test_typed_hasattr() -> None:
    cfg = OmegaConf.structured(SubscriptedDict)
    assert hasattr(cfg.dict_enum, "foo") is False
    with raises(AttributeError):
        cfg.dict_int.foo


def test_struct_mode_missing_key_getitem() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    with raises(KeyError):
        cfg.__getitem__("zoo")


def test_struct_mode_missing_key_setitem() -> None:
    cfg = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(cfg, True)
    with raises(KeyError):
        cfg.__setitem__("zoo", 10)


def test_get_type() -> None:
    cfg = OmegaConf.structured(User)
    assert OmegaConf.get_type(cfg) == User

    cfg = OmegaConf.structured(User(name="bond"))
    assert OmegaConf.get_type(cfg) == User

    cfg = OmegaConf.create({"user": User, "inter": "${user}"})
    assert OmegaConf.get_type(cfg.user) == User
    assert OmegaConf.get_type(cfg.inter) == User


@mark.parametrize(
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
    assert _utils.get_type_hint(cfg.plugin) == expected_ref_type


def test_get_ref_type_with_conflict() -> None:
    cfg = OmegaConf.create(
        {"user": User, "inter": DictConfig(ref_type=Plugin, content="${user}")}
    )

    assert OmegaConf.get_type(cfg.user) == User
    assert _utils.get_type_hint(cfg.user) == Any

    # Interpolation inherits both type and ref type from the target
    assert OmegaConf.get_type(cfg.inter) == User
    assert _utils.get_type_hint(cfg.inter) == Any


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
    assert cfg._get_node("foo")._is_missing()  # type: ignore
    assert not cfg._get_node("inter")._is_missing()  # type: ignore
    assert not cfg._get_node("str_inter")._is_missing()  # type: ignore
    assert cfg._get_node("missing_node")._is_missing()  # type: ignore
    assert not cfg._get_node("missing_node_inter")._is_missing()  # type: ignore


@mark.parametrize("ref_type", [None, Any])
@mark.parametrize("assign", [None, {}, {"foo": "bar"}, [1, 2, 3]])
def test_assign_to_reftype_none_or_any(ref_type: Any, assign: Any) -> None:
    cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content={})})
    cfg.foo = assign
    assert cfg.foo == assign


@mark.parametrize(
    "ref_type,assign",
    [
        param(Plugin, None, id="plugin_none"),
        param(Plugin, Plugin, id="plugin_plugin"),
        param(Plugin, Plugin(), id="plugin_plugin()"),
        param(Plugin, ConcretePlugin, id="plugin_concrete"),
        param(Plugin, ConcretePlugin(), id="plugin_concrete()"),
        param(ConcretePlugin, None, id="concrete_none"),
        param(ConcretePlugin, ConcretePlugin, id="subclass=subclass_obj"),
        param(ConcretePlugin, ConcretePlugin(), id="subclass=subclass_obj"),
    ],
)
class TestAssignAndMergeIntoReftypePlugin:
    def _test_assign(self, ref_type: Any, value: Any, assign: Any) -> None:
        cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content=value)})
        assert _utils.get_type_hint(cfg, "foo") == Optional[ref_type]
        cfg.foo = assign
        assert cfg.foo == assign
        assert _utils.get_type_hint(cfg, "foo") == Optional[ref_type]

    def _test_merge(self, ref_type: Any, value: Any, assign: Any) -> None:
        cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content=value)})
        cfg2 = OmegaConf.merge(cfg, {"foo": assign})
        assert isinstance(cfg2, DictConfig)
        assert cfg2.foo == assign
        assert _utils.get_type_hint(cfg2, "foo") == Optional[ref_type]

    def test_assign_to_reftype_plugin1(self, ref_type: Any, assign: Any) -> None:
        self._test_assign(ref_type, ref_type, assign)
        self._test_assign(ref_type, ref_type(), assign)

    @mark.parametrize("value", [None, "???"])
    def test_assign_to_reftype_plugin(
        self, ref_type: Any, value: Any, assign: Any
    ) -> None:
        self._test_assign(ref_type, value, assign)

    def test_merge_into_reftype_plugin_(self, ref_type: Any, assign: Any) -> None:
        self._test_merge(ref_type, ref_type, assign)
        self._test_merge(ref_type, ref_type(), assign)

    @mark.parametrize("value", [None, "???"])
    def test_merge_into_reftype_plugin(
        self, ref_type: Any, value: Any, assign: Any
    ) -> None:
        self._test_merge(ref_type, value, assign)


@mark.parametrize(
    "ref_type,assign,expectation",
    [
        param(
            Plugin,
            10,
            raises(ValidationError),
            id="assign_primitive_to_typed",
        ),
        param(
            ConcretePlugin,
            Plugin,
            raises(ValidationError),
            id="assign_base_type_to_subclass",
        ),
        param(
            ConcretePlugin,
            Plugin(),
            raises(ValidationError),
            id="assign_base_instance_to_subclass",
        ),
    ],
)
class TestAssignAndMergeIntoReftypePlugin_Errors:
    def _test_assign(
        self, ref_type: Any, value: Any, assign: Any, expectation: Any
    ) -> None:
        cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content=value)})
        with expectation:
            cfg.foo = assign

    def _test_merge(
        self, ref_type: Any, value: Any, assign: Any, expectation: Any
    ) -> None:
        cfg = OmegaConf.create({"foo": DictConfig(ref_type=ref_type, content=value)})
        with expectation:
            OmegaConf.merge(cfg, {"foo": assign})

    def test_assign_to_reftype_plugin_(
        self, ref_type: Any, assign: Any, expectation: Any
    ) -> None:
        self._test_assign(ref_type, ref_type, assign, expectation)
        self._test_assign(ref_type, ref_type(), assign, expectation)

    @mark.parametrize("value", [None, "???"])
    def test_assign_to_reftype_plugin(
        self, ref_type: Any, value: Any, assign: Any, expectation: Any
    ) -> None:
        self._test_assign(ref_type, value, assign, expectation)

    def test_merge_into_reftype_plugin1(
        self, ref_type: Any, assign: Any, expectation: Any
    ) -> None:
        self._test_merge(ref_type, ref_type, assign, expectation)
        self._test_merge(ref_type, ref_type(), assign, expectation)

    @mark.parametrize("value", [None, "???"])
    def test_merge_into_reftype_plugin(
        self, ref_type: Any, value: Any, assign: Any, expectation: Any
    ) -> None:
        self._test_merge(ref_type, value, assign, expectation)


def test_setdefault() -> None:
    cfg = OmegaConf.create({})
    assert cfg.setdefault("foo", 10) == 10
    assert cfg["foo"] == 10
    assert cfg.setdefault("foo", 20) == 10
    assert cfg["foo"] == 10

    cfg = OmegaConf.create({})
    OmegaConf.set_struct(cfg, True)
    with raises(ConfigKeyError):
        assert cfg.setdefault("foo", 10) == 10
    assert cfg == {}
    with open_dict(cfg):
        assert cfg.setdefault("foo", 10) == 10

    assert cfg.setdefault("foo", 20) == 10
    assert cfg["foo"] == 10

    assert cfg["foo"] == 10


@mark.parametrize(
    "c",
    [
        param({"a": ListConfig([1, 2, 3], ref_type=list)}, id="list_value"),
        param({"a": DictConfig({"b": 10}, ref_type=dict)}, id="dict_value"),
    ],
)
def test_self_assign_list_value_with_ref_type(c: Any) -> None:
    cfg = OmegaConf.create(c)
    cfg.a = cfg.a
    assert cfg == c


def test_assign_to_sc_field_without_ref_type() -> None:
    cfg = OmegaConf.create({"plugin": ConcretePlugin})
    with raises(ValidationError):
        cfg.plugin.params.foo = "bar"

    cfg.plugin = 10
    assert cfg.plugin == 10


def test_dict_getitem_not_found() -> None:
    cfg = OmegaConf.create()
    with raises(ConfigKeyError):
        cfg["aaa"]


def test_dict_getitem_none_output() -> None:
    cfg = OmegaConf.create({"a": None})
    assert cfg["a"] is None


@mark.parametrize("data", [{"b": 0}, User])
@mark.parametrize("flag", ["struct", "readonly"])
def test_dictconfig_creation_with_parent_flag(flag: str, data: Any) -> None:
    parent = OmegaConf.create({"a": 10})
    parent._set_flag(flag, True)
    cfg = DictConfig(data, parent=parent)
    assert cfg == data


@mark.parametrize(
    "node",
    [
        param(AnyNode("hello"), id="any"),
        param(DictConfig({}), id="dict"),
        param(ListConfig([]), id="list"),
    ],
)
def test_node_copy_on_set(node: Any) -> None:
    cfg = OmegaConf.create({})
    cfg.a = node
    assert cfg.__dict__["_content"]["a"] is not node
