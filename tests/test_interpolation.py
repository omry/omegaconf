import os
import random
import re
from typing import Any, Dict

import pytest

from omegaconf import (
    DictConfig,
    IntegerNode,
    ListConfig,
    OmegaConf,
    Resolver,
    ValidationError,
)


def test_str_interpolation_dict_1() -> None:
    # Simplest str_interpolation
    c = OmegaConf.create(dict(a="${referenced}", referenced="bar"))
    assert c.referenced == "bar"
    assert c.a == "bar"


def test_str_interpolation_key_error_1() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(a="${not_found}"))

    with pytest.raises(KeyError):
        _ = c.a


def test_str_interpolation_key_error_2() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(a="${not.found}"))

    with pytest.raises(KeyError):
        c.a


def test_str_interpolation_3() -> None:
    # Test that str_interpolation works with complex strings
    c = OmegaConf.create(dict(a="the year ${year}", year="of the cat"))

    assert c.a == "the year of the cat"


def test_str_interpolation_4() -> None:
    # Test that a string with multiple str_interpolations works
    c = OmegaConf.create(
        dict(a="${ha} ${ha} ${ha}, said Pennywise, ${ha} ${ha}... ${ha}!", ha="HA")
    )

    assert c.a == "HA HA HA, said Pennywise, HA HA... HA!"


def test_deep_str_interpolation_1() -> None:
    # Test deep str_interpolation works
    c = OmegaConf.create(
        dict(
            a="the answer to the universe and everything is ${nested.value}",
            nested=dict(value=42),
        )
    )

    assert c.a == "the answer to the universe and everything is 42"


def test_deep_str_interpolation_2() -> None:
    # Test that str_interpolation of a key that is nested works
    c = OmegaConf.create(
        dict(
            out=42,
            deep=dict(inside="the answer to the universe and everything is ${out}"),
        )
    )

    assert c.deep.inside == "the answer to the universe and everything is 42"


def test_simple_str_interpolation_inherit_type() -> None:
    # Test that str_interpolation of a key that is nested works
    c = OmegaConf.create(
        dict(
            inter1="${answer1}",
            inter2="${answer2}",
            inter3="${answer3}",
            inter4="${answer4}",
            answer1=42,
            answer2=42.0,
            answer3=False,
            answer4="string",
        )
    )

    assert type(c.inter1) == int
    assert type(c.inter2) == float
    assert type(c.inter3) == bool
    assert type(c.inter4) == str


def test_complex_str_interpolation_is_always_str_1() -> None:
    c = OmegaConf.create(dict(two=2, four=4, inter1="${four}${two}", inter2="4${two}"))

    assert type(c.inter1) == str
    assert c.inter1 == "42"
    assert type(c.inter2) == str
    assert c.inter2 == "42"


@pytest.mark.parametrize(  # type: ignore
    "input_,key,expected",
    [
        (dict(a=10, b="${a}"), "b", 10),
        (dict(a=10, b=[1, "${a}", 3, 4]), "b.1", 10),
        (dict(a="${b.1}", b=[1, dict(c=10), 3, 4]), "a", dict(c=10)),
        (dict(a="${b}", b=[1, 2]), "a", [1, 2]),
        (dict(a="foo-${b}", b=[1, 2]), "a", "foo-[1, 2]"),
        (dict(a="foo-${b}", b=dict(c=10)), "a", "foo-{'c': 10}"),
    ],
)
def test_interpolation(input_: Dict[str, Any], key: str, expected: str) -> None:
    c = OmegaConf.create(input_)
    assert OmegaConf.select(c, key) == expected


def test_2_step_interpolation() -> None:
    c = OmegaConf.create(dict(src="bar", copy_src="${src}", copy_copy="${copy_src}"))
    assert c.copy_src == "bar"
    assert c.copy_copy == "bar"


def test_env_interpolation1() -> None:
    try:
        os.environ["foobar"] = "1234"
        c = OmegaConf.create({"path": "/test/${env:foobar}"})
        assert c.path == "/test/1234"
    finally:
        del os.environ["foobar"]


def test_env_interpolation_not_found() -> None:
    c = OmegaConf.create({"path": "/test/${env:foobar}"})
    with pytest.raises(
        ValidationError, match=re.escape("Environment variable 'foobar' not found")
    ):
        c.path


