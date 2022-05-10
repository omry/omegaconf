import copy
import re
from pathlib import Path
from textwrap import dedent
from typing import Any, Tuple

from pytest import mark, param, raises

from omegaconf import (
    II,
    SI,
    AnyNode,
    Container,
    DictConfig,
    IntegerNode,
    ListConfig,
    Node,
    OmegaConf,
    StringNode,
    ValidationError,
)
from omegaconf._utils import _ensure_container
from omegaconf.errors import InterpolationKeyError
from omegaconf.errors import InterpolationResolutionError
from omegaconf.errors import InterpolationResolutionError as IRE
from omegaconf.errors import InterpolationValidationError, ReadonlyConfigError
from omegaconf.nodes import InterpolationResultNode
from tests import (
    Color,
    MissingDict,
    MissingList,
    StructuredWithMissing,
    SubscriptedList,
    User,
)
from tests.interpolation import dereference_node

# file deepcode ignore CopyPasteError:
# The above comment is a statement to stop DeepCode from raising a warning on
# lines that do equality checks of the form
#       c.k == c.k


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

    with raises(ValidationError):
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

    with raises(ValidationError):
        OmegaConf.merge(cfg, {"typed_bar": "nope"})


def test_non_container_interpolation() -> None:
    cfg = OmegaConf.create({"foo": 0, "bar": "${foo.baz}"})
    with raises(InterpolationResolutionError):
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


@mark.parametrize(
    "cfg",
    [
        param({"a": "${b}", "b": "string", "s": "foo_${b}"}, id="str"),
        param({"a": "${b}", "b": True, "s": "foo_${b}"}, id="bool"),
        param({"a": "${b}", "b": 10, "s": "foo_${b}"}, id="int"),
        param({"a": "${b}", "b": 3.14, "s": "foo_${b}"}, id="float"),
        param({"a": "${b}", "b": Color.RED, "s": "foo_${b}"}, id="enum"),
        param({"a": "${b}", "b": b"binary", "s": "foo_${b}"}, id="bytes"),
        param({"a": "${b}", "b": Path("hello.txt"), "s": "foo_${b}"}, id="path"),
    ],
)
def test_type_inherit_type(cfg: Any) -> None:
    cfg = _ensure_container(cfg)
    assert isinstance(cfg.a, type(cfg.b))
    assert type(cfg.s) == str  # check that string interpolations are always strings


def test_interpolation_in_list_key_error() -> None:
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(["${10}"])

    with raises(InterpolationKeyError):
        c[0]


def test_unsupported_interpolation_type() -> None:
    c = OmegaConf.create({"foo": "${wrong_type:ref}"})
    with raises(ValueError):
        c.foo


def test_incremental_dict_with_interpolation() -> None:
    conf = OmegaConf.create()
    conf.a = 1
    conf.b = OmegaConf.create()
    conf.b.c = "${a}"
    assert conf.b.c == conf.a  # type:ignore


@mark.parametrize(
    "cfg,node_key,key,expected",
    [
        param({"a": 10}, "", "", ({"a": 10}, "")),
        param({"a": 10}, "", ".", ({"a": 10}, "")),
        param({"a": 10}, "", "a", ({"a": 10}, "a")),
        param({"a": 10}, "", ".a", ({"a": 10}, "a")),
        param({"a": {"b": 10}}, "a", ".", ({"b": 10}, "")),
        param({"a": {"b": 10}}, "a", ".b", ({"b": 10}, "b")),
        param({"a": {"b": 10}}, "a", "..", ({"a": {"b": 10}}, "")),
        param({"a": {"b": 10}}, "a", "..a", ({"a": {"b": 10}}, "a")),
        param({"a": {"b": {"c": 10}}}, "a.b", ".", ({"c": 10}, "")),
        param({"a": {"b": {"c": 10}}}, "a.b", "..", ({"b": {"c": 10}}, "")),
        param({"a": {"b": {"c": 10}}}, "a.b", "...", ({"a": {"b": {"c": 10}}}, "")),
    ],
)
def test_resolve_key_and_root(
    cfg: Any, node_key: str, key: str, expected: Tuple[Node, str]
) -> None:
    cfg = _ensure_container(cfg)
    node: Container = OmegaConf.select(cfg, node_key)
    assert node._resolve_key_and_root(key) == expected


@mark.parametrize("copy_func", [copy.copy, copy.deepcopy])
@mark.parametrize(
    "data,key",
    [
        param({"a": 10, "b": "${a}"}, "b", id="dict"),
        param([10, "${0}"], 1, id="list"),
    ],
)
def test_interpolation_after_copy(copy_func: Any, data: Any, key: Any) -> None:
    dict_cfg = OmegaConf.create(data)
    assert copy_func(dict_cfg._get_node(key))._dereference_node() == 10


