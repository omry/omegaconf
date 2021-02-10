import copy
import math
import random
import re
from typing import Any, Callable, List, Optional, Tuple

import antlr4
import pytest
from _pytest.python_api import RaisesContext

from omegaconf import (
    II,
    Container,
    DictConfig,
    IntegerNode,
    ListConfig,
    Node,
    OmegaConf,
    Resolver,
    ValidationError,
    grammar_parser,
)
from omegaconf._utils import _ensure_container, _get_value
from omegaconf.errors import (
    ConfigAttributeError,
    GrammarParseError,
    InterpolationResolutionError,
    OmegaConfBaseException,
    UnsupportedInterpolationType,
)
from omegaconf.grammar_visitor import GrammarVisitor

from . import StructuredWithMissing

# A fixed config that may be used (but not modified!) by tests.
BASE_TEST_CFG = OmegaConf.create(
    {
        # Standard data types.
        "str": "hi",
        "int": 123,
        "float": 1.2,
        "dict": {"a": 0},
        "list": [x - 1 for x in range(11)],
        "null": None,
        # Special cases.
        "x@y": 123,  # to test keys with @ in name
        "0": 0,  # to test keys with int names
        "1": {"2": 12},  # to test dot-path with int keys
        "FalsE": {"TruE": True},  # to test keys with bool names
        "None": {"null": 1},  # to test keys with null-like names
        # Used in nested interpolations.
        "str_test": "test",
        "ref_str": "str",
        "options": {"a": "A", "b": "B"},
        "choice": "a",
        "rel_opt": ".options",
    }
)


# Characters that are not allowed by the grammar in config key names.
INVALID_CHARS_IN_KEY_NAMES = "\\${}()[].: '\""


@pytest.mark.parametrize(
    "cfg,key,expected",
    [
        pytest.param({"a": "${b}", "b": 10}, "a", 10, id="simple"),
        pytest.param(
            {"a": "${x}"},
            "a",
            pytest.raises(InterpolationResolutionError),
            id="not_found",
        ),
        pytest.param(
            {"a": "${x.y}"},
            "a",
            pytest.raises(InterpolationResolutionError),
            id="not_found",
        ),
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
        pytest.param(
            {"user@domain": 10, "foo": "${user@domain}"}, "foo", 10, id="user@domain"
        ),
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
        {
            "a": "${x.missing}.txt",
            "b": "${x.missing}",
            "x": {"missing": "???"},
        }
    )
    assert not OmegaConf.is_missing(cfg, "a")
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
    with pytest.raises(ConfigAttributeError):
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


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
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


def test_env_is_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("foobar", "1234")
    c = OmegaConf.create({"foobar": "${env:foobar}"})
    before = c.foobar
    monkeypatch.setenv("foobar", "3456")
    assert c.foobar == before


@pytest.mark.parametrize(
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
        # more advanced uses of the grammar
        ("ab \\{foo} cd", "ab \\{foo} cd"),
        ("ab \\\\{foo} cd", "ab \\\\{foo} cd"),
        ("'\\${other_key}'", "${other_key}"),  # escaped interpolation
        ("'ab \\${other_key} cd'", "ab ${other_key} cd"),  # escaped interpolation
        ("[1, 2, 3]", [1, 2, 3]),
        ("{a: 0, b: 1}", {"a": 0, "b": 1}),
        ("  123  ", "  123  "),
        ("  1 2 3  ", "  1 2 3  "),
        ("\t[1, 2, 3]\t", "\t[1, 2, 3]\t"),
        ("[\t1, 2, 3\t]", [1, 2, 3]),
        ("   {a: b}\t  ", "   {a: b}\t  "),
        ("{   a: b\t  }", {"a": "b"}),
        ("'123'", "123"),
        ("${env:my_key_2}", 456),  # can call another resolver
    ],
)
def test_env_values_are_typed(monkeypatch: Any, value: Any, expected: Any) -> None:
    monkeypatch.setenv("my_key", value)
    monkeypatch.setenv("my_key_2", "456")
    c = OmegaConf.create(dict(my_key="${env:my_key}"))
    assert c.my_key == expected


def test_env_node_interpolation(monkeypatch: Any) -> None:
    # Test that node interpolations are not supported in env variables.
    monkeypatch.setenv("my_key", "${other_key}")
    c = OmegaConf.create(dict(my_key="${env:my_key}", other_key=123))
    with pytest.raises(InterpolationResolutionError):
        c.my_key


def test_env_default_none(monkeypatch: Any) -> None:
    monkeypatch.delenv("my_key", raising=False)
    c = OmegaConf.create({"my_key": "${env:my_key, null}"})
    assert c.my_key is None


