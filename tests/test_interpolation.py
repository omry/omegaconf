import copy
import random
import re
from typing import Any, Optional, Tuple

import pytest
from _pytest.python_api import RaisesContext

from omegaconf import (
    II,
    Container,
    DictConfig,
    IntegerNode,
    Node,
    OmegaConf,
    Resolver,
    ValidationError,
    grammar_parser,
)
from omegaconf._utils import _ensure_container
from omegaconf.errors import (
    GrammarParseError,
    InterpolationKeyError,
    InterpolationResolutionError,
    OmegaConfBaseException,
    UnsupportedInterpolationType,
)

from . import StructuredWithMissing

# file deepcode ignore CopyPasteError:
# The above comment is a statement to stop DeepCode from raising a warning on
# lines that do equality checks of the form
#       c.k == c.k

# Characters that are not allowed by the grammar in config key names.
INVALID_CHARS_IN_KEY_NAMES = "\\${}()[].: '\""


@pytest.mark.parametrize(
    "cfg,key,expected",
    [
        pytest.param({"a": "${b}", "b": 10}, "a", 10, id="simple"),
        pytest.param(
            {"a": "${x}"},
            "a",
            pytest.raises(InterpolationKeyError),
            id="not_found",
        ),
        pytest.param(
            {"a": "${x.y}"},
            "a",
            pytest.raises(InterpolationKeyError),
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
            {"a": "${..b}", "b": 10},
            "a",
            pytest.raises(InterpolationKeyError),
            id="relative",
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
    assert OmegaConf.is_missing(cfg.x, "missing")
    assert not OmegaConf.is_missing(cfg, "a")
    assert not OmegaConf.is_missing(cfg, "b")


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
    cfg = OmegaConf.create({"foo": 0, "bar": "${foo.baz}"})
    with pytest.raises(InterpolationKeyError):
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
                InterpolationResolutionError,
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
    c = OmegaConf.create({"my_key": "${env:my_key}"})
    assert c.my_key == expected


def test_env_node_interpolation(monkeypatch: Any) -> None:
    # Test that node interpolations are not supported in env variables.
    monkeypatch.setenv("MYKEY", "${other_key}")
    c = OmegaConf.create({"my_key": "${env:MYKEY}", "other_key": 123})
    with pytest.raises(
        InterpolationKeyError,
        match=re.escape(
            "When attempting to resolve env variable 'MYKEY', a node interpolation caused "
            "the following exception: Interpolation key 'other_key' not found."
        ),
    ):
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
        {
            "lst1": "${random:[0, 1]}",
            "lst2": "${random:[0, 1]}",
            "lst3": "${random:[]}",
            "dct1": "${random:{a: 1, b: 2}}",
            "dct2": "${random:{b: 2, a: 1}}",
            "mixed1": "${random:{x: [1.1], y: {a: true, b: false, c: null, d: []}}}",
            "mixed2": "${random:{x: [1.1], y: {b: false, c: null, a: true, d: []}}}",
        }
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
    c = OmegaConf.create({"k": "${random:__}"})
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
    c = OmegaConf.create({"k": "${random:__}"})
    old = c.k
    OmegaConf.clear_cache(c)
    assert old != c.k


def test_supported_chars() -> None:
    supported_chars = "abc123_/:-\\+.$%*@"
    c = OmegaConf.create({"dir1": "${copy:" + supported_chars + "}"})

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
    def create() -> DictConfig:
        return OmegaConf.create({"invalid": f"${{ab{c}de}}"})

    # Test that all invalid characters trigger errors in interpolations.
    if c in [".", "}"]:
        # With '.', we try to access `${ab.de}`.
        # With '}', we try to access `${ab}`.
        cfg = create()
        with pytest.raises(InterpolationKeyError):
            cfg.invalid
    elif c == ":":
        # With ':', we try to run a resolver `${ab:de}`
        cfg = create()
        with pytest.raises(UnsupportedInterpolationType):
            cfg.invalid
    else:
        # Other invalid characters should be detected at creation time.
        with pytest.raises(GrammarParseError):
            create()


def test_interpolation_in_list_key_error() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(["${10}"])

    with pytest.raises(InterpolationKeyError):
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


@pytest.mark.parametrize("ref", ["missing", "invalid"])
def test_invalid_intermediate_result_when_not_throwing(
    ref: str, restore_resolvers: Any
) -> None:
    """
    Test the handling of missing / resolution failures in nested interpolations.

    The main goal of this test is to make sure that the resolution of an interpolation
    is stopped immediately when a missing / resolution failure occurs, even if
    `throw_on_resolution_failure` is set to False.
    When this happens while dereferencing a node, the result should be `None`.
    """

    def fail_if_called(x: Any) -> None:
        assert False

    OmegaConf.register_new_resolver("fail_if_called", fail_if_called)
    cfg = OmegaConf.create(
        {
            "x": "${fail_if_called:${%s}}" % ref,
            "missing": "???",
        }
    )
    x_node = cfg._get_node("x")
    assert isinstance(x_node, Node)
    assert x_node._dereference_node(throw_on_resolution_failure=False) is None