def test_resolve_interpolation_without_parent() -> None:
    with raises(
        IRE, match=re.escape("Cannot resolve interpolation for a node without a parent")
    ):
        DictConfig(content="${foo}")._dereference_node()


def test_resolve_interpolation_without_parent_no_throw() -> None:
    cfg = DictConfig(content="${foo}")
    assert cfg._maybe_dereference_node() is None


def test_optional_after_interpolation() -> None:
    cfg = OmegaConf.structured(StructuredWithMissing(opt_num=II("num")))
    # Ensure that we can set an optional field to `None` even when it currently
    # points to a non-optional field.
    cfg.opt_num = None


@mark.parametrize("ref", ["missing", "invalid"])
def test_invalid_intermediate_result_when_not_throwing(
    ref: str, restore_resolvers: Any
) -> None:
    """
    Test the handling of missing / resolution failures in nested interpolations.

    The main goal of this test is to make sure that the resolution of an interpolation
    is stopped immediately when a missing / resolution failure occurs, even if
    `_maybe_dereference_node(throw_on_resolution_failure=False)` is used
    instead of `_dereference_node`.
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
    assert x_node._maybe_dereference_node(throw_on_resolution_failure=False) is None


def test_none_value_in_quoted_string(restore_resolvers: Any) -> None:
    OmegaConf.register_new_resolver("test", lambda x: x)
    cfg = OmegaConf.create({"x": "${test:'${missing}'}", "missing": None})
    assert cfg.x == "None"


@mark.parametrize(
    ("cfg", "key", "expected_value", "expected_node_type"),
    [
        param(
            User(name="Bond", age=SI("${cast:int,'7'}")),
            "age",
            7,
            InterpolationResultNode,
            id="expected_type",
        ),
        param(
            # This example specifically test the case where intermediate resolver results
            # cannot be cast to the same type as the key.
            User(name="Bond", age=SI("${cast:int,${drop_last:${drop_last:7xx}}}")),
            "age",
            7,
            InterpolationResultNode,
            id="intermediate_type_mismatch_ok",
        ),
        param(
            # This example relies on the automatic casting of a string to int when
            # assigned to an IntegerNode.
            User(name="Bond", age=SI("${cast:str,'7'}")),
            "age",
            7,
            InterpolationResultNode,
            id="convert_str_to_int",
        ),
        param(
            MissingList(list=SI("${oc.create:[a, b, c]}")),
            "list",
            ListConfig(["a", "b", "c"]),
            ListConfig,
            id="list_str",
        ),
        param(
            MissingDict(dict=SI("${oc.create:{key1: val1, key2: val2}}")),
            "dict",
            DictConfig({"key1": "val1", "key2": "val2"}),
            DictConfig,
            id="dict_str",
        ),
    ],
)
def test_interpolation_type_validated_ok(
    cfg: Any,
    key: str,
    expected_value: Any,
    expected_node_type: Any,
    common_resolvers: Any,
) -> Any:
    def drop_last(s: str) -> str:
        return s[0:-1]  # drop last character from string `s`

    OmegaConf.register_new_resolver("drop_last", drop_last)

    cfg = OmegaConf.structured(cfg)

    val = cfg[key]
    assert val == expected_value
    assert type(val) is type(expected_value)

    node = cfg._get_node(key)
    assert isinstance(node, Node)
    assert isinstance(node._dereference_node(), expected_node_type)


@mark.parametrize(
    ("cfg", "key", "expected_error"),
    [
        param(
            User(name="Bond", age=SI("${cast:str,seven}")),
            "age",
            raises(
                InterpolationValidationError,
                match=re.escape(
                    dedent(
                        """\
                        Value 'seven' of type 'str' could not be converted to Integer
                            full_key: age
                        """
                    )
                ),
            ),
            id="type_mismatch_resolver",
        ),
        param(
            User(name="Bond", age=SI("${name}")),
            "age",
            raises(
                InterpolationValidationError,
                match=re.escape(
                    "'Bond' of type 'str' could not be converted to Integer"
                ),
            ),
            id="type_mismatch_node_interpolation",
        ),
        param(
            StructuredWithMissing(opt_num=None, num=II("opt_num")),
            "num",
            raises(
                InterpolationValidationError,
                match=re.escape(
                    "While dereferencing interpolation '${opt_num}': Incompatible value 'None' for field of type 'int'"
                ),
            ),
            id="non_optional_node_interpolation",
        ),
    ],
)
def test_interpolation_type_validated_error(
    cfg: Any,
    key: str,
    expected_error: Any,
    common_resolvers: Any,
) -> None:
    cfg = OmegaConf.structured(cfg)

    with expected_error:
        cfg[key]

    assert OmegaConf.select(cfg, key, throw_on_resolution_failure=False) is None


@mark.parametrize(
    ("cfg", "key", "expected_value", "expected_node_type"),
    [
        param(
            MissingList(list=SI("${oc.create:[0, 1, 2]}")),
            "list",
            [0, 1, 2],
            ListConfig,
            id="list_int_to_str",
        ),
        param(
            MissingDict(dict=SI("${oc.create:{a: 0, b: 1}}")),
            "dict",
            {"a": 0, "b": 1},
            DictConfig,
            id="dict_int_to_str",
        ),
        param(
            SubscriptedList(list=SI("${oc.create:[a, b]}")),
            "list",
            ["a", "b"],
            ListConfig,
            id="list_type_mismatch",
        ),
        param(
            MissingDict(dict=SI("${oc.create:{0: b, 1: d}}")),
            "dict",
            {0: "b", 1: "d"},
            DictConfig,
            id="dict_key_type_mismatch",
        ),
    ],
)
def test_interpolation_type_not_validated(
    cfg: Any,
    key: str,
    expected_value: Any,
    expected_node_type: Any,
) -> Any:
    cfg = OmegaConf.structured(cfg)

    val = cfg[key]
    assert val == expected_value

    node = cfg._get_node(key)
    assert isinstance(node, Node)
    assert isinstance(node._dereference_node(), expected_node_type)


def test_type_validation_error_no_throw() -> None:
    cfg = OmegaConf.structured(User(name="Bond", age=SI("${name}")))
    bad_node = cfg._get_node("age")
    assert bad_node._maybe_dereference_node() is None


@mark.parametrize(
    ("cfg", "key"),
    [
        param({"a": {"a": "${a}"}}, "a.a"),
        param({"a": {"a": "${..a}"}}, "a.a"),
    ],
)
def test_parent_interpolation(cfg: Any, key: str) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(IRE, match=re.escape("Interpolation to parent node detected")):
        OmegaConf.select(cfg, key)


@mark.parametrize(
    ("cfg", "key", "expected"),
    [
        param({"a": "${a}"}, "a", IRE, id="self_interpolation"),
        param({"a": "${b}", "b": "${a}"}, "a", IRE, id="ping-pong"),
        param({"a": {"a": "${b}"}, "b": "${a.a}"}, "a.a", IRE, id="ping-pong"),
        param({"a": {"a": "${.a}"}}, "a.a", IRE, id="self-relative"),
        param({"a": "${b}", "b": "${a.a}"}, "a.a", IRE, id="pass-through"),
        # quoted strings
        param({"a": "${oc.decode:'${a}'}"}, "a", IRE, id="quoted"),
        # custom resolver
        param({"a": "${foo:${a}}"}, "a", IRE, id="custom-resolver"),
        param({"a": "${foo:${foo:${a}}}"}, "a", IRE, id="custom-resolver"),
        # string interpolation
        param({"a": "x ${a}"}, "a", IRE, id="str-inter"),
        param({"a": "${b}_${c}", "b": "10", "c": 20}, "a", "10_20", id="str-inter"),
        param({"a": "A", "b": "${a}_${a}"}, "b", "A_A", id="str-inter"),
    ],
)
def test_circular_interpolation(cfg: Any, key: str, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    if isinstance(expected, type):
        with raises(expected, match=re.escape("Recursive interpolation detected")):
            OmegaConf.select(cfg, key)
    else:
        assert OmegaConf.select(cfg, key) == expected


@mark.parametrize(
    "node_type",
    [
        param(lambda x: x, id="untyped"),
        param(AnyNode, id="any"),
        param(StringNode, id="str"),
    ],
)
@mark.parametrize(
    ("value", "expected"),
    [
        param(r"\${foo}", "${foo}", id="escaped_interpolation_1"),
        param(r"\${foo", "${foo", id="escaped_interpolation_2"),
        param(r"$${y1}", "${foo}", id="string_interpolation_1"),
        param(r"$${y2}", "${foo", id="string_interpolation_2"),
        # This passes to `oc.decode` the string with characters: '\${foo}' which
        # is then resolved into: ${foo}
        param(r"${oc.decode:'\'\\\${foo}\''}", "${foo}", id="resolver_1"),
        param(r"${oc.decode:'\'\\\${foo\''}", "${foo", id="resolver_2"),
    ],
)
def test_interpolation_like_result_is_not_an_interpolation(
    node_type: Any, value: str, expected: str
) -> None:
    cfg = OmegaConf.create({"x": node_type(value), "y1": "{foo}", "y2": "{foo"})
    assert cfg.x == expected

    # Check that the resulting node is not considered to be an interpolation.
    resolved_node = dereference_node(cfg, "x")
    assert not resolved_node._is_interpolation()

    # Check that the resulting node is read-only.
    with raises(ReadonlyConfigError):
        resolved_node._set_value("foo")
