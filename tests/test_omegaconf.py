from typing import Any

import pytest
from pytest import raises

from omegaconf import (
    MISSING,
    BooleanNode,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    StringNode,
)
from omegaconf.errors import UnsupportedInterpolationType

from . import Color, ConcretePlugin, IllegalType, StructuredWithMissing, does_not_raise


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, expected_is_missing, expectation",
    [
        ({}, "foo", False, does_not_raise()),
        ({"foo": True}, "foo", False, does_not_raise()),
        ({"foo": MISSING}, "foo", True, raises(MissingMandatoryValue)),
        (
            {"foo": "${bar}", "bar": MISSING},
            "foo",
            True,
            raises(MissingMandatoryValue),
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
            True,
            raises(MissingMandatoryValue),
        ),
        (StructuredWithMissing, "num", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_num", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "dict", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_dict", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "list", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_list", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "user", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "opt_user", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "inter_user", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "inter_opt_user", True, raises(MissingMandatoryValue)),
        (StructuredWithMissing, "inter_num", True, raises(MissingMandatoryValue)),
    ],
)
def test_is_missing(
    cfg: Any, key: str, expected_is_missing: bool, expectation: Any
) -> None:
    cfg = OmegaConf.create(cfg)
    with expectation:
        cfg.get(key)

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


@pytest.mark.parametrize(  # type: ignore
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
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


@pytest.mark.parametrize(  # type: ignore
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
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


@pytest.mark.parametrize(  # type: ignore
    "cfg, expected",
    [
        (None, False),
        ({}, False),
        ([], False),
        ("aa", False),
        (10, False),
        (True, False),
        (bool, False),
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


@pytest.mark.parametrize("is_optional", [True, False])  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "fac",
    [
        (
            lambda is_optional, missing: StringNode(
                value="foo" if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: IntegerNode(
                value=10 if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: FloatNode(
                value=10 if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: BooleanNode(
                value=True if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: EnumNode(
                enum_type=Color,
                value=Color.RED if not missing else "???",
                is_optional=is_optional,
            )
        ),
        (
            lambda is_optional, missing: ListConfig(
                content=[1, 2, 3] if not missing else "???", is_optional=is_optional
            )
        ),
        (
            lambda is_optional, missing: DictConfig(
                content={"foo": "bar"} if not missing else "???",
                is_optional=is_optional,
            )
        ),
        (
            lambda is_optional, missing: DictConfig(
                ref_type=ConcretePlugin,
                content=ConcretePlugin() if not missing else "???",
                is_optional=is_optional,
            )
        ),
    ],
)
def test_is_optional(fac: Any, is_optional: bool) -> None:
    obj = fac(is_optional, False)
    assert OmegaConf.is_optional(obj) == is_optional

    cfg = OmegaConf.create({"node": obj})
    assert OmegaConf.is_optional(cfg, "node") == is_optional

    obj = fac(is_optional, True)
    assert OmegaConf.is_optional(obj) == is_optional

    cfg = OmegaConf.create({"node": obj})
    assert OmegaConf.is_optional(cfg, "node") == is_optional


@pytest.mark.parametrize("is_none", [True, False])  # type: ignore
@pytest.mark.parametrize(  # type: ignore
    "fac",
    [
        (lambda none: StringNode(value="foo" if not none else None, is_optional=True)),
        (lambda none: IntegerNode(value=10 if not none else None, is_optional=True)),
        (lambda none: FloatNode(value=10 if not none else None, is_optional=True)),
        (lambda none: BooleanNode(value=True if not none else None, is_optional=True)),
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
    assert OmegaConf.is_none(obj) == is_none

    cfg = OmegaConf.create({"node": obj})
    assert OmegaConf.is_none(cfg, "node") == is_none


@pytest.mark.parametrize(
    "fac",  # type: ignore
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
        "EnumNode",
        "ListConfig",
        "DictConfig",
        "ConcretePlugin",
    ],
)
def test_is_interpolation(fac):
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


@pytest.mark.parametrize(  # type: ignore
    "cfg, type_",
    [
        ({"foo": 10}, int),
        ({"foo": 10.0}, float),
        ({"foo": True}, bool),
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


@pytest.mark.parametrize(  # type: ignore
    "obj, type_",
    [
        (10, int),
        (10.0, float),
        (True, bool),
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