def test_register_resolver_twice_error(restore_resolvers: Any) -> None:
    def foo(_: Any) -> int:
        return 10

    OmegaConf.register_new_resolver("foo", foo)
    with pytest.raises(AssertionError):
        OmegaConf.register_new_resolver("foo", lambda _: 10)


def test_register_resolver_twice_error_legacy(restore_resolvers: Any) -> None:
    def foo() -> int:
        return 10

    OmegaConf.legacy_register_resolver("foo", foo)
    with pytest.raises(AssertionError):
        OmegaConf.register_new_resolver("foo", lambda: 10)


def test_clear_resolvers(restore_resolvers: Any) -> None:
    assert OmegaConf.get_resolver("foo") is None
    OmegaConf.register_new_resolver("foo", lambda x: x + 10)
    assert OmegaConf.get_resolver("foo") is not None
    OmegaConf.clear_resolvers()
    assert OmegaConf.get_resolver("foo") is None


def test_clear_resolvers_legacy(restore_resolvers: Any) -> None:
    assert OmegaConf.get_resolver("foo") is None
    OmegaConf.legacy_register_resolver("foo", lambda x: int(x) + 10)
    assert OmegaConf.get_resolver("foo") is not None
    OmegaConf.clear_resolvers()
    assert OmegaConf.get_resolver("foo") is None


def test_register_resolver_1(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("plus_10", lambda x: x + 10)
    c = OmegaConf.create(
        {"k": "${plus_10:990}", "node": {"bar": 10, "foo": "${plus_10:${.bar}}"}}
    )

    assert type(c.k) == int
    assert c.k == 1000
    assert c.node.foo == 20  # this also tests relative interpolations with resolvers


def test_register_resolver_1_legacy(restore_resolvers: Any) -> None:
    OmegaConf.legacy_register_resolver("plus_10", lambda x: int(x) + 10)
    c = OmegaConf.create({"k": "${plus_10:990}"})

    assert type(c.k) == int
    assert c.k == 1000


def test_resolver_cache_1(restore_resolvers: Any) -> None:
    # resolvers are always converted to stateless idempotent functions
    # subsequent calls to the same function with the same argument will always return the same value.
    # this is important to allow embedding of functions like time() without having the value change during
    # the program execution.
    OmegaConf.register_new_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create({"k": "${random:__}"})
    assert c.k == c.k


def test_resolver_cache_1_legacy(restore_resolvers: Any) -> None:
    OmegaConf.legacy_register_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create({"k": "${random:_}"})
    assert c.k == c.k


def test_resolver_cache_2(restore_resolvers: Any) -> None:
    """
    Tests that resolver cache is not shared between different OmegaConf objects
    """
    OmegaConf.register_new_resolver("random", lambda _: random.randint(0, 10000000))
    c1 = OmegaConf.create({"k": "${random:__}"})
    c2 = OmegaConf.create({"k": "${random:__}"})

    assert c1.k != c2.k
    assert c1.k == c1.k
    assert c2.k == c2.k


def test_resolver_cache_2_legacy(restore_resolvers: Any) -> None:
    OmegaConf.legacy_register_resolver("random", lambda _: random.randint(0, 10000000))
    c1 = OmegaConf.create({"k": "${random:_}"})
    c2 = OmegaConf.create({"k": "${random:_}"})

    assert c1.k != c2.k
    assert c1.k == c1.k
    assert c2.k == c2.k


def test_resolver_cache_3_dict_list(restore_resolvers: Any) -> None:
    """
    Tests that the resolver cache works as expected with lists and dicts.
    """
    OmegaConf.register_new_resolver("random", lambda _: random.uniform(0, 1))
    c = OmegaConf.create(
        dict(
            lst1="${random:[0, 1]}",
            lst2="${random:[0, 1]}",
            lst3="${random:[]}",
            dct1="${random:{a: 1, b: 2}}",
            dct2="${random:{b: 2, a: 1}}",
            mixed1="${random:{x: [1.1], y: {a: true, b: false, c: null, d: []}}}",
            mixed2="${random:{x: [1.1], y: {b: false, c: null, a: true, d: []}}}",
        )
    )
    assert c.lst1 == c.lst1
    assert c.lst1 == c.lst2
    assert c.lst1 != c.lst3
    assert c.dct1 == c.dct1
    assert c.dct1 == c.dct2
    assert c.mixed1 == c.mixed1
    assert c.mixed2 == c.mixed2
    assert c.mixed1 == c.mixed2


def test_resolver_no_cache(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver(
        "random", lambda _: random.uniform(0, 1), use_cache=False
    )
    c = OmegaConf.create(dict(k="${random:__}"))
    assert c.k != c.k


def test_resolver_dot_start(restore_resolvers: Any) -> None:
    """
    Regression test for #373
    """
    OmegaConf.register_new_resolver("identity", lambda x: x)
    c = OmegaConf.create(
        {"foo_nodot": "${identity:bar}", "foo_dot": "${identity:.bar}"}
    )
    assert c.foo_nodot == "bar"
    assert c.foo_dot == ".bar"


def test_resolver_dot_start_legacy(restore_resolvers: Any) -> None:
    OmegaConf.legacy_register_resolver("identity", lambda x: x)
    c = OmegaConf.create(
        {"foo_nodot": "${identity:bar}", "foo_dot": "${identity:.bar}"}
    )
    assert c.foo_nodot == "bar"
    assert c.foo_dot == ".bar"


@pytest.mark.parametrize(
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
            "${my_resolver:cat,\\ do g}",
            ("cat", " do g"),
        ),
        (lambda: "zero", "zero_arg", "${my_resolver:}", "zero"),
    ],
)
def test_resolver_that_allows_a_list_of_arguments(
    restore_resolvers: Any, resolver: Resolver, name: str, key: str, result: Any
) -> None:
    OmegaConf.register_new_resolver("my_resolver", resolver)
    c = OmegaConf.create({name: key})
    assert c[name] == result


