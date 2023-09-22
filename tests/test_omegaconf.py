import pathlib
import platform
from contextlib import nullcontext
from pathlib import Path
from typing import Any, Union

from pytest import mark, param, raises

from omegaconf import (
    MISSING,
    BooleanNode,
    BytesNode,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    PathNode,
    StringNode,
    UnionNode,
)
from omegaconf._utils import _is_none
from omegaconf.errors import (
    ConfigKeyError,
    InterpolationKeyError,
    InterpolationToMissingValueError,
    UnsupportedInterpolationType,
)
from tests import Color, ConcretePlugin, IllegalType, StructuredWithMissing


@mark.parametrize(
    "cfg, key, expected_is_missing, expectation",
    [
        ({}, "foo", False, raises(ConfigKeyError)),
        ({"foo": True}, "foo", False, nullcontext()),
        ({"foo": "${no_such_key}"}, "foo", False, raises(InterpolationKeyError)),
        ({"foo": MISSING}, "foo", True, raises(MissingMandatoryValue)),
        param(
            {"foo": "${bar}", "bar": DictConfig(content=MISSING)},
            "foo",
            False,
            raises(InterpolationToMissingValueError),
            id="missing_interpolated_dict",
        ),
        param(
            {"foo": ListConfig(content="???")},
            "foo",
            True,
            raises(MissingMandatoryValue),
            id="missing_list",
        ),
        param(
            {"foo": DictConfig(content="???")},
            "foo",
            True,
            raises(MissingMandatoryValue),
            id="missing_dict",
        ),
        param(
            {"foo": ListConfig(content="${missing}"), "missing": "???"},
            "foo",
            False,
            raises(InterpolationToMissingValueError),
            id="missing_list_interpolation",
        ),
        param(
            {"foo": DictConfig(content="${missing}"), "missing": "???"},
            "foo",
            False,
            raises(InterpolationToMissingValueError),
            id="missing_dict_interpolation",
        ),
        (
            {"foo": "${bar}", "bar": MISSING},
            "foo",
            False,
            raises(InterpolationToMissingValueError),
        ),
        (
            {"foo": "foo_${bar}", "bar": MISSING},
            "foo",
            False,
            raises(InterpolationToMissingValueError),
        ),
        (
            {"foo": "${unknown_resolver:foo}"},
            "foo",
            False,
            raises(UnsupportedInterpolationType),
        ),
        ({"foo": StringNode(value="???")}, "foo", True, raises(MissingMandatoryValue)),
        (
            {"foo": StringNode(value="???"), "inter": "${foo}"},
            "inter",
            False,
            raises(InterpolationToMissingValueError),
        ),
        (StructuredWithMissing, "num", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_num", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "dict", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_dict", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "list", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_list", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "user", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_user", True, raises(MissingMandatoryValue)),
        (
            StructuredWithMissing,
            "inter_user",
            False,
            raises(InterpolationToMissingValueError),
        ),
        (
            StructuredWithMissing,
            "inter_opt_user",
            False,
            raises(InterpolationToMissingValueError),
        ),
        (
            StructuredWithMissing,
            "inter_num",
            False,
            raises(InterpolationToMissingValueError),
        ),
    ],
)
def test_is_missing(
    cfg: Any, key: str, expected_is_missing: bool, expectation: Any
) -> None:
    cfg = OmegaConf.create(cfg)
    with expectation:
        cfg[key]

    assert OmegaConf.is_missing(cfg, key) == expected_is_missing
    OmegaConf.set_struct(cfg, True)
    assert OmegaConf.is_missing(cfg, key) == expected_is_missing
    OmegaConf.set_readonly(cfg, True)
    assert OmegaConf.is_missing(cfg, key) == expected_is_missing