def test_env_default_str_interpolation_missing_env() -> None:
    if os.getenv("foobar") is not None:
        del os.environ["foobar"]
    c = OmegaConf.create({"path": "/test/${env:foobar,abc}"})
    assert c.path == "/test/abc"


def test_env_default_interpolation_missing_env_default_with_slash() -> None:
    if os.getenv("foobar") is not None:
        del os.environ["foobar"]
    c = OmegaConf.create({"path": "${env:DATA_PATH,a/b}"})
    assert c.path == "a/b"


def test_env_default_interpolation_env_exist() -> None:
    os.environ["foobar"] = "1234"
    c = OmegaConf.create({"path": "/test/${env:foobar,abc}"})
    assert c.path == "/test/1234"


@pytest.mark.parametrize(  # type: ignore
    "value,expected",
    [
        # bool
        ("false", False),
        ("true", True),
        # int
        ("10", 10),
        ("-10", -10),
        # float
        ("10.0", 10.0),
        ("-10.0", -10.0),
        # strings
        ("off", "off"),
        ("no", "no"),
        ("on", "on"),
        ("yes", "yes"),
        (">1234", ">1234"),
        (":1234", ":1234"),
        ("/1234", "/1234"),
        # yaml strings are not getting parsed by the env resolver
        ("foo: bar", "foo: bar"),
        ("foo: \n - bar\n - baz", "foo: \n - bar\n - baz"),
    ],
)
def test_env_values_are_typed(value: Any, expected: Any) -> None:
    try:
        os.environ["my_key"] = value
        c = OmegaConf.create(dict(my_key="${env:my_key}"))
        assert c.my_key == expected
    finally:
        del os.environ["my_key"]


def test_register_resolver_twice_error(restore_resolvers: Any) -> None:
    def foo() -> int:
        return 10

    OmegaConf.register_resolver("foo", foo)
    with pytest.raises(AssertionError):
        OmegaConf.register_resolver("foo", lambda: 10)


def test_clear_resolvers(restore_resolvers: Any) -> None:
    assert OmegaConf.get_resolver("foo") is None
    OmegaConf.register_resolver("foo", lambda x: int(x) + 10)
    assert OmegaConf.get_resolver("foo") is not None
    OmegaConf.clear_resolvers()
    assert OmegaConf.get_resolver("foo") is None


