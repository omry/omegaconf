from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List

import attr
import pytest

from omegaconf import DictConfig, OmegaConf, _utils
from omegaconf.errors import ValidationError
from omegaconf.nodes import StringNode

from . import Color, does_not_raise


@pytest.mark.parametrize(  # type: ignore
    "target_type, value, expectation",
    [
        # Any
        (Any, "foo", does_not_raise()),
        (Any, True, does_not_raise()),
        (Any, 1, does_not_raise()),
        (Any, 1.0, does_not_raise()),
        (Any, Color.RED, does_not_raise()),
        # int
        (int, "foo", pytest.raises(ValidationError)),
        (int, True, pytest.raises(ValidationError)),
        (int, 1, does_not_raise()),
        (int, 1.0, pytest.raises(ValidationError)),
        (int, Color.RED, pytest.raises(ValidationError)),
        # float
        (float, "foo", pytest.raises(ValidationError)),
        (float, True, pytest.raises(ValidationError)),
        (float, 1, does_not_raise()),
        (float, 1.0, does_not_raise()),
        (float, Color.RED, pytest.raises(ValidationError)),
        # bool
        (bool, "foo", pytest.raises(ValidationError)),
        (bool, True, does_not_raise()),
        (bool, 1, does_not_raise()),
        (bool, 0, does_not_raise()),
        (bool, 1.0, pytest.raises(ValidationError)),
        (bool, Color.RED, pytest.raises(ValidationError)),
        (bool, "true", does_not_raise()),
        (bool, "false", does_not_raise()),
        (bool, "on", does_not_raise()),
        (bool, "off", does_not_raise()),
        # str
        (str, "foo", does_not_raise()),
        (str, True, does_not_raise()),
        (str, 1, does_not_raise()),
        (str, 1.0, does_not_raise()),
        (str, Color.RED, does_not_raise()),
        # Color
        (Color, "foo", pytest.raises(ValidationError)),
        (Color, True, pytest.raises(ValidationError)),
        (Color, 1, does_not_raise()),
        (Color, 1.0, pytest.raises(ValidationError)),
        (Color, Color.RED, does_not_raise()),
        (Color, "RED", does_not_raise()),
        (Color, "Color.RED", does_not_raise()),
        # bad type
        (Exception, "nope", pytest.raises(ValueError)),
    ],
)
def test_maybe_wrap(target_type: type, value: Any, expectation: Any) -> None:
    with expectation:
        from omegaconf.omegaconf import _maybe_wrap

        _maybe_wrap(
            annotated_type=target_type, value=value, is_optional=False, parent=None
        )


class _TestEnum(Enum):
    A = 1
    B = 2


@dataclass
class _TestDataclass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = field(default_factory=lambda: [])
    dict1: Dict[str, int] = field(default_factory=lambda: {})


@attr.s(auto_attribs=True)
class _TestAttrsClass:
    x: int = 10
    s: str = "foo"
    b: bool = True
    f: float = 3.14
    e: _TestEnum = _TestEnum.A
    list1: List[int] = []
    dict1: Dict[str, int] = {}


class _TestUserClass:
    pass


@pytest.mark.parametrize(  # type: ignore
    "type_, expected",
    [
        (int, True),
        (float, True),
        (bool, True),
        (str, True),
        (Any, True),
        (_TestEnum, True),
        (_TestUserClass, False),
        # Nesting structured configs in contain
        (_TestAttrsClass, True),
        (_TestDataclass, True),
    ],
)
def test_valid_value_annotation_type(type_: type, expected: bool) -> None:
    from omegaconf._utils import _valid_value_annotation_type

    assert _valid_value_annotation_type(type_) == expected


@pytest.mark.parametrize(  # type: ignore
    "test_cls_or_obj, expectation",
    [
        (_TestDataclass, does_not_raise()),
        (_TestDataclass(), does_not_raise()),
        (_TestAttrsClass, does_not_raise()),
        (_TestAttrsClass(), does_not_raise()),
        ("invalid", pytest.raises(ValueError)),
    ],
)
def test_get_structured_config_data(test_cls_or_obj: Any, expectation: Any) -> None:
    with expectation:
        d = _utils.get_structured_config_data(test_cls_or_obj)
        assert d["x"] == 10
        assert d["s"] == "foo"
        assert d["b"] == bool(True)
        assert d["f"] == 3.14
        assert d["e"] == _TestEnum.A
        assert d["list1"] == []
        assert d["dict1"] == {}


def test_is_dataclass(mocker: Any) -> None:
    @dataclass
    class Foo:
        pass

    assert _utils.is_dataclass(Foo)
    assert _utils.is_dataclass(Foo())
    assert not _utils.is_dataclass(10)

    mocker.patch("omegaconf._utils.dataclasses", None)
    assert not _utils.is_dataclass(10)


def test_is_attr_class(mocker: Any) -> None:
    @attr.s
    class Foo:
        pass

    assert _utils.is_attr_class(Foo)
    assert _utils.is_attr_class(Foo())

    assert not _utils.is_attr_class(10)
    mocker.patch("omegaconf._utils.attr", None)
    assert not _utils.is_attr_class(10)


def test_is_structured_config_frozen_with_invalid_obj() -> None:
    with pytest.raises(ValueError):
        _utils.is_structured_config_frozen(10)


@dataclass
class Dataclass:
    pass


@pytest.mark.parametrize(  # type: ignore
    "value,kind",
    [
        ("foo", _utils.ValueKind.VALUE),
        (1, _utils.ValueKind.VALUE),
        (1.0, _utils.ValueKind.VALUE),
        (True, _utils.ValueKind.VALUE),
        (False, _utils.ValueKind.VALUE),
        (Color.GREEN, _utils.ValueKind.VALUE),
        (Dataclass, _utils.ValueKind.VALUE),
        ("???", _utils.ValueKind.MANDATORY_MISSING),
        ("${foo.bar}", _utils.ValueKind.INTERPOLATION),
        ("ftp://${host}/path", _utils.ValueKind.STR_INTERPOLATION),
    ],
)
def test_value_kind(value: Any, kind: _utils.ValueKind) -> None:
    assert _utils.get_value_kind(value) == kind


def test_re_parent() -> None:
    def validate(cfg1: DictConfig) -> None:
        assert cfg1._get_parent() is None
        assert cfg1.get_node("str")._get_parent() == cfg1
        assert cfg1.get_node("list")._get_parent() == cfg1
        assert cfg1.list.get_node(0)._get_parent() == cfg1.list

    cfg = OmegaConf.create({})
    assert isinstance(cfg, DictConfig)
    cfg.str = StringNode("str")
    cfg.list = [1]

    validate(cfg)

    cfg.get_node("str")._set_parent(None)
    cfg.get_node("list")._set_parent(None)
    cfg.list.get_node(0)._set_parent(None)  # type: ignore
    # noinspection PyProtectedMember
    cfg._re_parent()
    validate(cfg)
