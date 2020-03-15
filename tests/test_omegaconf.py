from typing import Any, Optional, Type

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

from . import Color, ConcretePlugin, StructuredWithMissing, does_not_raise


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
    "cfg, is_conf, is_list, is_dict, type_",
    [
        (None, False, False, False, None),
        ({}, False, False, False, None),
        ("aa", False, False, False, None),
        (10, False, False, False, None),
        (True, False, False, False, None),
        (bool, False, False, False, None),
        (StringNode("foo"), False, False, False, None),
        (OmegaConf.create({}), True, False, True, None),
        (OmegaConf.create([]), True, True, False, None),
        (OmegaConf.structured(ConcretePlugin), True, False, True, ConcretePlugin),
        (OmegaConf.structured(ConcretePlugin()), True, False, True, ConcretePlugin),
    ],
)
def test_is_config(
    cfg: Any, is_conf: bool, is_list: bool, is_dict: bool, type_: Type[Any]
) -> None:
    assert OmegaConf.is_config(cfg) == is_conf
    assert OmegaConf.is_list(cfg) == is_list
    assert OmegaConf.is_dict(cfg) == is_dict
    assert OmegaConf.get_type(cfg) == type_


@pytest.mark.parametrize(  # type: ignore
    "is_optional", [True, False]
)
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
                annotated_type=ConcretePlugin,
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


@pytest.mark.parametrize(  # type: ignore
    "is_none", [True, False]
)
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
                content={"foo": "bar"} if not none else None, is_optional=True,
            )
        ),
        (
            lambda none: DictConfig(
                annotated_type=ConcretePlugin,
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
                content={"foo": "bar"} if inter is None else inter, is_optional=True,
            )
        ),
        (
            lambda inter: DictConfig(
                annotated_type=ConcretePlugin,
                content=ConcretePlugin() if inter is None else inter,
                is_optional=True,
            )
        ),
    ],
)
def test_is_interpolation(fac):
    obj = fac(inter=None)
    assert not OmegaConf.is_interpolation(obj)
    cfg = OmegaConf.create({"node": obj})
    assert not OmegaConf.is_interpolation(cfg, "node")

    for inter in ["${foo}", "http://${url}", "${resolver:value}"]:
        obj = fac(inter=inter)
        assert OmegaConf.is_interpolation(obj)
        cfg = OmegaConf.create({"node": obj})
        assert OmegaConf.is_interpolation(cfg, "node")
