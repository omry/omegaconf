import os
import random
import re
from typing import Any, Optional, Tuple

import pytest
from _pytest.python_api import RaisesContext

from omegaconf import Container, IntegerNode, Node, OmegaConf, Resolver, ValidationError
from omegaconf._utils import _ensure_container


@pytest.mark.parametrize(  # type:ignore
    "cfg,key,expected",
    [
        pytest.param({"a": "${b}", "b": 10}, "a", 10, id="simple"),
        pytest.param({"a": "${x}"}, "a", pytest.raises(KeyError), id="not_found"),
        pytest.param({"a": "${x.y}"}, "a", pytest.raises(KeyError), id="not_found"),
        pytest.param({"a": "foo_${b}", "b": "bar"}, "a", "foo_bar", id="str_inter"),
        pytest.param(
            {"a": "${x}_${y}", "x": "foo", "y": "bar"},
            "a",
            "foo_bar",
            id="multi_str_inter",
        ),
        pytest.param(
            {"a": "foo_${b.c}", "b": {"c": 10}}, "a", "foo_10", id="str_deep_inter"
        ),
        pytest.param({"a": 10, "b": [1, "${a}"]}, "b.1", 10, id="from_list"),
        pytest.param({"a": "${b}", "b": {"c": 10}}, "a", {"c": 10}, id="dict_val"),
        pytest.param({"a": "${b}", "b": [1, 2]}, "a", [1, 2], id="list_val"),
        pytest.param({"a": "${b.1}", "b": [1, 2]}, "a", 2, id="list_index"),
        pytest.param({"a": "X_${b}", "b": [1, 2]}, "a", "X_[1, 2]", id="liststr"),
        pytest.param({"a": "X_${b}", "b": {"c": 1}}, "a", "X_{'c': 1}", id="dict_str"),
        pytest.param({"a": "${b}", "b": "${c}", "c": 10}, "a", 10, id="two_steps"),
        pytest.param({"bar": 10, "foo": ["${bar}"]}, "foo.0", 10, id="inter_in_list"),
        pytest.param({"foo": None, "bar": "${foo}"}, "bar", None, id="none"),
        pytest.param({"list": ["bar"], "foo": "${list.0}"}, "foo", "bar", id="list"),
        # relative interpolations
        pytest.param({"a": "${.b}", "b": 10}, "a", 10, id="relative"),
        pytest.param({"a": {"z": "${.b}", "b": 10}}, "a.z", 10, id="relative"),
        pytest.param({"a": {"z": "${..b}"}, "b": 10}, "a.z", 10, id="relative"),
        pytest.param({"a": {"z": "${..a.b}", "b": 10}}, "a.z", 10, id="relative"),
        pytest.param(
            {"a": "${..b}", "b": 10}, "a", pytest.raises(KeyError), id="relative"
        ),
    ],
)
def test_interpolation(cfg: Any, key: str, expected: Any) -> None:
    cfg = _ensure_container(cfg)
    if isinstance(expected, RaisesContext):
        with expected:
            OmegaConf.select(cfg, key)
    else:
        assert OmegaConf.select(cfg, key) == expected


def test_interpolation_with_missing() -> None:
    cfg = OmegaConf.create(
        {"a": "${x.missing}.txt", "b": "${x.missing}", "x": {"missing": "???"}}
    )
    assert OmegaConf.is_missing(cfg, "a")
    assert OmegaConf.is_missing(cfg, "b")


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
        {
            "foo": 10,
            "bar": "${foo}",
            "typed_bar": IntegerNode("${foo}"),
        }
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


@pytest.mark.parametrize(  # type:ignore
    "cfg",
    [
        pytest.param({"a": "${b}", "b": "string", "s": "foo_${b}"}, id="str"),
        pytest.param({"a": "${b}", "b": True, "s": "foo_${b}"}, id="bool"),
        pytest.param({"a": "${b}", "b": 10, "s": "foo_${b}"}, id="int"),
        pytest.param({"a": "${b}", "b": 3.14, "s": "foo_${b}"}, id="float"),
    ],
)
def test_type_inherit_type(cfg: Any) -> None:
    cfg = _ensure_container(cfg)
    assert isinstance(cfg.a, type(cfg.b))
    assert type(cfg.s) == str  # check that string interpolations are always strings