def test_is_missing_resets() -> None:
    cfg = OmegaConf.structured(StructuredWithMissing)
    assert OmegaConf.is_missing(cfg, "dict")
    cfg.dict = {}
    assert not OmegaConf.is_missing(cfg, "dict")

    assert OmegaConf.is_missing(cfg, "list")
    cfg.list = [1, 2, 3]
    assert not OmegaConf.is_missing(cfg, "list")
    cfg.list = "???"
    assert OmegaConf.is_missing(cfg, "list")


@mark.parametrize(
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
        (Path, False),
        (Path("hello.txt"), False),
        (StringNode("foo"), False),
        (ConcretePlugin, False),
        (ConcretePlugin(), False),
        (OmegaConf.create({}), True),
        (OmegaConf.create([]), True),
        (OmegaConf.structured(ConcretePlugin), True),
        (OmegaConf.structured(ConcretePlugin()), True),
    ],
)
def test_is_config(cfg: Any, expected: bool) -> None:
    assert OmegaConf.is_config(cfg) == expected


@mark.parametrize(
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
        (Path, False),
        (Path("hello.txt"), False),
        (StringNode("foo"), False),
        (ConcretePlugin, False),
        (ConcretePlugin(), False),
        (OmegaConf.create({}), False),
        (OmegaConf.create([]), True),
        (OmegaConf.structured(ConcretePlugin), False),
        (OmegaConf.structured(ConcretePlugin()), False),
    ],
)
def test_is_list(cfg: Any, expected: bool) -> None:
    assert OmegaConf.is_list(cfg) == expected


@mark.parametrize(
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
        (Path, False),
        (Path("hello.txt"), False),
        (StringNode("foo"), False),
        (ConcretePlugin, False),
        (ConcretePlugin(), False),
        (OmegaConf.create({}), True),
        (OmegaConf.create([]), False),
        (OmegaConf.structured(ConcretePlugin), True),
        (OmegaConf.structured(ConcretePlugin()), True),
    ],
)
def test_is_dict(cfg: Any, expected: bool) -> None:
    assert OmegaConf.is_dict(cfg) == expected


@mark.parametrize("is_none", [True, False])
@mark.parametrize(
    "fac",
    [
        (lambda none: StringNode(value="foo" if not none else None, is_optional=True)),
        (lambda none: IntegerNode(value=10 if not none else None, is_optional=True)),
        (lambda none: FloatNode(value=10.0 if not none else None, is_optional=True)),
        (lambda none: BooleanNode(value=True if not none else None, is_optional=True)),
        (lambda none: BytesNode(value=b"123" if not none else None, is_optional=True)),
        (
            lambda none: PathNode(
                value=Path("hello.txt") if not none else None, is_optional=True
            )
        ),
        (
            lambda none: EnumNode(
                enum_type=Color,
                value=Color.RED if not none else None,
                is_optional=True,
            )
        ),
        (
            lambda none: ListConfig(
                content=[1, 2, 3] if not none else None, is_optional=True
            )
        ),
        (
            lambda none: DictConfig(
                content={"foo": "bar"} if not none else None, is_optional=True
            )
        ),
        (
            lambda none: DictConfig(
                ref_type=ConcretePlugin,
                content=ConcretePlugin() if not none else None,
                is_optional=True,
            )
        ),
    ],
)
def test_is_none(fac: Any, is_none: bool) -> None:
    obj = fac(is_none)
    assert obj._is_none() == is_none

    cfg = OmegaConf.create({"node": obj})
    assert (cfg.node is None) == is_none


@mark.parametrize(
    ("cfg", "key", "is_none"),
    [
        ({"foo": "${none}", "none": None}, "foo", True),
        ({"foo": "${missing_node}"}, "foo", False),
        ({"foo": "${missing_resolver:}"}, "foo", False),
        ({"foo": "${oc.decode:'[1, '}"}, "foo", False),
    ],
)
def test_is_none_interpolation(cfg: Any, key: str, is_none: bool) -> None:
    cfg = OmegaConf.create(cfg)
    check = _is_none(
        cfg._get_node(key), resolve=True, throw_on_resolution_failure=False
    )
    assert check == is_none