@pytest.mark.parametrize(
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
            "${my_resolver:cat,\\ do g}",
            ("cat", " do g"),
        ),
        (lambda: "zero", "zero_arg", "${my_resolver:}", "zero"),
    ],
)
def test_resolver_that_allows_a_list_of_arguments_legacy(
    restore_resolvers: Any, resolver: Resolver, name: str, key: str, result: Any
) -> None:
    OmegaConf.legacy_register_resolver("my_resolver", resolver)
    c = OmegaConf.create({name: key})
    assert c[name] == result


def test_resolver_deprecated_behavior(restore_resolvers: Any) -> None:
    # Ensure that resolvers registered with the old "register_resolver()" function
    # behave as expected.

    # The registration should trigger a deprecation warning.
    # with pytest.warns(UserWarning):  # TODO re-enable this check with the warning
    OmegaConf.register_resolver("my_resolver", lambda *args: args)

    c = OmegaConf.create(
        {
            "int": "${my_resolver:1}",
            "null": "${my_resolver:null}",
            "bool": "${my_resolver:TruE,falSE}",
            "str": "${my_resolver:a,b,c}",
            "inter": "${my_resolver:${int}}",
        }
    )

    # All resolver arguments should be provided as strings (with no modification).
    assert c.int == ("1",)
    assert c.null == ("null",)
    assert c.bool == ("TruE", "falSE")
    assert c.str == ("a", "b", "c")

    # Trying to nest interpolations should trigger an error (users should switch to
    # `register_new_resolver()` in order to use nested interpolations).
    with pytest.raises(ValueError):
        c.inter


