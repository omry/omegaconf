import copy
import math
import os
import random
import re
from typing import Any, List, Optional, Tuple

import pytest
from _pytest.python_api import RaisesContext

from omegaconf import (
    II,
    SI,
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
from omegaconf._utils import _ensure_container
from omegaconf.errors import (
    ConfigAttributeError,
    GrammarParseError,
    InterpolationResolutionError,
    OmegaConfBaseException,
    UnsupportedInterpolationType,
)

from . import StructuredWithMissing, User

# file deepcode ignore CopyPasteError: there are several tests of the form `c.k == c.k`
# (this is intended to trigger multiple accesses to the same config key)


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


def test_env_is_cached() -> None:
    os.environ["foobar"] = "1234"
    c = OmegaConf.create({"foobar": "${env:foobar}"})
    before = c.foobar
    os.environ["foobar"] = "3456"
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
def test_env_values_are_typed(value: Any, expected: Any) -> None:
    try:
        os.environ["my_key"] = value
        os.environ["my_key_2"] = "456"
        c = OmegaConf.create(dict(my_key="${env:my_key}"))
        assert c.my_key == expected
    finally:
        del os.environ["my_key"]
        del os.environ["my_key_2"]


def test_env_node_interpolation() -> None:
    # Test that node interpolations are not supported in env variables.
    try:
        os.environ["my_key"] = "${other_key}"
        c = OmegaConf.create(dict(my_key="${env:my_key}", other_key=123))
        with pytest.raises(ConfigAttributeError):
            c.my_key
    finally:
        del os.environ["my_key"]


def test_register_resolver_twice_error(restore_resolvers: Any) -> None:
    def foo(_: Any) -> int:
        return 10

    OmegaConf.new_register_resolver("foo", foo)
    with pytest.raises(AssertionError):
        OmegaConf.new_register_resolver("foo", lambda _: 10)


def test_register_resolver_twice_error_legacy(restore_resolvers: Any) -> None:
    def foo() -> int:
        return 10

    OmegaConf.legacy_register_resolver("foo", foo)
    with pytest.raises(AssertionError):
        OmegaConf.new_register_resolver("foo", lambda: 10)


def test_clear_resolvers(restore_resolvers: Any) -> None:
    assert OmegaConf.get_resolver("foo") is None
    OmegaConf.new_register_resolver("foo", lambda x: x + 10)
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
    OmegaConf.new_register_resolver("plus_10", lambda x: x + 10)
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
    OmegaConf.new_register_resolver("random", lambda _: random.randint(0, 10000000))
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
    OmegaConf.new_register_resolver("random", lambda _: random.randint(0, 10000000))
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
    OmegaConf.new_register_resolver("random", lambda _: random.uniform(0, 1))
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
    OmegaConf.new_register_resolver(
        "random", lambda _: random.uniform(0, 1), use_cache=False
    )
    c = OmegaConf.create(dict(k="${random:__}"))
    assert c.k != c.k


def test_resolver_dot_start(restore_resolvers: Any) -> None:
    """
    Regression test for #373
    """
    OmegaConf.new_register_resolver("identity", lambda x: x)
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
    OmegaConf.new_register_resolver("my_resolver", resolver)
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
    with pytest.warns(UserWarning):
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
    # `new_register_resolver()` in order to use nested interpolations).
    with pytest.raises(ValueError):
        c.inter


def test_copy_cache(restore_resolvers: Any) -> None:
    OmegaConf.new_register_resolver("random", lambda _: random.randint(0, 10000000))
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
    OmegaConf.new_register_resolver("random", lambda _: random.randint(0, 10000000))
    c = OmegaConf.create(dict(k="${random:__}"))
    old = c.k
    OmegaConf.clear_cache(c)
    assert old != c.k


def test_supported_chars() -> None:
    supported_chars = "abc123_/:-\\+.$%*@"
    c = OmegaConf.create(dict(dir1="${copy:" + supported_chars + "}"))

    OmegaConf.new_register_resolver("copy", lambda x: x)
    assert c.dir1 == supported_chars


def test_valid_key_names() -> None:
    invalid_chars = "\\${}()[].: '\""
    valid_chars = "".join(chr(i) for i in range(33, 128) if chr(i) not in invalid_chars)
    cfg_dict = {valid_chars: 123, "inter": f"${{{valid_chars}}}"}
    cfg = OmegaConf.create(cfg_dict)
    # Test that we can access the node made of all valid characters, both
    # directly and through interpolations.
    assert cfg[valid_chars] == 123
    assert cfg.inter == 123
    # Test that all invalid characters trigger errors in interpolations.
    for c in invalid_chars:
        cfg_dict["invalid"] = f"${{ab{c}de}}"
        cfg = OmegaConf.create(cfg_dict)
        error: type
        if c in [".", "}"]:
            # With '.', we try to access `${ab.de}`.
            # With "}", we try to access `${ab}`.
            error = ConfigAttributeError
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


# Config data used to run many interpolation tests. Each 3-element tuple
# contains the config key, its value , and its expected value after
# interpolations are resolved (possibly an exception class).
# If the expected value is the ellipsis ... then it is expected to be the
# same as the definition (or `OmegaConf.create()` called on it for lists
# and dictionaries).
# Order matters! (each entry should only depend on those above)
TEST_CONFIG_DATA: List[Tuple[str, Any, Any]] = [
    # Not interpolations (just building blocks for below).
    ("prim_str", "hi", ...),
    ("prim_str_space", "hello world", ...),
    ("test_str", "test", ...),
    ("test_str_partial", "st", ...),
    ("prim_list", [-1, "a", 1.1], ...),
    ("prim_dict", {"a": 0, "b": 1}, ...),
    ("FalsE", {"TruE": True}, ...),  # used to test keys with bool names
    ("None", {"True": 1}, ...),  # used to test keys with null-like names
    ("0", 42, ...),  # used to test keys with int names
    ("1", {"2": 1337}, ...),  # used to test dot-path with int keys
    ("x@y", 123, ...),
    # Special keywords.
    ("null", "${test:null}", None),
    ("true", "${test:TrUe}", True),
    ("false", "${test:falsE}", False),
    ("true_false", "${test:true_false}", "true_false"),
    # Integers.
    ("int", "${test:123}", 123),
    ("int_pos", "${test:+123}", 123),
    ("int_neg", "${test:-123}", -123),
    ("int_underscore", "${test:1_000}", 1000),
    ("int_bad_underscore_1", "${test:1_000_}", "1_000_"),
    ("int_bad_underscore_2", "${test:1__000}", "1__000"),
    ("int_bad_underscore_3", "${test:_1000}", "_1000"),
    ("int_bad_zero_start", "${test:007}", "007"),
    # Floats.
    ("float", "${test:1.1}", 1.1),
    ("float_no_int", "${test:.1}", 0.1),
    ("float_no_decimal", "${test:1.}", 1.0),
    ("float_plus", "${test:+1.01}", 1.01),
    ("float_minus", "${test:-.2}", -0.2),
    ("float_underscore", "${test:1.1_1}", 1.11),
    ("float_bad_1", "${test:1.+2}", "1.+2"),
    ("float_bad_2", r"${test:1\.2}", r"1\.2"),
    ("float_bad_3", "${test:1.2_}", "1.2_"),
    ("float_exp_1", "${test:-1e2}", -100.0),
    ("float_exp_2", "${test:+1E-2}", 0.01),
    ("float_exp_3", "${test:1_0e1_0}", 10e10),
    ("float_exp_4", "${test:1.07e+2}", 107.0),
    ("float_exp_5", "${test:1e+03}", 1000.0),
    ("float_exp_bad_1", "${test:e-2}", "e-2"),
    ("float_exp_bad_2", "${test:01e2}", "01e2"),
    ("float_inf", "${test:inf}", math.inf),
    ("float_plus_inf", "${test:+inf}", math.inf),
    ("float_minus_inf", "${test:-inf}", -math.inf),
    ("float_nan", "${test:nan}", math.nan),
    ("float_plus_nan", "${test:+nan}", math.nan),
    ("float_minus_nan", "${test:-nan}", math.nan),
    # Node interpolations.
    ("dict_access", "${prim_dict.a}", 0),
    ("list_access_1", "${prim_list.0}", -1),
    ("list_access_2", "${test:${prim_list.1},${prim_list.2}}", ["a", 1.1]),
    ("list_access_underscore", "${prim_list.1_000}", ConfigAttributeError),  # "working"
    ("list_access_bad_negative", "${prim_list.-1}", ConfigAttributeError),
    ("dict_access_list_like_1", "${0}", 42),
    ("dict_access_list_like_2", "${1.2}", 1337),
    ("bool_like_keys", "${FalsE.TruE}", True),
    ("null_like_key_ok", "${None.True}", 1),
    ("null_like_key_bad_case", "${null.True}", ConfigAttributeError),
    ("null_like_key_quoted_1", "${'None'.'True'}", GrammarParseError),
    ("null_like_key_quoted_2", "${'None.True'}", GrammarParseError),
    ("dotpath_bad_type", "${prim_dict.${float}}", GrammarParseError),
    ("at_in_key", "${x@y}", 123),
    # Resolver interpolations.
    ("no_args", "${test:}", []),
    ("space_in_args", "${test:a, b c}", ["a", "b c"]),
    ("list_as_input", "${test:[a, b], 0, [1.1]}", [["a", "b"], 0, [1.1]]),
    ("dict_as_input", "${test:{a: 1.1, b: b}}", {"a": 1.1, "b": "b"}),
    ("dict_as_input_quotes", "${test:{'a': 1.1, b: b}}", {"a": 1.1, "b": "b"}),
    ("dict_typo_colons", "${test:{a: 1.1, b:: b}}", {"a": 1.1, "b": ": b"}),
    ("dict_list_as_key", "${test:{[0]: 1}}", GrammarParseError),
    ("missing_resolver", "${MiSsInG_ReSoLvEr:0}", UnsupportedInterpolationType),
    ("non_str_resolver", "${${bool}:}", GrammarParseError),
    ("at_in_resolver", "${y@z:}", GrammarParseError),
    # Env resolver (limited: more tests in `test_env_values_are_typed()`).
    ("env_int", "${env:OMEGACONF_TEST_ENV_INT}", 123),
    ("env_missing_str", "${env:OMEGACONF_TEST_MISSING,miss}", "miss"),
    ("env_missing_int", "${env:OMEGACONF_TEST_MISSING,123}", 123),
    ("env_missing_quoted_int", "${env:OMEGACONF_TEST_MISSING,'123'}", "123"),
    # Resolvers with special names (note: such resolvers are registered).
    ("bool_resolver_1", "${True:1,2,3}", ["True", 1, 2, 3]),
    ("bool_resolver_2", "${FALSE:1,2,3}", ["FALSE", 1, 2, 3]),
    ("null_resolver", "${null:1,2,3}", ["null", 1, 2, 3]),
    ("resolver_special", "${infnannulltruefalse:}", "ok"),
    # Invalid resolver names.
    ("int_resolver_quoted", "${'0':1,2,3}", GrammarParseError),
    ("int_resolver_noquote", "${0:1,2,3}", GrammarParseError),
    ("float_resolver_quoted", "${'1.1':1,2,3}", GrammarParseError),
    ("float_resolver_noquote", "${1.1:1,2,3}", GrammarParseError),
    ("float_resolver_exp", "${1e1:1,2,3}", GrammarParseError),
    # String interpolations (top-level).
    ("str_top_basic", "bonjour ${prim_str}", "bonjour hi"),
    ("str_top_quotes_single_1", "'bonjour ${prim_str}'", "'bonjour hi'"),
    (
        "str_top_quotes_single_2",
        "'Bonjour ${prim_str}', I said.",
        "'Bonjour hi', I said.",
    ),
    ("str_top_quotes_double_1", '"bonjour ${prim_str}"', '"bonjour hi"'),
    (
        "str_top_quotes_double_2",
        '"Bonjour ${prim_str}", I said.',
        '"Bonjour hi", I said.',
    ),
    ("str_top_missing_end_quote_single", "'${prim_str}", "'hi"),
    ("str_top_missing_end_quote_double", '"${prim_str}', '"hi'),
    ("str_top_missing_start_quote_double", '${prim_str}"', 'hi"'),
    ("str_top_missing_start_quote_single", "${prim_str}'", "hi'"),
    ("str_top_middle_quote_single", "I'd like ${prim_str}", "I'd like hi"),
    ("str_top_middle_quote_double", 'I"d like ${prim_str}', 'I"d like hi'),
    ("str_top_middle_quotes_single", "I like '${prim_str}'", "I like 'hi'"),
    ("str_top_middle_quotes_double", 'I like "${prim_str}"', 'I like "hi"'),
    ("str_top_any_char", "${prim_str} !@\\#$%^&*})][({,/?;", "hi !@\\#$%^&*})][({,/?;"),
    ("str_top_esc_inter", r"Esc: \${prim_str}", "Esc: ${prim_str}"),
    ("str_top_esc_inter_wrong_1", r"Wrong: $\{prim_str\}", r"Wrong: $\{prim_str\}"),
    ("str_top_esc_inter_wrong_2", r"Wrong: \${prim_str\}", r"Wrong: ${prim_str\}"),
    ("str_top_esc_backslash", r"Esc: \\${prim_str}", r"Esc: \hi"),
    ("str_top_quoted_braces_wrong", r"Wrong: \{${prim_str}\}", r"Wrong: \{hi\}"),
    ("str_top_leading_dollars", r"$$${prim_str}", "$$hi"),
    ("str_top_trailing_dollars", r"${prim_str}$$$$", "hi$$$$"),
    ("str_top_leading_escapes", r"\\\\\${prim_str}", r"\\${prim_str}"),
    ("str_top_middle_escapes", r"abc\\\\\${prim_str}", r"abc\\${prim_str}"),
    ("str_top_trailing_escapes", "${prim_str}" + "\\" * 5, "hi" + "\\" * 3),
    ("str_top_concat_interpolations", "${true}${float}", "True1.1"),
    # Quoted strings (within interpolations).
    ("str_quoted_single", "${test:'!@#$%^&*()[]:.,\"'}", '!@#$%^&*()[]:.,"'),
    ("str_quoted_double", '${test:"!@#$%^&*()[]:.,\'"}', "!@#$%^&*()[]:.,'"),
    ("str_quoted_outer_ws_single", "${test: '  a \t'}", "  a \t"),
    ("str_quoted_outer_ws_double", '${test: "  a \t"}', "  a \t"),
    ("str_quoted_int", "${test:'123'}", "123"),
    ("str_quoted_null", "${test:'null'}", "null"),
    ("str_quoted_bool", "${test:'truE', \"FalSe\"}", ["truE", "FalSe"]),
    ("str_quoted_list", "${test:'[a,b, c]'}", "[a,b, c]"),
    ("str_quoted_dict", '${test:"{a:b, c: d}"}', "{a:b, c: d}"),
    ("str_quoted_inter", "${test:'${null}'}", "None"),
    (
        "str_quoted_inter_nested",
        "${test:'${test:\"L=${prim_list}\"}'}",
        "L=[-1, 'a', 1.1]",
    ),
    ("str_quoted_nested", r"${test:'AB${test:\'CD${test:\\'EF\\'}GH\'}'}", "ABCDEFGH"),
    ("str_quoted_esc_single_1", r"${test:'ab\'cd\'\'${prim_str}'}", "ab'cd''hi"),
    ("str_quoted_esc_single_2", "${test:'\"\\\\\\\\\\${foo}\\ '}", r'"\${foo}\ '),
    ("str_quoted_esc_double_1", r'${test:"ab\"cd\"\"${prim_str}"}', 'ab"cd""hi'),
    ("str_quoted_esc_double_2", '${test:"\'\\\\\\\\\\${foo}\\ "}', r"'\${foo}\ "),
    ("str_quoted_backslash_noesc_single", r"${test:'a\b'}", r"a\b"),
    ("str_quoted_backslash_noesc_double", r'${test:"a\b"}', r"a\b"),
    ("str_quoted_concat_bad_1", '${test:"Hi "${prim_str}}', GrammarParseError),
    ("str_quoted_concat_bad_2", "${test:'Hi''there'}", GrammarParseError),
    ("str_quoted_too_many_1", "${test:''a'}", GrammarParseError),
    ("str_quoted_too_many_2", "${test:'a''}", GrammarParseError),
    ("str_quoted_too_many_3", "${test:''a''}", GrammarParseError),
    # Unquoted strings (within interpolations).
    ("str_legal", "${test:a/-\\+.$*@, \\\\}", ["a/-\\+.$*@", "\\"]),
    ("str_illegal_1", "${test:a,=b}", GrammarParseError),
    ("str_illegal_2", f"${{test:{chr(200)}}}", GrammarParseError),
    ("str_illegal_3", f"${{test:{chr(129299)}}}", GrammarParseError),
    ("str_dot", "${test:.}", "."),
    ("str_dollar", "${test:$}", "$"),
    ("str_colon", "${test::}", ":"),
    ("str_dollar_and_inter", "${test:$$${prim_str}}", "$$hi"),
    ("str_ws_1", "${test:hello world}", "hello world"),
    ("str_ws_2", "${test:a b\tc  \t\t  d}", "a b\tc  \t\t  d"),
    ("str_inter", "${test:hi_${prim_str_space}}", "hi_hello world"),
    ("str_esc_ws_1", r"${test:\ hello\ world\ }", " hello world "),
    ("str_esc_ws_2", "${test:\\ \\\t,\\\t}", [" \t", "\t"]),
    ("str_esc_comma", r"${test:hello\, world}", "hello, world"),
    ("str_esc_colon", r"${test:a\:b}", "a:b"),
    ("str_esc_equal", r"${test:a\=b}", "a=b"),
    ("str_esc_parentheses", r"${test:\(foo\)}", "(foo)"),
    ("str_esc_brackets", r"${test:\[foo\]}", "[foo]"),
    ("str_esc_braces", r"${test:\{foo\}}", "{foo}"),
    ("str_esc_backslash", r"${test:\\}", "\\"),
    ("str_backslash_noesc", r"${test:ab\cd}", r"ab\cd"),
    ("str_esc_illegal_1", r"${test:\#}", GrammarParseError),
    ("str_esc_illegal_2", r"${test:\${foo\}}", GrammarParseError),
    ("str_esc_illegal_3", "${test:\\'\\\"}", GrammarParseError),
    # Whitespaces.
    ("ws_toplevel_1", "  \tab  ${prim_str} cd  \t", "  \tab  hi cd  \t"),
    ("ws_toplevel_2", "\t${test:foo}\t${float}\t${null}\t", "\tfoo\t1.1\tNone\t"),
    ("ws_inter_node_outer", "${ \tprim_dict.a  \t}", 0),
    ("ws_inter_node_around_dot", "${prim_dict .\ta}", 0),
    ("ws_inter_node_inside_id", "${prim _ dict.a}", GrammarParseError),
    ("ws_inter_res_outer", "${\t test:foo\t  }", "foo"),
    ("ws_inter_res_around_colon", "${test\t  : \tfoo}", "foo"),
    ("ws_inter_res_inside_id", "${te st:foo}", GrammarParseError),
    ("ws_inter_res_inside_args", "${test:f o o}", "f o o"),
    ("ws_list", "${test:[\t a,   b,  ''\t  ]}", ["a", "b", ""]),
    ("ws_dict", "${test:{\t a   : 1\t  , b:  \t''}}", {"a": 1, "b": ""}),
    ("ws_quoted_single", "${test:  \t'foo'\t }", "foo"),
    ("ws_quoted_double", '${test:  \t"foo"\t }', "foo"),
    # Lists and dictionaries.
    ("list", "${test:[0, 1]}", [0, 1]),
    (
        "dict",
        "${test:{x: 1, a: 'b', y: 1e2, null2: 0.1, true3: false, inf4: true}}",
        {"x": 1, "a": "b", "y": 100.0, "null2": 0.1, "true3": False, "inf4": True},
    ),
    (
        "dict_interpolation_key",
        "${test:{${prim_str}: 0, ${null}: 1, ${int}: 2}}",
        GrammarParseError,
    ),
    (
        "dict_quoted_key",
        "${test:{0: 1, 'a': 'b', 1.1: 1e2, null: 0.1, true: false, -inf: true}}",
        {0: 1, "a": "b", 1.1: 100.0, None: 0.1, True: False, -math.inf: True},
    ),
    (
        "dict_unquoted_key",
        "${test:{a0-null-1-3.14-NaN- \t-true-False-/\\+.$%*@\\(\\)\\[\\]\\{\\}\\:\\=\\ \\\t\\,:0}}",
        {"a0-null-1-3.14-NaN- \t-true-False-/\\+.$%*@()[]{}:= \t,": 0},
    ),
    ("dict_int_key", "${test:{0: 0}}", {0: 0}),
    ("dict_float_key", "${test:{1.1: 0}}", {1.1: 0}),
    ("dict_nan_key_1", "${first:{nan: 0}}", math.nan),
    ("dict_nan_key_2", "${first:{${test:nan}: 0}}", GrammarParseError),
    ("dict_nan_key_3", "${test:{'nan': 0}}", {"nan": 0}),
    ("dict_null_key", "${test:{null: 0}}", {None: 0}),
    (
        "dict_bool_key",
        "${test:{true: true, false: 'false'}}",
        {True: True, False: "false"},
    ),
    ("empty_dict_list", "${test:[],{}}", [[], {}]),
    (
        "structured_mixed",
        "${test:10,str,3.14,true,false,inf,[1,2,3], 'quoted', \"quoted\", 'a,b,c'}",
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
    (
        "structured_deep",
        "${test:{null0: [0, 3.14, false], true1: {a: [0, 1, 2], b: {}}}}",
        {"null0": [0, 3.14, False], "true1": {"a": [0, 1, 2], "b": {}}},
    ),
    # Chained interpolations.
    ("null_chain", "${null}", None),
    ("true_chain", "${true}", True),
    ("int_chain", "${int}", 123),
    ("list_chain_bad_1", "${${prim_list}.0}", GrammarParseError),
    ("dict_chain_bad_1", "${${prim_dict}.a}", GrammarParseError),
    ("prim_list_copy", "${prim_list}", OmegaConf.create([-1, "a", 1.1])),
    ("prim_dict_copy", "${prim_dict}", OmegaConf.create({"a": 0, "b": 1})),
    ("list_chain", "${prim_list_copy.0}", -1),
    ("dict_chain", "${prim_dict_copy.a}", 0),
    # Nested interpolations.
    ("ref_prim_str", "prim_str", ...),
    ("nested_simple", "${${ref_prim_str}}", "hi"),
    ("plans", {"plan A": "awesome plan", "plan B": "crappy plan"}, ...),
    ("selected_plan", "plan A", ...),
    (
        "nested_dotted",
        r"I choose: ${plans.${selected_plan}}",
        "I choose: awesome plan",
    ),
    ("nested_deep", "${test:${${test:${ref_prim_str}}}}", "hi"),
    ("nested_resolver", "${${test_str}:a, b, c}", ["a", "b", "c"]),
    (
        "nested_resolver_combined_illegal",
        "${te${test_str_partial}:a, b, c}",
        GrammarParseError,
    ),
    ("nested_args", "${test:${prim_str}, ${null}, ${int}}", ["hi", None, 123]),
    # Relative interpolations.
    (
        "relative",
        {"foo": 0, "one_dot": "${.foo}", "two_dots": "${..prim_dict.b}"},
        OmegaConf.create({"foo": 0, "one_dot": 0, "two_dots": 1}),
    ),
    ("relative_nested", "${test:${.relative.foo}}", 0),
    # Unmatched braces.
    ("missing_brace_1", "${test:${prim_str}", GrammarParseError),
    ("missing_brace_2", "${${test:prim_str}", GrammarParseError),
    ("extra_brace", "${test:${prim_str}}}", "hi}"),
]


@pytest.mark.parametrize(
    "key,expected",
    [
        pytest.param(
            key, _maybe_create(definition) if expected is ... else expected, id=key
        )
        for key, definition, expected in TEST_CONFIG_DATA
    ],
)
def test_all_interpolations(
    restore_resolvers: Any, monkeypatch: Any, key: str, expected: Any
) -> None:
    dbg_test_access_only = False  # debug flag to not test against expected value
    monkeypatch.setenv("OMEGACONF_TEST_ENV_INT", "123")
    monkeypatch.delenv("OMEGACONF_TEST_MISSING", raising=False)
    OmegaConf.new_register_resolver(
        "test", lambda *args: args[0] if len(args) == 1 else list(args)
    )
    OmegaConf.new_register_resolver("first", lambda d: next(iter(d)))
    OmegaConf.new_register_resolver("null", lambda *args: ["null"] + list(args))
    OmegaConf.new_register_resolver("FALSE", lambda *args: ["FALSE"] + list(args))
    OmegaConf.new_register_resolver("True", lambda *args: ["True"] + list(args))
    OmegaConf.new_register_resolver("infnannulltruefalse", lambda: "ok")

    cfg_dict = {}
    for cfg_key, definition, exp in TEST_CONFIG_DATA:
        assert cfg_key not in cfg_dict, f"duplicated key: {cfg_key}"
        cfg_dict[cfg_key] = definition
        if cfg_key == key:
            break
    cfg = OmegaConf.create(cfg_dict)

    if isinstance(expected, type) and issubclass(expected, Exception):
        with pytest.raises(expected):
            getattr(cfg, key)
    else:
        if dbg_test_access_only:
            # Only test that we can access, not that it yields the correct value.
            # This is a debug flag to use when testing new grammars without
            # corresponding visitor code.
            getattr(cfg, key)
        elif expected is math.nan:
            # Special case since nan != nan.
            assert math.isnan(getattr(cfg, key))
        else:
            value = getattr(cfg, key)
            assert value == expected
            # We also check types in particular because instances of `Node` are very
            # good at mimicking their underlying type's behavior, and it is easy to
            # fail to notice that the result contains nodes when it should not.
            _check_is_same_type(value, expected)


def _check_is_same_type(value: Any, expected: Any) -> None:
    """
    Helper function to validate that types of `value` and `expected are the same.

    This function assumes that `value == expected` holds, and performs a "deep"
    comparison of types (= it goes into data structures like dictionaries, lists
    and tuples).

    Note that dictionaries being compared must have keys ordered the same way!
    """
    assert type(expected) is type(value)
    if isinstance(value, (str, int, float)):
        pass
    elif isinstance(value, (list, tuple, ListConfig)):
        for vx, ex in zip(value, expected):
            _check_is_same_type(vx, ex)
    elif isinstance(value, (dict, DictConfig)):
        for (vk, vv), (ek, ev) in zip(value.items(), expected.items()):
            assert vk == ek, "dictionaries are not ordered the same"
            _check_is_same_type(vk, ek)
            _check_is_same_type(vv, ev)
    elif value is None:
        assert expected is None
    else:
        raise NotImplementedError(type(value))


def test_custom_resolver_return_validated(restore_resolvers: Any) -> Any:
    def cast(t: Any, v: Any) -> Any:
        if t == "str":
            return str(v)
        if t == "int":
            return int(v)
        assert False

    OmegaConf.new_register_resolver("cast", cast)
    cfg = OmegaConf.structured(User(name="Bond", age=SI("${cast:int,'7'}")))
    assert cfg.age == 7

    # converted to int per the dataclass age field
    cfg = OmegaConf.structured(User(name="Bond", age=SI("${cast:str,'7'}")))
    assert cfg.age == 7

    cfg = OmegaConf.structured(User(name="Bond", age=SI("${cast:str,seven}")))
    with pytest.raises(ValidationError):
        cfg.age