@mark.parametrize(
    "fac",
    [
        (
            lambda inter: StringNode(
                value="foo" if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: IntegerNode(
                value=10 if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: FloatNode(
                value=10 if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: BooleanNode(
                value=True if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: BytesNode(
                value=b"123" if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: PathNode(
                value="hello.txt" if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: EnumNode(
                enum_type=Color,
                value=Color.RED if inter is None else inter,
                is_optional=True,
            )
        ),
        (
            lambda inter: ListConfig(
                content=[1, 2, 3] if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: DictConfig(
                content={"foo": "bar"} if inter is None else inter, is_optional=True
            )
        ),
        (
            lambda inter: DictConfig(
                ref_type=ConcretePlugin,
                content=ConcretePlugin() if inter is None else inter,
                is_optional=True,
            )
        ),
    ],
    ids=[
        "StringNode",
        "IntegerNode",
        "FloatNode",
        "BooleanNode",
        "BytesNode",
        "PathNode",
        "EnumNode",
        "ListConfig",
        "DictConfig",
        "ConcretePlugin",
    ],
)
def test_is_interpolation(fac: Any) -> Any:
    obj = fac(inter=None)
    assert not OmegaConf.is_interpolation(obj)
    cfg = OmegaConf.create({"node": obj})
    assert not OmegaConf.is_interpolation(cfg, "node")

    assert not OmegaConf.is_interpolation(cfg, "missing")

    for inter in ["${foo}", "http://${url}", "${resolver:value}"]:
        obj = fac(inter=inter)
        assert OmegaConf.is_interpolation(obj)
        cfg = OmegaConf.create({"node": obj})
        assert OmegaConf.is_interpolation(cfg, "node")


@mark.parametrize(
    "cfg, type_",
    [
        ({"foo": 10}, int),
        ({"foo": 10.0}, float),
        ({"foo": True}, bool),
        ({"foo": b"123"}, bytes),
        ({"foo": UnionNode(10.0, Union[float, bytes])}, float),
        ({"foo": UnionNode(None, Union[float, bytes])}, type(None)),
        ({"foo": FloatNode(10.0)}, float),
        ({"foo": FloatNode(None)}, type(None)),
        (
            {"foo": Path("hello.txt")},
            pathlib.WindowsPath
            if platform.system() == "Windows"
            else pathlib.PosixPath,
        ),
        ({"foo": "bar"}, str),
        ({"foo": None}, type(None)),
        ({"foo": ConcretePlugin()}, ConcretePlugin),
        ({"foo": ConcretePlugin}, ConcretePlugin),
        ({"foo": {}}, dict),
        ({"foo": OmegaConf.create()}, dict),
        ({"foo": []}, list),
        ({"foo": OmegaConf.create([])}, list),
    ],
)
def test_get_type(cfg: Any, type_: Any) -> None:
    cfg = OmegaConf.create(cfg)
    assert OmegaConf.get_type(cfg, "foo") == type_


@mark.parametrize(
    "obj, type_",
    [
        (10, int),
        (10.0, float),
        (True, bool),
        (b"123", bytes),
        (
            Path("hello.txt"),
            pathlib.WindowsPath
            if platform.system() == "Windows"
            else pathlib.PosixPath,
        ),
        ("foo", str),
        (DictConfig(content={}), dict),
        (ListConfig(content=[]), list),
        (IllegalType, IllegalType),
        (IllegalType(), IllegalType),
    ],
)
def test_get_type_on_raw(obj: Any, type_: Any) -> None:
    assert OmegaConf.get_type(obj) == type_


def test_is_issubclass() -> None:
    cfg = OmegaConf.structured(ConcretePlugin)
    t = OmegaConf.get_type(cfg)
    assert t is not None and issubclass(t, ConcretePlugin)


@mark.parametrize(
    ("cfg", "expected"),
    [
        # dict
        param(OmegaConf.create(), {}, id="dict"),
        param(OmegaConf.create({"a": 10, "b": "${a}"}), {"a": 10, "b": 10}, id="dict"),
        param(
            OmegaConf.create({"a": 10, "b": {"a": "${a}"}}),
            {"a": 10, "b": {"a": 10}},
            id="dict",
        ),
        param(
            OmegaConf.create({"a": "${b.a}", "b": {"a": 10}}),
            {"a": 10, "b": {"a": 10}},
            id="dict",
        ),
        param(OmegaConf.create({"a": "???"}), {"a": "???"}, id="dict:missing"),
        param(
            OmegaConf.create({"a": "???", "b": "${a}"}),
            {"a": "???", "b": "???"},
            id="dict:missing",
        ),
        param(
            OmegaConf.create({"a": 10, "b": "a_${a}"}),
            {"a": 10, "b": "a_10"},
            id="dict:str_inter",
        ),
        # This seems like a reasonable resolution for a string interpolation pointing to a missing node:
        param(
            OmegaConf.create({"a": "???", "b": "a_${a}"}),
            {"a": "???", "b": "???"},
            id="dict:str_inter_missing",
        ),
        param(
            DictConfig("${a}", parent=OmegaConf.create({"a": {"b": 10}})),
            {"b": 10},
            id="inter_dict",
        ),
        param(
            DictConfig("${a}", parent=OmegaConf.create({"a": "???"})),
            "???",
            id="inter_dict_to_missing",
        ),
        param(
            OmegaConf.create({"x": "${y}", "y": {"z": "${foo}"}, "foo": 0}),
            {"x": {"z": 0}, "y": {"z": 0}, "foo": 0},
            id="dict_nested_interpolation",
        ),
        param(DictConfig(None), None, id="none_dict"),
        # comparing to ??? because to_container returns it.
        param(DictConfig("???"), "???", id="missing_dict"),
        # lists
        param(OmegaConf.create([]), [], id="list"),
        param(OmegaConf.create([10, "${0}"]), [10, 10], id="list"),
        param(OmegaConf.create(["???"]), ["???"], id="list:missing"),
        param(OmegaConf.create(["${1}", "???"]), ["???", "???"], id="list:missing"),
        param(
            ListConfig("${a}", parent=OmegaConf.create({"a": [1, 2]})),
            [1, 2],
            id="inter_list",
        ),
        param(
            ListConfig("${a}", parent=OmegaConf.create({"a": "???"})),
            "???",
            id="inter_list_to_missing",
        ),
        param(ListConfig(None), None, id="none_list"),
        # comparing to ??? because to_container returns it.
        param(ListConfig("???"), "???", id="missing_list"),
        # Tests for cases where an AnyNode with interpolation is promoted to a DictConfig/ListConfig node
        param(
            OmegaConf.create({"a": "${z}", "z": {"y": 1}}),
            {"a": {"y": 1}, "z": {"y": 1}},
            id="any_in_dict_to_dict",
        ),
        param(
            OmegaConf.create({"a": "${z}", "z": [1, 2]}),
            {"a": [1, 2], "z": [1, 2]},
            id="any_in_dict_to_list",
        ),
        param(
            OmegaConf.create(["${1}", {"z": {"y": 1}}]),
            [{"z": {"y": 1}}, {"z": {"y": 1}}],
            id="any_in_list_to_dict",
        ),
        param(
            OmegaConf.create(["${1}", [1, 2]]),
            [[1, 2], [1, 2]],
            id="any_in_list_to_list",
        ),
    ],
)
def test_resolve(cfg: Any, expected: Any) -> None:
    OmegaConf.resolve(cfg)
    # convert output to plain dict to avoid smart OmegaConf eq logic
    resolved_plain = OmegaConf.to_container(cfg, resolve=False)
    assert resolved_plain == expected


def test_resolve_invalid_input() -> None:
    with raises(ValueError):
        OmegaConf.resolve("aaa")  # type: ignore


@mark.parametrize(
    "cfg, expected",
    [
        # dict:
        ({"a": 10, "b": {"c": "???", "d": "..."}}, {"b.c"}),
        (
            {
                "a": "???",
                "b": {
                    "foo": "bar",
                    "bar": "???",
                    "more": {"missing": "???", "available": "yes"},
                },
                Color.GREEN: {"tint": "???", "default": Color.BLUE},
            },
            {"a", "b.bar", "b.more.missing", "GREEN.tint"},
        ),
        (
            {"a": "a", "b": {"foo": "bar", "bar": "foo"}},
            set(),
        ),
        (
            {"foo": "bar", "bar": "???", "more": {"foo": "???", "bar": "foo"}},
            {"bar", "more.foo"},
        ),
        # list:
        (["???", "foo", "bar", "???", 77], {"[0]", "[3]"}),
        (["", "foo", "bar"], set()),
        (["foo", "bar", "???"], {"[2]"}),
        (["foo", "???", ["???", "bar"]], {"[1]", "[2][0]"}),
        # mixing:
        (
            [
                "???",
                "foo",
                {
                    "a": True,
                    "b": "???",
                    "c": ["???", None],
                    "d": {"e": "???", "f": "fff", "g": [True, "???"]},
                },
                "???",
                77,
            ],
            {"[0]", "[2].b", "[2].c[0]", "[2].d.e", "[2].d.g[1]", "[3]"},
        ),
        (
            {
                "list": [
                    0,
                    DictConfig({"foo": "???", "bar": None}),
                    "???",
                    ["???", 3, False],
                ],
                "x": "y",
                "y": "???",
            },
            {"list[1].foo", "list[2]", "list[3][0]", "y"},
        ),
        ({Color.RED: ["???", {"missing": "???"}]}, {"RED[0]", "RED[1].missing"}),
        # with DictConfig and ListConfig:
        (
            DictConfig(
                {
                    "foo": "???",
                    "list": ["???", 1],
                    "bar": {"missing": "???", "more": "yes"},
                }
            ),
            {"foo", "list[0]", "bar.missing"},
        ),
        (
            ListConfig(
                ["???", "yes", "???", [0, 1, "???"], {"missing": "???", "more": ""}],
            ),
            {"[0]", "[2]", "[3][2]", "[4].missing"},
        ),
    ],
)
def test_missing_keys(cfg: Any, expected: Any) -> None:
    assert OmegaConf.missing_keys(cfg) == expected


@mark.parametrize("cfg", [float, int])
def test_missing_keys_invalid_input(cfg: Any) -> None:
    with raises(ValueError):
        OmegaConf.missing_keys(cfg)


@mark.parametrize(
    ("register_resolver_params", "name", "expected"),
    [
        param(
            dict(
                name="iamnew",
                resolver=lambda x: str(x).lower(),
                use_cache=False,
                replace=False,
            ),
            "iamnew",
            dict(pre_clear=True, result=True),
            id="remove-new-custom-resolver",
        ),
        param(
            dict(),
            "oc.env",
            dict(pre_clear=True, result=True),
            id="remove-default-resolver",
        ),
        param(
            dict(),
            "idonotexist",
            dict(pre_clear=False, result=False),
            id="remove-nonexistent-resolver",
        ),
    ],
)
def test_clear_resolver(
    restore_resolvers: Any, register_resolver_params: Any, name: str, expected: Any
) -> None:
    if register_resolver_params:
        OmegaConf.register_new_resolver(**register_resolver_params)
    assert expected["pre_clear"] == OmegaConf.has_resolver(name)

    assert OmegaConf.clear_resolver(name) == expected["result"]
    assert not OmegaConf.has_resolver(name)