@pytest.mark.parametrize(  # type:ignore
    "cfg,env_name,env_val,key,expected",
    [
        pytest.param(
            {"path": "/test/${env:foo}"},
            "foo",
            "1234",
            "path",
            "/test/1234",
            id="simple",
        ),
        pytest.param(
            {"path": "/test/${env:not_found}"},
            None,
            None,
            "path",
            pytest.raises(
                ValidationError,
                match=re.escape("Environment variable 'not_found' not found"),
            ),
            id="not_found",
        ),
        pytest.param(
            {"path": "/test/${env:not_found,ZZZ}"},
            None,
            None,
            "path",
            "/test/ZZZ",
            id="not_found_with_default",
        ),
        pytest.param(
            {"path": "/test/${env:not_found,a/b}"},
            None,
            None,
            "path",
            "/test/a/b",
            id="not_found_with_default",
        ),
    ],
)
def test_env_interpolation(
    monkeypatch: Any,
    cfg: Any,
    env_name: Optional[str],
    env_val: str,
    key: str,
    expected: Any,
) -> None:
    if env_name is not None:
        monkeypatch.setenv(env_name, env_val)

    cfg = _ensure_container(cfg)
    if isinstance(expected, RaisesContext):
        with expected:
            OmegaConf.select(cfg, key)
    else:
        assert OmegaConf.select(cfg, key) == expected


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
    c = OmegaConf.create({"k": "${plus_10:990}"})

    assert type(c.k) == int
    assert c.k == 1000


def test_resolver_cache_1(restore_resolvers: Any) -> None:
    # resolvers are always converted to stateless idempotent functions
    # subsequent calls to the same function with the same argument will always return the same value.
    # this is important to allow embedding of functions like time() without having the value change during
    # the program execution.
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create({"k": "${random:_}"})
    assert c.k == c.k


def test_resolver_cache_2(restore_resolvers: Any) -> None:
    """
    Tests that resolver cache is not shared between different OmegaConf objects
    """
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c1 = OmegaConf.create({"k": "${random:_}"})
    c2 = OmegaConf.create({"k": "${random:_}"})

    assert c1.k != c2.k
    assert c1.k == c1.k
    assert c2.k == c2.k


def test_resolver_dot_start(restore_resolvers: Any) -> None:
    """
    Regression test for #373
    """
    OmegaConf.register_resolver("identity", lambda x: x)
    c = OmegaConf.create(
        {"foo_nodot": "${identity:bar}", "foo_dot": "${identity:.bar}"}
    )
    assert c.foo_nodot == "bar"
    assert c.foo_dot == ".bar"


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

    with pytest.raises(KeyError):
        c[0]


def test_unsupported_interpolation_type() -> None:
    c = OmegaConf.create({"foo": "${wrong_type:ref}"})
    with pytest.raises(ValueError):
        c.foo


def test_incremental_dict_with_interpolation() -> None:
    conf = OmegaConf.create()
    conf.a = 1
    conf.b = OmegaConf.create()
    conf.b.c = "${a}"
    assert conf.b.c == conf.a  # type:ignore


@pytest.mark.parametrize(  # type: ignore
    "cfg,node_key,key,expected",
    [
        pytest.param({"a": 10}, "", "", ({"a": 10}, "")),
        pytest.param({"a": 10}, "", ".", ({"a": 10}, "")),
        pytest.param({"a": 10}, "", "a", ({"a": 10}, "a")),
        pytest.param({"a": 10}, "", ".a", ({"a": 10}, "a")),
        pytest.param({"a": {"b": 10}}, "a", ".", ({"b": 10}, "")),
        pytest.param({"a": {"b": 10}}, "a", ".b", ({"b": 10}, "b")),
        pytest.param({"a": {"b": 10}}, "a", "..", ({"a": {"b": 10}}, "")),
        pytest.param({"a": {"b": 10}}, "a", "..a", ({"a": {"b": 10}}, "a")),
        pytest.param({"a": {"b": {"c": 10}}}, "a.b", ".", ({"c": 10}, "")),
        pytest.param({"a": {"b": {"c": 10}}}, "a.b", "..", ({"b": {"c": 10}}, "")),
        pytest.param(
            {"a": {"b": {"c": 10}}}, "a.b", "...", ({"a": {"b": {"c": 10}}}, "")
        ),
    ],
)
def test_resolve_key_and_root(
    cfg: Any, node_key: str, key: str, expected: Tuple[Node, str]
) -> None:
    cfg = _ensure_container(cfg)
    node: Container = OmegaConf.select(cfg, node_key)
    assert node._resolve_key_and_root(key) == expected
