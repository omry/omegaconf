import random
import re
from typing import Any, Dict, List, Optional

from pytest import mark, param, raises, warns

from omegaconf import DictConfig, ListConfig, OmegaConf, Resolver
from omegaconf._utils import _ensure_container
from omegaconf.errors import InterpolationResolutionError
from tests.interpolation import dereference_node


@mark.parametrize("env_func", ["env", "oc.env"])
class TestEnvInterpolation:
    @mark.parametrize(
        ("cfg", "env_name", "env_val", "key", "expected"),
        [
            param(
                {"path": "/test/${${env_func}:foo}"},
                "foo",
                "1234",
                "path",
                "/test/1234",
                id="simple",
            ),
            param(
                {"path": "/test/${${env_func}:not_found,ZZZ}"},
                None,
                None,
                "path",
                "/test/ZZZ",
                id="not_found_with_default",
            ),
            param(
                {"path": "/test/${${env_func}:not_found,a/b}"},
                None,
                None,
                "path",
                "/test/a/b",
                id="not_found_with_default",
            ),
        ],
    )
    def test_env_interpolation(
        self,
        # DEPRECATED: remove in 2.2 with the legacy env resolver
        recwarn: Any,
        monkeypatch: Any,
        env_func: str,
        cfg: Any,
        env_name: Optional[str],
        env_val: str,
        key: str,
        expected: Any,
    ) -> None:
        if env_name is not None:
            monkeypatch.setenv(env_name, env_val)

        cfg["env_func"] = env_func  # allows choosing which env resolver to use
        cfg = OmegaConf.create(cfg)

        assert OmegaConf.select(cfg, key) == expected

    @mark.parametrize(
        ("cfg", "key", "expected"),
        [
            param(
                {"path": "/test/${${env_func}:not_found}"},
                "path",
                raises(
                    InterpolationResolutionError,
                    match=re.escape("Environment variable 'not_found' not found"),
                ),
                id="not_found",
            ),
        ],
    )
    def test_env_interpolation_error(
        self,
        # DEPRECATED: remove in 2.2 with the legacy env resolver
        recwarn: Any,
        env_func: str,
        cfg: Any,
        key: str,
        expected: Any,
    ) -> None:
        cfg["env_func"] = env_func  # allows choosing which env resolver to use
        cfg = _ensure_container(cfg)

        with expected:
            OmegaConf.select(cfg, key)


def test_legacy_env_is_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("FOOBAR", "1234")
    c = OmegaConf.create({"foobar": "${env:FOOBAR}"})
    with warns(UserWarning):
        before = c.foobar
        monkeypatch.setenv("FOOBAR", "3456")
        assert c.foobar == before


def test_env_is_not_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("FOOBAR", "1234")
    c = OmegaConf.create({"foobar": "${oc.env:FOOBAR}"})
    before = c.foobar
    monkeypatch.setenv("FOOBAR", "3456")
    assert c.foobar != before


@mark.parametrize(
    "value,expected",
    [
        # We only test a few typical cases: more extensive grammar tests are
        # found in `test_grammar.py`.
        # bool
        ("false", False),
        ("true", True),
        # int
        ("10", 10),
        ("-10", -10),
        # float
        ("10.0", 10.0),
        ("-10.0", -10.0),
        # null
        ("null", None),
        ("NulL", None),
        # strings
        ("hello", "hello"),
        ("hello world", "hello world"),
        ("  123  ", "  123  "),
        ('"123"', "123"),
        # lists and dicts
        ("[1, 2, 3]", [1, 2, 3]),
        ("{a: 0, b: 1}", {"a": 0, "b": 1}),
        ("[\t1, 2, 3\t]", [1, 2, 3]),
        ("{   a: b\t  }", {"a": "b"}),
        # interpolations
        ("${parent.sibling}", 1),
        ("${.sibling}", 1),
        ("${..parent.sibling}", 1),
        ("${uncle}", 2),
        ("${..uncle}", 2),
        ("${oc.env:MYKEY}", 456),
    ],
)
def test_decode(monkeypatch: Any, value: Optional[str], expected: Any) -> None:
    monkeypatch.setenv("MYKEY", "456")
    c = OmegaConf.create(
        {
            # The node of interest is "node" (others are used to test interpolations).
            "parent": {
                "node": f"${{oc.decode:'{value}'}}",
                "sibling": 1,
            },
            "uncle": 2,
        }
    )
    assert c.parent.node == expected


def test_decode_none() -> None:
    c = OmegaConf.create({"x": "${oc.decode:null}"})
    assert c.x is None