def test_register_resolver_1(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    c = OmegaConf.create(dict(k="${plus_10:990}"))

    assert type(c.k) == int
    assert c.k == 1000


def test_resolver_cache_1(restore_resolvers: Any) -> None:
    # resolvers are always converted to stateless idempotent functions
    # subsequent calls to the same function with the same argument will always return the same value.
    # this is important to allow embedding of functions like time() without having the value change during
    # the program execution.
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create(dict(k="${random:_}"))
    assert c.k == c.k


def test_resolver_cache_2(restore_resolvers: Any) -> None:
    """
    Tests that resolver cache is not shared between different OmegaConf objects
    """
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c1 = OmegaConf.create(dict(k="${random:_}"))
    c2 = OmegaConf.create(dict(k="${random:_}"))
    assert c1.k != c2.k
    assert c1.k == c1.k
    assert c2.k == c2.k


@pytest.mark.parametrize(  # type: ignore
    "resolver,name,key,result",
    [
        (lambda *args: args, "arg_list", "${my_resolver:cat, dog}", ("cat", "dog")),
        (
            lambda *args: args,
            "escape_comma",
            "${my_resolver:cat\\, do g}",
            ("cat, do g",),
        ),
        (
            lambda *args: args,
            "escape_whitespace",
            "${my_resolver:cat\\, do g}",
            ("cat, do g",),
        ),
        (lambda: "zero", "zero_arg", "${my_resolver:}", "zero"),
    ],
)
def test_resolver_that_allows_a_list_of_arguments(
    restore_resolvers: Any, resolver: Resolver, name: str, key: str, result: Any
) -> None:
    OmegaConf.register_resolver("my_resolver", resolver)
    c = OmegaConf.create({name: key})
    assert isinstance(c, DictConfig)
    assert c[name] == result


def test_copy_cache(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    d = {"k": "${random:_}"}
    c1 = OmegaConf.create(d)
    assert c1.k == c1.k

    c2 = OmegaConf.create(d)
    assert c2.k != c1.k
    OmegaConf.set_cache(c2, OmegaConf.get_cache(c1))
    assert c2.k == c1.k

    c3 = OmegaConf.create(d)

    assert c3.k != c1.k
    OmegaConf.copy_cache(c1, c3)
    assert c3.k == c1.k


def test_clear_cache(restore_resolvers: Any) -> None:
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create(dict(k="${random:_}"))
    old = c.k
    OmegaConf.clear_cache(c)
    assert old != c.k


def test_supported_chars() -> None:
    supported_chars = "%_-abc123."
    c = OmegaConf.create(dict(dir1="${copy:" + supported_chars + "}"))

    OmegaConf.register_resolver("copy", lambda x: x)
    assert c.dir1 == supported_chars


def test_interpolation_in_list_key_error() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(["${10}"])
    assert isinstance(c, ListConfig)

    with pytest.raises(KeyError):
        c[0]


def test_unsupported_interpolation_type() -> None:
    c = OmegaConf.create(dict(foo="${wrong_type:ref}"))

    with pytest.raises(ValueError):
        c.foo


def test_incremental_dict_with_interpolation() -> None:
    conf = OmegaConf.create()
    assert isinstance(conf, DictConfig)
    conf.a = 1
    conf.b = OmegaConf.create()
    assert isinstance(conf.b, DictConfig)
    conf.b.c = "${a}"
    assert conf.b.c == conf.a  # type: ignore


@pytest.mark.parametrize(  # type: ignore
    "cfg,key,expected",
    [
        ({"a": 10, "b": "${a}"}, "b", 10),
        ({"a": 10, "b": "${a}", "c": "${b}"}, "c", 10),
        ({"bar": 10, "foo": ["${bar}"]}, "foo.0", 10),
        ({"foo": None, "bar": "${foo}"}, "bar", None),
        ({"list": ["bar"], "foo": "${list.0}"}, "foo", "bar"),
        ({"list": ["${ref}"], "ref": "bar"}, "list.0", "bar"),
    ],
)
def test_interpolations(cfg: DictConfig, key: str, expected: Any) -> None:
    c = OmegaConf.create(cfg)
    assert OmegaConf.select(c, key) == expected


def test_interpolation_with_missing() -> None:
    cfg = OmegaConf.create({"out_file": "${x.name}.txt", "x": {"name": "???"}})
    assert OmegaConf.is_missing(cfg, "out_file")


def test_assign_to_interpolation() -> None:
    cfg = OmegaConf.create(
        {"foo": 10, "bar": "${foo}", "typed_bar": IntegerNode("${foo}")}
    )
    assert OmegaConf.is_interpolation(cfg, "bar")
    assert cfg.bar == 10
    assert cfg.typed_bar == 10

    # assign regular field
    cfg.bar = 20
    assert not OmegaConf.is_interpolation(cfg, "bar")

    with pytest.raises(ValidationError):
        cfg.typed_bar = "nope"
    cfg.typed_bar = 30

    assert cfg.foo == 10
    assert cfg.bar == 20
    assert cfg.typed_bar == 30


def test_merge_with_interpolation() -> None:
    cfg = OmegaConf.create(
        {"foo": 10, "bar": "${foo}", "typed_bar": IntegerNode("${foo}")}
    )

    assert OmegaConf.merge(cfg, {"bar": 20}) == {"foo": 10, "bar": 20, "typed_bar": 10}
    assert OmegaConf.merge(cfg, {"typed_bar": 30}) == {
        "foo": 10,
        "bar": 10,
        "typed_bar": 30,
    }

    with pytest.raises(ValidationError):
        OmegaConf.merge(cfg, {"typed_bar": "nope"})


def test_non_container_interpolation() -> None:
    cfg = OmegaConf.create(dict(foo=0, bar="${foo.baz}"))
    with pytest.raises(AssertionError):
        cfg.bar


def test_indirect_interpolation() -> None:
    d = {
        "a": {"aa": 10},
        "b": "${a}",
        "c": "${b.aa}",
    }

    cfg = OmegaConf.create(d)
    assert cfg.c == 10
    assert OmegaConf.to_container(cfg, resolve=True) == {
        "a": {"aa": 10},
        "b": {"aa": 10},
        "c": 10,
    }


def test_indirect_interpolation2() -> None:
    d = {
        "a": {"aa": 10},
        "b": "${a.aa}",
        "c": "${b}",
    }

    cfg = OmegaConf.create(d)
    assert cfg.c == 10

    assert OmegaConf.to_container(cfg, resolve=True) == {
        "a": {"aa": 10},
        "b": 10,
        "c": 10,
    }