def test_copy_cache(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("random", lambda _: random.randint(0, 10000000))
    d = {"k": "${random:__}"}
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
    OmegaConf.register_new_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create(dict(k="${random:__}"))
    old = c.k
    OmegaConf.clear_cache(c)
    assert old != c.k


def test_supported_chars() -> None:
    supported_chars = "abc123_/:-\\+.$%*@"
    c = OmegaConf.create(dict(dir1="${copy:" + supported_chars + "}"))

    OmegaConf.register_new_resolver("copy", lambda x: x)
    assert c.dir1 == supported_chars


def test_valid_chars_in_key_names() -> None:
    valid_chars = "".join(
        chr(i) for i in range(33, 128) if chr(i) not in INVALID_CHARS_IN_KEY_NAMES
    )
    cfg_dict = {valid_chars: 123, "inter": f"${{{valid_chars}}}"}
    cfg = OmegaConf.create(cfg_dict)
    # Test that we can access the node made of all valid characters, both
    # directly and through interpolations.
    assert cfg[valid_chars] == 123
    assert cfg.inter == 123


@pytest.mark.parametrize("c", list(INVALID_CHARS_IN_KEY_NAMES))
def test_invalid_chars_in_key_names(c: str) -> None:
    # Test that all invalid characters trigger errors in interpolations.
    cfg = OmegaConf.create({"invalid": f"${{ab{c}de}}"})
    error: type
    if c in [".", "}"]:
        # With '.', we try to access `${ab.de}`.
        # With "}", we try to access `${ab}`.
        error = InterpolationResolutionError
    elif c == ":":
        error = UnsupportedInterpolationType  # `${ab:de}`
    else:
        error = GrammarParseError  # other cases are all parse errors
    with pytest.raises(error):
        cfg.invalid


def test_interpolation_in_list_key_error() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(["${10}"])

    with pytest.raises(InterpolationResolutionError):
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


@pytest.mark.parametrize(
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


@pytest.mark.parametrize("copy_func", [copy.copy, copy.deepcopy])
@pytest.mark.parametrize(
    "data,key",
    [
        pytest.param({"a": 10, "b": "${a}"}, "b", id="dict"),
        pytest.param([10, "${0}"], 1, id="list"),
    ],
)
def test_interpolation_after_copy(copy_func: Any, data: Any, key: Any) -> None:
    dict_cfg = OmegaConf.create(data)
    assert copy_func(dict_cfg._get_node(key))._dereference_node() == 10


def test_resolve_interpolation_without_parent() -> None:
    with pytest.raises(OmegaConfBaseException):
        DictConfig(content="${foo}")._dereference_node()


def test_optional_after_interpolation() -> None:
    cfg = OmegaConf.structured(StructuredWithMissing(opt_num=II("num")))
    # Ensure that we can set an optional field to `None` even when it currently
    # points to a non-optional field.
    cfg.opt_num = None


def test_empty_stack() -> None:
    """
    Check that an empty stack during ANTLR parsing raises a `GrammarParseError`.
    """
    with pytest.raises(GrammarParseError):
        grammar_parser.parse("ab}", lexer_mode="VALUE_MODE")


def _maybe_create(definition: str) -> Any:
    """
    Helper function to create config objects for lists and dictionaries.
    """
    if isinstance(definition, (list, dict)):
        return OmegaConf.create(definition)
    return definition


# Parameters for tests of the "singleElement" rule when there is no interpolation.
# Each item is a tuple with three elements:
#   - The id of the test.
#   - The expression to be evaluated.
#   - The expected result, that may be an exception. If it is a `GrammarParseError` then
#     it is assumed that the parsing will fail. If it is another kind of exception then
#     it is assumed that the parsing will succeed, but this exception will be raised when
#     visiting (= evaluating) the parse tree. If the expected behavior is for the parsing
#     to succeed, but a `GrammarParseError` to be raised when visiting it, then set the
#     expected result to the pair `(None, GrammarParseError)`.
PARAMS_SINGLE_ELEMENT_NO_INTERPOLATION: List[Tuple[str, str, Any]] = [
    # Special keywords.
    ("null", "null", None),
    ("true", "TrUe", True),
    ("false", "falsE", False),
    ("true_false", "true_false", "true_false"),
    # Integers.
    ("int", "123", 123),
    ("int_pos", "+123", 123),
    ("int_neg", "-123", -123),
    ("int_underscore", "1_000", 1000),
    ("int_bad_underscore_1", "1_000_", "1_000_"),
    ("int_bad_underscore_2", "1__000", "1__000"),
    ("int_bad_underscore_3", "_1000", "_1000"),
    ("int_bad_zero_start", "007", "007"),
    # Floats.
    ("float", "1.1", 1.1),
    ("float_no_int", ".1", 0.1),
    ("float_no_decimal", "1.", 1.0),
    ("float_minus", "-.2", -0.2),
    ("float_underscore", "1.1_1", 1.11),
    ("float_bad_1", "1.+2", "1.+2"),
    ("float_bad_2", r"1\.2", r"1\.2"),
    ("float_bad_3", "1.2_", "1.2_"),
    ("float_exp_1", "-1e2", -100.0),
    ("float_exp_2", "+1E-2", 0.01),
    ("float_exp_3", "1_0e1_0", 10e10),
    ("float_exp_4", "1.07e+2", 107.0),
    ("float_exp_5", "1e+03", 1000.0),
    ("float_exp_bad_1", "e-2", "e-2"),
    ("float_exp_bad_2", "01e2", "01e2"),
    ("float_inf", "inf", math.inf),
    ("float_plus_inf", "+inf", math.inf),
    ("float_minus_inf", "-inf", -math.inf),
    ("float_nan", "nan", math.nan),
    ("float_plus_nan", "+nan", math.nan),
    ("float_minus_nan", "-nan", math.nan),
    # Unquoted strings.
    ("str_legal", "a/-\\+.$*@\\\\", "a/-\\+.$*@\\"),
    ("str_illegal_1", "a,=b", GrammarParseError),
    ("str_illegal_2", f"{chr(200)}", GrammarParseError),
    ("str_illegal_3", f"{chr(129299)}", GrammarParseError),
    ("str_dot", ".", "."),
    ("str_dollar", "$", "$"),
    ("str_colon", ":", ":"),
    ("str_ws_1", "hello world", "hello world"),
    ("str_ws_2", "a b\tc  \t\t  d", "a b\tc  \t\t  d"),
    ("str_esc_ws_1", r"\ hello\ world\ ", " hello world "),
    ("str_esc_ws_2", "\\ \\\t\\\t", " \t\t"),
    ("str_esc_comma", r"hello\, world", "hello, world"),
    ("str_esc_colon", r"a\:b", "a:b"),
    ("str_esc_equal", r"a\=b", "a=b"),
    ("str_esc_parentheses", r"\(foo\)", "(foo)"),
    ("str_esc_brackets", r"\[foo\]", "[foo]"),
    ("str_esc_braces", r"\{foo\}", "{foo}"),
    ("str_esc_backslash", r"\\", "\\"),
    ("str_backslash_noesc", r"ab\cd", r"ab\cd"),
    ("str_esc_illegal_1", r"\#", GrammarParseError),
    ("str_esc_illegal_2", "\\'\\\"", GrammarParseError),
    # Quoted strings.
    ("str_quoted_single", "'!@#$%^&*()[]:.,\"'", '!@#$%^&*()[]:.,"'),
    ("str_quoted_double", '"!@#$%^&*()[]:.,\'"', "!@#$%^&*()[]:.,'"),
    ("str_quoted_outer_ws_single", "'  a \t'", "  a \t"),
    ("str_quoted_outer_ws_double", '"  a \t"', "  a \t"),
    ("str_quoted_int", "'123'", "123"),
    ("str_quoted_null", "'null'", "null"),
    ("str_quoted_bool", "['truE', \"FalSe\"]", ["truE", "FalSe"]),
    ("str_quoted_list", "'[a,b, c]'", "[a,b, c]"),
    ("str_quoted_dict", '"{a:b, c: d}"', "{a:b, c: d}"),
    ("str_quoted_backslash_noesc_single", r"'a\b'", r"a\b"),
    ("str_quoted_backslash_noesc_double", r'"a\b"', r"a\b"),
    ("str_quoted_concat_bad_2", "'Hi''there'", GrammarParseError),
    ("str_quoted_too_many_1", "''a'", GrammarParseError),
    ("str_quoted_too_many_2", "'a''", GrammarParseError),
    ("str_quoted_too_many_3", "''a''", GrammarParseError),
    # Lists and dictionaries.
    ("list", "[0, 1]", [0, 1]),
    (
        "dict",
        "{x: 1, a: b, y: 1e2, null2: 0.1, true3: false, inf4: true}",
        {"x": 1, "a": "b", "y": 100.0, "null2": 0.1, "true3": False, "inf4": True},
    ),
    (
        "dict_unquoted_key",
        "{a0-null-1-3.14-NaN- \t-true-False-/\\+.$%*@\\(\\)\\[\\]\\{\\}\\:\\=\\ \\\t\\,:0}",
        {"a0-null-1-3.14-NaN- \t-true-False-/\\+.$%*@()[]{}:= \t,": 0},
    ),
    (
        "dict_quoted",
        "{0: 1, 'a': 'b', 1.1: 1e2, null: 0.1, true: false, -inf: true}",
        {0: 1, "a": "b", 1.1: 100.0, None: 0.1, True: False, -math.inf: True},
    ),
    (
        "structured_mixed",
        "[10,str,3.14,true,false,inf,[1,2,3], 'quoted', \"quoted\", 'a,b,c']",
        [
            10,
            "str",
            3.14,
            True,
            False,
            math.inf,
            [1, 2, 3],
            "quoted",
            "quoted",
            "a,b,c",
        ],
    ),
    ("dict_int_key", "{0: 0}", {0: 0}),
    ("dict_float_key", "{1.1: 0}", {1.1: 0}),
    ("dict_null_key", "{null: 0}", {None: 0}),
    ("dict_nan_like_key", "{'nan': 0}", {"nan": 0}),
    ("dict_list_as_key", "{[0]: 1}", GrammarParseError),
    (
        "dict_bool_key",
        "{true: true, false: 'false'}",
        {True: True, False: "false"},
    ),
    ("empty_dict", "{}", {}),
    ("empty_list", "[]", []),
    (
        "structured_deep",
        "{null0: [0, 3.14, false], true1: {a: [0, 1, 2], b: {}}}",
        {"null0": [0, 3.14, False], "true1": {"a": [0, 1, 2], "b": {}}},
    ),
]

# Parameters for tests of the "singleElement" rule when there are interpolations.
PARAMS_SINGLE_ELEMENT_WITH_INTERPOLATION = [
    # Node interpolations.
    ("dict_access", "${dict.a}", 0),
    ("list_access", "${list.0}", -1),
    ("list_access_underscore", "${list.1_0}", 9),
    ("list_access_bad_negative", "${list.-1}", InterpolationResolutionError),
    ("dict_access_list_like_1", "${0}", 0),
    ("dict_access_list_like_2", "${1.2}", 12),
    ("bool_like_keys", "${FalsE.TruE}", True),
    ("null_like_key_ok", "${None.null}", 1),
    ("null_like_key_bad_case", "${NoNe.null}", InterpolationResolutionError),
    ("null_like_key_quoted_1", "${'None'.'null'}", GrammarParseError),
    ("null_like_key_quoted_2", "${'None.null'}", GrammarParseError),
    ("dotpath_bad_type", "${dict.${float}}", (None, GrammarParseError)),
    ("at_in_key", "${x@y}", 123),
    # Interpolations in dictionaries.
    ("dict_interpolation_value", "{hi: ${str}, int: ${int}}", {"hi": "hi", "int": 123}),
    ("dict_interpolation_key", "{${str}: 0, ${null}: 1", GrammarParseError),
    # Interpolations in lists.
    ("list_interpolation", "[${str}, ${int}]", ["hi", 123]),
    # Interpolations in unquoted strings.
    ("str_dollar_and_inter", "$$${str}", "$$hi"),
    ("str_inter", "hi_${str}", "hi_hi"),
    ("str_esc_illegal_3", r"\${foo\}", GrammarParseError),
    # Interpolations in quoted strings.
    ("str_quoted_inter", "'${null}'", "None"),
    ("str_quoted_esc_single_1", r"'ab\'cd\'\'${str}'", "ab'cd''hi"),
    ("str_quoted_esc_single_2", "'\"\\\\\\\\\\${foo}\\ '", r'"\${foo}\ '),
    ("str_quoted_esc_double_1", r'"ab\"cd\"\"${str}"', 'ab"cd""hi'),
    ("str_quoted_esc_double_2", '"\'\\\\\\\\\\${foo}\\ "', r"'\${foo}\ "),
    ("str_quoted_concat_bad_1", '"Hi "${str}', GrammarParseError),
    # Whitespaces.
    ("ws_inter_node_outer", "${ \tdict.a  \t}", 0),
    ("ws_inter_node_around_dot", "${dict .\ta}", 0),
    ("ws_inter_node_inside_id", "${d i c t.a}", GrammarParseError),
    ("ws_inter_res_outer", "${\t test:foo\t  }", "foo"),
    ("ws_inter_res_around_colon", "${test\t  : \tfoo}", "foo"),
    ("ws_inter_res_inside_id", "${te st:foo}", GrammarParseError),
    ("ws_inter_res_inside_args", "${test:f o o}", "f o o"),
    ("ws_list", "${test:[\t a,   b,  ''\t  ]}", ["a", "b", ""]),
    ("ws_dict", "${test:{\t a   : 1\t  , b:  \t''}}", {"a": 1, "b": ""}),
    ("ws_quoted_single", "${test:  \t'foo'\t }", "foo"),
    ("ws_quoted_double", '${test:  \t"foo"\t }', "foo"),
    # Nested interpolations.
    ("nested_simple", "${${ref_str}}", "hi"),
    ("nested_select", "${options.${choice}}", "A"),
    ("nested_relative", "${${rel_opt}.b}", "B"),
    ("str_quoted_nested", r"'AB${test:\'CD${test:\\'EF\\'}GH\'}'", "ABCDEFGH"),
    # Resolver interpolations.
    ("no_args", "${test:}", []),
    ("space_in_args", "${test:a, b c}", ["a", "b c"]),
    ("list_as_input", "${test:[a, b], 0, [1.1]}", [["a", "b"], 0, [1.1]]),
    ("dict_as_input", "${test:{a: 1.1, b: b}}", {"a": 1.1, "b": "b"}),
    ("dict_as_input_quotes", "${test:{'a': 1.1, b: b}}", {"a": 1.1, "b": "b"}),
    ("dict_typo_colons", "${test:{a: 1.1, b:: b}}", {"a": 1.1, "b": ": b"}),
    ("missing_resolver", "${MiSsInG_ReSoLvEr:0}", UnsupportedInterpolationType),
    ("at_in_resolver", "${y@z:}", GrammarParseError),
    # Nested resolvers.
    ("nested_resolver", "${${str_test}:a, b, c}", ["a", "b", "c"]),
    ("nested_deep", "${test:${${test:${ref_str}}}}", "hi"),
    (
        "nested_resolver_combined_illegal",
        "${some_${resolver}:a, b, c}",
        GrammarParseError,
    ),
    ("nested_args", "${test:${str}, ${null}, ${int}}", ["hi", None, 123]),
    # Invalid resolver names.
    ("int_resolver_quoted", "${'0':1,2,3}", GrammarParseError),
    ("int_resolver_noquote", "${0:1,2,3}", GrammarParseError),
    ("float_resolver_quoted", "${'1.1':1,2,3}", GrammarParseError),
    ("float_resolver_noquote", "${1.1:1,2,3}", GrammarParseError),
    ("float_resolver_exp", "${1e1:1,2,3}", GrammarParseError),
    ("inter_float_resolver", "${${float}:1,2,3}", (None, GrammarParseError)),
    # NaN as dictionary key (a resolver is used here to output only the key).
    ("dict_nan_key_1", "${first:{nan: 0}}", math.nan),
    ("dict_nan_key_2", "${first:{${test:nan}: 0}}", GrammarParseError),
]

# Parameters for tests of the "configValue" rule (may contain node
# interpolations, but no resolvers).
PARAMS_CONFIG_VALUE = [
    # String interpolations (top-level).
    ("str_top_basic", "bonjour ${str}", "bonjour hi"),
    ("str_top_quotes_single_1", "'bonjour ${str}'", "'bonjour hi'"),
    (
        "str_top_quotes_single_2",
        "'Bonjour ${str}', I said.",
        "'Bonjour hi', I said.",
    ),
    ("str_top_quotes_double_1", '"bonjour ${str}"', '"bonjour hi"'),
    (
        "str_top_quotes_double_2",
        '"Bonjour ${str}", I said.',
        '"Bonjour hi", I said.',
    ),
    ("str_top_missing_end_quote_single", "'${str}", "'hi"),
    ("str_top_missing_end_quote_double", '"${str}', '"hi'),
    ("str_top_missing_start_quote_double", '${str}"', 'hi"'),
    ("str_top_missing_start_quote_single", "${str}'", "hi'"),
    ("str_top_middle_quote_single", "I'd like ${str}", "I'd like hi"),
    ("str_top_middle_quote_double", 'I"d like ${str}', 'I"d like hi'),
    ("str_top_middle_quotes_single", "I like '${str}'", "I like 'hi'"),
    ("str_top_middle_quotes_double", 'I like "${str}"', 'I like "hi"'),
    ("str_top_any_char", "${str} !@\\#$%^&*})][({,/?;", "hi !@\\#$%^&*})][({,/?;"),
    ("str_top_esc_inter", r"Esc: \${str}", "Esc: ${str}"),
    ("str_top_esc_inter_wrong_1", r"Wrong: $\{str\}", r"Wrong: $\{str\}"),
    ("str_top_esc_inter_wrong_2", r"Wrong: \${str\}", r"Wrong: ${str\}"),
    ("str_top_esc_backslash", r"Esc: \\${str}", r"Esc: \hi"),
    ("str_top_quoted_braces_wrong", r"Wrong: \{${str}\}", r"Wrong: \{hi\}"),
    ("str_top_leading_dollars", r"$$${str}", "$$hi"),
    ("str_top_trailing_dollars", r"${str}$$$$", "hi$$$$"),
    ("str_top_leading_escapes", r"\\\\\${str}", r"\\${str}"),
    ("str_top_middle_escapes", r"abc\\\\\${str}", r"abc\\${str}"),
    ("str_top_trailing_escapes", "${str}" + "\\" * 5, "hi" + "\\" * 3),
    ("str_top_concat_interpolations", "${null}${float}", "None1.2"),
    # Whitespaces.
    ("ws_toplevel", "  \tab  ${str} cd  ${int}\t", "  \tab  hi cd  123\t"),
    # Unmatched braces.
    ("missing_brace_1", "${test:${str}", GrammarParseError),
    ("missing_brace_2", "${${test:str}", GrammarParseError),
    ("extra_brace", "${str}}", "hi}"),
]


def parametrize_from(
    data: List[Tuple[str, str, Any]]
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """Utility function to create PyTest parameters from the lists above"""
    return pytest.mark.parametrize(
        ["definition", "expected"],
        [
            pytest.param(definition, expected, id=key)
            for key, definition, expected in data
        ],
    )


class TestInterpolationGrammar:
    """
    Test most grammar constructs.

    Each method in this class tests the validity of expressions in a specific
    setting. For instance, `test_single_element_no_interpolation()` tests the
    "singleElement" parsing rule on expressions that do not contain interpolations
    (which allows for faster tests without using any config object).

    Tests that actually need a config object all re-use the same `BASE_TEST_CFG`
    config, to avoid creating a new config for each test.
    """

    @parametrize_from(PARAMS_SINGLE_ELEMENT_NO_INTERPOLATION)
    def test_single_element_no_interpolation(
        self, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("singleElement", definition, expected)
        if parse_tree is None:
            return

        # Since there are no interpolations here, we do not need to provide
        # callbacks to resolve them, and the quoted string callback can simply
        # be the identity.
        visitor = GrammarVisitor(
            node_interpolation_callback=None,  # type: ignore
            resolver_interpolation_callback=None,  # type: ignore
            quoted_string_callback=lambda s: s,
        )
        self._visit(lambda: visitor.visit(parse_tree), expected_visit)

    @parametrize_from(PARAMS_SINGLE_ELEMENT_WITH_INTERPOLATION)
    def test_single_element_with_resolver(
        self, restore_resolvers: Any, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("singleElement", definition, expected)

        OmegaConf.register_new_resolver("test", self._resolver_test)
        OmegaConf.register_new_resolver("first", self._resolver_first)

        self._visit_with_config(parse_tree, expected_visit)

    @parametrize_from(PARAMS_CONFIG_VALUE)
    def test_config_value(
        self, restore_resolvers: Any, definition: str, expected: Any
    ) -> None:
        parse_tree, expected_visit = self._parse("configValue", definition, expected)
        self._visit_with_config(parse_tree, expected_visit)

    def _check_is_same_type(self, value: Any, expected: Any) -> None:
        """
        Helper function to validate that types of `value` and `expected are the same.

        This function assumes that `value == expected` holds, and performs a "deep"
        comparison of types (= it goes into data structures like dictionaries, lists
        and tuples).

        Note that dictionaries being compared must have keys ordered the same way!
        """
        assert type(value) is type(expected)
        if isinstance(value, (str, int, float)):
            pass
        elif isinstance(value, (list, tuple, ListConfig)):
            for vx, ex in zip(value, expected):
                self._check_is_same_type(vx, ex)
        elif isinstance(value, (dict, DictConfig)):
            for (vk, vv), (ek, ev) in zip(value.items(), expected.items()):
                assert vk == ek, "dictionaries are not ordered the same"
                self._check_is_same_type(vk, ek)
                self._check_is_same_type(vv, ev)
        elif value is None:
            assert expected is None
        else:
            raise NotImplementedError(type(value))

    def _get_expected(self, expected: Any) -> Tuple[Any, Any]:
        """Obtain the expected result of the parse & visit steps"""
        if isinstance(expected, tuple):
            # Outcomes of both the parse and visit steps are provided.
            assert len(expected) == 2
            return expected[0], expected[1]
        elif expected is GrammarParseError:
            # If only a `GrammarParseError` is expected, assume it happens in parse step.
            return expected, None
        else:
            # If anything else is provided, assume it is the outcome of the visit step.
            return None, expected

    def _get_lexer_mode(self, rule: str) -> str:
        return {"configValue": "DEFAULT_MODE", "singleElement": "VALUE_MODE"}[rule]

    def _parse(
        self, rule: str, definition: str, expected: Any
    ) -> Tuple[Optional[antlr4.ParserRuleContext], Any]:
        """
        Parse the expression given by `definition`.

        Return both the parse tree and the expected result when visiting this tree.
        """

        def get_tree() -> antlr4.ParserRuleContext:
            return grammar_parser.parse(
                value=definition,
                parser_rule=rule,
                lexer_mode=self._get_lexer_mode(rule),
            )

        expected_parse, expected_visit = self._get_expected(expected)
        if expected_parse is None:
            return get_tree(), expected_visit
        else:  # expected failure on the parse step
            with pytest.raises(expected_parse):
                get_tree()
            return None, None

    def _resolver_first(self, item: Any, *_: Any) -> Any:
        """Resolver that returns the first element of its first input"""
        return next(iter(item))

    def _resolver_test(self, *args: Any) -> Any:
        """Resolver that returns the list of its inputs"""
        return args[0] if len(args) == 1 else list(args)

    def _visit(self, visit: Callable[[], Any], expected: Any) -> None:
        """Run the `visit()` function to visit the parse tree and validate the result"""
        if isinstance(expected, type) and issubclass(expected, Exception):
            with pytest.raises(expected):
                visit()
        else:
            result = visit()
            if expected is math.nan:
                # Special case since nan != nan.
                assert math.isnan(result)
            else:
                assert result == expected
                # We also check types in particular because instances of `Node` are very
                # good at mimicking their underlying type's behavior, and it is easy to
                # fail to notice that the result contains nodes when it should not.
                self._check_is_same_type(result, expected)

    def _visit_with_config(
        self, parse_tree: antlr4.ParserRuleContext, expected: Any
    ) -> None:
        """Visit the tree using the default config `BASE_TEST_CFG`"""
        if parse_tree is None:
            return
        cfg = BASE_TEST_CFG

        def visit() -> Any:
            return _get_value(
                cfg.resolve_parse_tree(
                    parse_tree,
                    key=None,
                    parent=cfg,
                )
            )

        self._visit(visit, expected)