@mark.parametrize(
    ("value", "exc"),
    [
        param(
            123,
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.decode` can only take strings or None as input, but `123` is of type int"
                ),
            ),
            id="bad_type",
        ),
        param(
            "'[1, '",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "GrammarParseError raised while resolving interpolation: "
                    "missing BRACKET_CLOSE at '<EOF>'"
                ),
            ),
            id="parse_error",
        ),
        param(
            # Must be escaped to prevent resolution before feeding it to `oc.decode`.
            "'\\${foo}'",
            raises(
                InterpolationResolutionError,
                match=re.escape("Interpolation key 'foo' not found"),
            ),
            id="interpolation_not_found",
        ),
    ],
)
def test_decode_error(monkeypatch: Any, value: Any, exc: Any) -> None:
    c = OmegaConf.create({"x": f"${{oc.decode:{value}}}"})
    with exc:
        c.x


@mark.parametrize(
    "value",
    ["false", "true", "10", "1.5", "null", "None", "${foo}"],
)
def test_env_preserves_string(monkeypatch: Any, value: str) -> None:
    monkeypatch.setenv("MYKEY", value)
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY}"})
    assert c.my_key == value


@mark.parametrize(
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
        ("  1 2 3  ", "  1 2 3  "),
        ("\t[1, 2, 3]\t", "\t[1, 2, 3]\t"),
        ("   {a: b}\t  ", "   {a: b}\t  "),
    ],
)
def test_legacy_env_values_are_typed(
    monkeypatch: Any, value: Any, expected: Any
) -> None:
    monkeypatch.setenv("MYKEY", value)
    c = OmegaConf.create({"my_key": "${env:MYKEY}"})
    with warns(UserWarning, match=re.escape("The `env` resolver is deprecated")):
        assert c.my_key == expected


def test_env_default_none(monkeypatch: Any) -> None:
    monkeypatch.delenv("MYKEY", raising=False)
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, null}"})
    assert c.my_key is None


@mark.parametrize("has_var", [True, False])
def test_env_non_str_default(monkeypatch: Any, has_var: bool) -> None:
    if has_var:
        monkeypatch.setenv("MYKEY", "456")
    else:
        monkeypatch.delenv("MYKEY", raising=False)

    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, 123}"})
    with raises(
        InterpolationResolutionError,
        match=re.escape(
            "TypeError raised while resolving interpolation: The default value "
            "of the `oc.env` resolver must be a string or None, but `123` is of type int"
        ),
    ):
        c.my_key


def test_register_resolver_twice_error(restore_resolvers: Any) -> None:
    def foo(_: Any) -> int:
        return 10

    OmegaConf.register_new_resolver("foo", foo)
    with raises(AssertionError):
        OmegaConf.register_new_resolver("foo", lambda _: 10)


def test_register_resolver_twice_error_legacy(restore_resolvers: Any) -> None:
    def foo() -> int:
        return 10

    OmegaConf.legacy_register_resolver("foo", foo)
    with raises(AssertionError):
        OmegaConf.register_new_resolver("foo", lambda: 10)


def test_register_non_inspectable_resolver(mocker: Any, restore_resolvers: Any) -> None:
    # When a function `f()` is not inspectable (e.g., some built-in CPython functions),
    # `inspect.signature(f)` will raise a `ValueError`. We want to make sure this does
    # not prevent us from using `f()` as a resolver.
    def signature_not_inspectable(*args: Any, **kw: Any) -> None:
        raise ValueError

    mocker.patch("inspect.signature", signature_not_inspectable)
    OmegaConf.register_new_resolver("not_inspectable", lambda: 123)
    assert OmegaConf.create({"x": "${not_inspectable:}"}).x == 123


def test_clear_resolvers_and_has_resolver(restore_resolvers: Any) -> None:
    assert not OmegaConf.has_resolver("foo")
    OmegaConf.register_new_resolver("foo", lambda x: x + 10)
    assert OmegaConf.has_resolver("foo")
    OmegaConf.clear_resolvers()
    assert not OmegaConf.has_resolver("foo")


def test_clear_resolvers_and_has_resolver_legacy(restore_resolvers: Any) -> None:
    assert not OmegaConf.has_resolver("foo")
    OmegaConf.legacy_register_resolver("foo", lambda x: int(x) + 10)
    assert OmegaConf.has_resolver("foo")
    OmegaConf.clear_resolvers()
    assert not OmegaConf.has_resolver("foo")


def test_get_resolver_deprecation() -> None:
    with warns(
        UserWarning, match=re.escape("https://github.com/omry/omegaconf/issues/608")
    ):
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


def test_resolver_dot_start(common_resolvers: Any) -> None:
    """
    Regression test for #373
    """
    c = OmegaConf.create(
        {"foo_nodot": "${identity:bar}", "foo_dot": "${identity:.bar}"}
    )
    assert c.foo_nodot == "bar"
    assert c.foo_dot == ".bar"


def test_resolver_dot_start_legacy(common_resolvers: Any) -> None:
    c = OmegaConf.create(
        {"foo_nodot": "${identity:bar}", "foo_dot": "${identity:.bar}"}
    )
    assert c.foo_nodot == "bar"
    assert c.foo_dot == ".bar"


@mark.parametrize(
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


@mark.parametrize(
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
    # with warns(UserWarning):  # TODO re-enable this check with the warning
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
    with raises(ValueError):
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


@mark.parametrize(
    ("cfg", "expected"),
    [
        ({"a": 0, "b": 1}, {"a": 0, "b": 1}),
        ({"a": "${y}"}, {"a": -1}),
        ({"a": 0, "b": "${x.a}"}, {"a": 0, "b": 0}),
        ({"a": 0, "b": "${.a}"}, {"a": 0, "b": 0}),
        ({"a": "${..y}"}, {"a": -1}),
    ],
)
def test_resolver_output_dict_to_dictconfig(
    restore_resolvers: Any, cfg: Dict[str, Any], expected: Dict[str, Any]
) -> None:
    OmegaConf.register_new_resolver("dict", lambda: cfg)
    c = OmegaConf.create({"x": "${dict:}", "y": -1})
    assert isinstance(c.x, DictConfig)
    assert c.x == expected
    assert dereference_node(c, "x")._get_flag("readonly")


@mark.parametrize(
    ("cfg", "expected"),
    [
        ([0, 1], [0, 1]),
        (["${y}"], [-1]),
        ([0, "${x.0}"], [0, 0]),
        ([0, "${.0}"], [0, 0]),
        (["${..y}"], [-1]),
    ],
)
def test_resolver_output_list_to_listconfig(
    restore_resolvers: Any, cfg: List[Any], expected: List[Any]
) -> None:
    OmegaConf.register_new_resolver("list", lambda: cfg)
    c = OmegaConf.create({"x": "${list:}", "y": -1})
    assert isinstance(c.x, ListConfig)
    assert c.x == expected
    assert dereference_node(c, "x")._get_flag("readonly")


def test_register_cached_resolver_with_keyword_unsupported() -> None:
    with raises(ValueError):
        OmegaConf.register_new_resolver("root", lambda _root_: None, use_cache=True)
    with raises(ValueError):
        OmegaConf.register_new_resolver("parent", lambda _parent_: None, use_cache=True)


def test_resolver_with_parent(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver(
        "parent", lambda _parent_: _parent_, use_cache=False
    )

    cfg = OmegaConf.create(
        {
            "a": 10,
            "b": {
                "c": 20,
                "parent": "${parent:}",
            },
            "parent": "${parent:}",
        }
    )

    assert cfg.parent is cfg
    assert cfg.b.parent is cfg.b


def test_resolver_with_root(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("root", lambda _root_: _root_, use_cache=False)
    cfg = OmegaConf.create(
        {
            "a": 10,
            "b": {
                "c": 20,
                "root": "${root:}",
            },
            "root": "${root:}",
        }
    )

    assert cfg.root is cfg
    assert cfg.b.root is cfg


def test_resolver_with_root_and_parent(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver(
        "both", lambda _root_, _parent_: _root_.add + _parent_.add, use_cache=False
    )

    cfg = OmegaConf.create(
        {
            "add": 10,
            "b": {
                "add": 20,
                "both": "${both:}",
            },
            "both": "${both:}",
        }
    )
    assert cfg.both == 20
    assert cfg.b.both == 30


def test_resolver_with_parent_and_default_value(restore_resolvers: Any) -> None:
    def parent_and_default(default: int = 10, *, _parent_: Any) -> Any:
        return _parent_.add + default

    OmegaConf.register_new_resolver(
        "parent_and_default", parent_and_default, use_cache=False
    )

    cfg = OmegaConf.create(
        {
            "add": 10,
            "no_param": "${parent_and_default:}",
            "param": "${parent_and_default:20}",
        }
    )

    assert cfg.no_param == 20
    assert cfg.param == 30
