import random
import re
from typing import Any

from pytest import mark, param, raises, warns

from omegaconf import OmegaConf, Resolver
from omegaconf.nodes import InterpolationResultNode
from tests import User
from tests.interpolation import dereference_node


def test_register_resolver_twice_error(restore_resolvers: Any) -> None:
    def foo(_: Any) -> int:
        return 10

    OmegaConf.register_new_resolver("foo", foo)
    with raises(ValueError, match=re.escape("resolver 'foo' is already registered")):
        OmegaConf.register_new_resolver("foo", foo)


def test_register_resolver_twice_error_legacy(restore_resolvers: Any) -> None:
    def foo() -> int:
        return 10

    OmegaConf.legacy_register_resolver("foo", foo)
    with raises(AssertionError):
        OmegaConf.legacy_register_resolver("foo", lambda: 10)


def test_register_resolver_twice_error_legacy_and_regular(
    restore_resolvers: Any,
) -> None:
    def foo() -> int:
        return 10

    OmegaConf.legacy_register_resolver("foo", foo)
    with raises(ValueError):
        OmegaConf.register_new_resolver("foo", foo)


def test_register_resolver_error_non_callable(restore_resolvers: Any) -> None:
    with raises(TypeError, match=re.escape("resolver must be callable")):
        OmegaConf.register_new_resolver("foo", 0)  # type: ignore


def test_register_resolver_error_empty_name(restore_resolvers: Any) -> None:
    with raises(ValueError, match=re.escape("cannot use an empty resolver name")):
        OmegaConf.register_new_resolver("", lambda: None)


def test_register_non_inspectable_resolver(mocker: Any, restore_resolvers: Any) -> None:
    # When a function `f()` is not inspectable (e.g., some built-in CPython functions),
    # `inspect.signature(f)` will raise a `ValueError`. We want to make sure this does
    # not prevent us from using `f()` as a resolver.
    def signature_not_inspectable(*args: Any, **kw: Any) -> None:
        raise ValueError

    mocker.patch("inspect.signature", signature_not_inspectable)
    OmegaConf.register_new_resolver("not_inspectable", lambda: 123)
    assert OmegaConf.create({"x": "${not_inspectable:}"}).x == 123


@mark.parametrize(
    ("use_cache_1", "use_cache_2", "expected"),
    [
        (False, False, 2),
        (False, True, 2),
        (True, False, 2),
        (True, True, 1),  # value is obtained from cache (see also #637)
    ],
)
def test_register_resolver_with_replace(
    restore_resolvers: Any,
    use_cache_1: bool,
    use_cache_2: bool,
    expected: Any,
) -> None:
    OmegaConf.register_new_resolver("foo", lambda: 1, use_cache=use_cache_1)
    cfg = OmegaConf.create({"x": "${foo:}"})
    assert cfg.x == 1
    OmegaConf.register_new_resolver(
        "foo", lambda: 2, use_cache=use_cache_2, replace=True
    )
    assert cfg.x == expected


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
    # The cache is important to allow embedding of functions like time()
    # without having the value change during the program execution.
    OmegaConf.register_new_resolver(
        "random", lambda _: random.randint(0, 10000000), use_cache=True
    )
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
    OmegaConf.register_new_resolver(
        "random", lambda _: random.randint(0, 10000000), use_cache=True
    )
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
    Test that the resolver cache works as expected with lists and dicts.

    Note that since the cache is based on string literals, changing the order of
    items in a dictionary is considered as a different input.
    """
    OmegaConf.register_new_resolver(
        "random", lambda _: random.uniform(0, 1), use_cache=True
    )
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
    assert c.dct1 != c.dct2
    assert c.mixed1 == c.mixed1
    assert c.mixed2 == c.mixed2
    assert c.mixed1 != c.mixed2


def test_resolver_cache_4_interpolation(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("test", lambda x: x, use_cache=True)
    c = OmegaConf.create({"x": "${test:${y}}", "y": 0})

    assert c.x == 0
    c.y = 1
    assert c.x == 0  # cache is based on string literals


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
    with warns(UserWarning):
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
    OmegaConf.register_new_resolver(
        "random", lambda _: random.randint(0, 10000000), use_cache=True
    )
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


@mark.parametrize("readonly", [True, False])
def test_resolver_output_dict(restore_resolvers: Any, readonly: bool) -> None:
    some_dict = {"a": 0, "b": "${y}"}
    OmegaConf.register_new_resolver("dict", lambda: some_dict)
    c = OmegaConf.create({"x": "${dict:}", "y": -1})
    OmegaConf.set_readonly(c, readonly)
    assert isinstance(c.x, dict)
    assert c.x == some_dict
    x_node = dereference_node(c, "x")
    assert isinstance(x_node, InterpolationResultNode)
    assert x_node._get_flag("readonly")


@mark.parametrize("readonly", [True, False])
@mark.parametrize(
    ("data", "expected_type"),
    [
        param({"a": 0, "b": "${y}"}, dict, id="dict"),
        param(["a", 0, "${y}"], list, id="list"),
    ],
)
def test_resolver_output_plain_dict_list(
    restore_resolvers: Any, readonly: bool, data: Any, expected_type: type
) -> None:
    OmegaConf.register_new_resolver("get_data", lambda: data)
    c = OmegaConf.create({"x": "${get_data:}", "y": -1})
    OmegaConf.set_readonly(c, readonly)

    assert isinstance(c.x, expected_type)
    assert c.x == data

    x_node = dereference_node(c, "x")
    assert isinstance(x_node, InterpolationResultNode)
    assert x_node._get_flag("readonly")


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


@mark.parametrize(
    ("cfg2", "expected"),
    [
        param({"foo": {"b": 1}}, {"foo": {"a": 0, "b": 1}}, id="extend"),
        param({"foo": {"b": "${.a}"}}, {"foo": {"a": 0, "b": 0}}, id="extend_inter"),
        param({"foo": {"a": 1}}, {"foo": {"a": 1}}, id="override_int"),
        param({"foo": {"a": {"b": 1}}}, {"foo": {"a": {"b": 1}}}, id="override_dict"),
        param({"foo": 10}, {"foo": 10}, id="replace_interpolation"),
        param({"bar": 10}, {"foo": {"a": 0}, "bar": 10}, id="other_node"),
    ],
)
def test_merge_into_resolver_output(
    restore_resolvers: Any, cfg2: Any, expected: Any
) -> None:
    OmegaConf.register_new_resolver(
        "make", lambda _parent_: OmegaConf.create({"a": 0}, parent=_parent_)
    )

    cfg = OmegaConf.create({"foo": "${make:}"})
    assert OmegaConf.merge(cfg, cfg2) == expected


@mark.parametrize(
    "primitive_container",
    [
        param({"first": 1, "second": 2}, id="dict"),
        param(["first", "second"], id="list"),
        param(User(name="Bond", age=7), id="user"),
    ],
)
def test_resolve_resolver_returning_primitive_container(
    restore_resolvers: Any, primitive_container: Any
) -> None:
    OmegaConf.register_new_resolver("returns_container", lambda: primitive_container)
    cfg = OmegaConf.create({"foo": "${returns_container:}"})
    assert cfg.foo == primitive_container
    OmegaConf.resolve(cfg)
    assert cfg.foo == primitive_container
