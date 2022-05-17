import re
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional, Type, Union

from pytest import mark, param, raises

import tests
from omegaconf import (
    BytesNode,
    DictConfig,
    FloatNode,
    IntegerNode,
    ListConfig,
    OmegaConf,
    PathNode,
    ReadonlyConfigError,
    StringNode,
    UnionNode,
    UnsupportedValueType,
    ValidationError,
)
from omegaconf._utils import format_and_raise, type_str
from omegaconf.errors import (
    ConfigAttributeError,
    ConfigKeyError,
    ConfigTypeError,
    ConfigValueError,
    GrammarParseError,
    InterpolationKeyError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
    InterpolationValidationError,
    KeyValidationError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)
from tests import (
    A,
    Color,
    ConcretePlugin,
    IllegalType,
    Module,
    NestedInterpolationToMissing,
    Package,
    Plugin,
    Str2Int,
    StructuredInterpolationKeyError,
    StructuredInterpolationValidationError,
    StructuredWithBadDict,
    StructuredWithBadList,
    StructuredWithMissing,
    SubscriptedDict,
    UnionError,
    User,
    warns_dict_subclass_deprecated,
)


# tests classes
@dataclass
class NotOptionalInt:
    foo: int = None  # type:ignore


@dataclass
class NotOptionalA:
    x: A = None  # type: ignore


@dataclass
class Expected:
    exception_type: Type[Exception]
    msg: str
    msg_is_regex: bool = False

    # "Low level exceptions" are thrown from internal APIs are are not populating all the fields
    low_level: bool = False
    key: Any = None
    # "AUTO" : determine automatically based on OmegaConf.get_type(cfg)
    object_type: Any = "AUTO"
    ref_type: Any = None

    # "AUTO: full_key is key
    full_key: Any = "AUTO"
    create: Any = lambda: None
    op: Any = lambda _cfg: None
    child_node: Any = lambda cfg: None
    parent_node: Any = lambda cfg: cfg

    object_type_str: Optional[str] = "AUTO"
    ref_type_str: Optional[str] = "AUTO"
    num_lines: int = 2

    def finalize(self, cfg: Any) -> None:
        if self.object_type == "AUTO":
            self.object_type = OmegaConf.get_type(cfg)

        if self.object_type_str == "AUTO":
            self.object_type_str = type_str(self.object_type)
        if self.ref_type_str == "AUTO" and self.ref_type is not None:
            self.ref_type_str = type_str(self.ref_type)
            self.num_lines = self.num_lines + 1

        if self.full_key == "AUTO":
            if self.key is None:
                self.full_key = ""
            else:
                if isinstance(self.key, (str, bytes, int, Enum, float, bool, slice)):
                    self.full_key = self.key
                else:
                    self.full_key = ""


params = [
    ##############
    # DictConfig #
    ##############
    # update
    param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredWithMissing),
            op=lambda cfg: OmegaConf.update(cfg, "num", "hello"),
            exception_type=ValidationError,
            msg="Value 'hello' of type 'str' could not be converted to Integer",
            parent_node=lambda cfg: cfg,
            child_node=lambda cfg: cfg._get_node("num"),
            object_type=StructuredWithMissing,
            key="num",
        ),
        id="structured:update_with_invalid_value",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredWithMissing),
            op=lambda cfg: OmegaConf.update(cfg, "num", None),
            exception_type=ValidationError,
            msg="field 'num' is not Optional",
            parent_node=lambda cfg: cfg,
            child_node=lambda cfg: cfg._get_node("num"),
            object_type=StructuredWithMissing,
            key="num",
        ),
        id="structured:update:none_to_non_optional",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({}),
            op=lambda cfg: OmegaConf.update(cfg, "a", IllegalType()),
            key="a",
            exception_type=UnsupportedValueType,
            msg="Value 'IllegalType' is not a supported primitive type",
        ),
        id="dict:update:object_of_illegal_type",
    ),
    # pop
    param(
        Expected(
            create=lambda: create_readonly({"foo": "bar"}),
            op=lambda cfg: cfg.pop("foo"),
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
            exception_type=ReadonlyConfigError,
            msg="Cannot pop from read-only node",
        ),
        id="dict,readonly:pop",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "bar"}),
            op=lambda cfg: cfg.pop("not_found"),
            key="not_found",
            exception_type=ConfigKeyError,
            msg="Key not found: 'not_found'",
        ),
        id="dict:pop_invalid",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": {}}),
            op=lambda cfg: cfg.foo.pop("not_found"),
            key="not_found",
            full_key="foo.not_found",
            parent_node=lambda cfg: cfg.foo,
            exception_type=ConfigKeyError,
            msg="Key not found: 'not_found' (path: 'foo.not_found')",
        ),
        id="dict:pop_invalid_nested",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "bar"}),
            op=lambda cfg: cfg.__delitem__("not_found"),
            key="not_found",
            exception_type=ConfigKeyError,
            msg="Key not found: 'not_found'",
        ),
        id="dict:del_invalid",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": {}}),
            op=lambda cfg: cfg.foo.__delitem__("not_found"),
            key="not_found",
            full_key="foo.not_found",
            parent_node=lambda cfg: cfg.foo,
            exception_type=ConfigKeyError,
            msg="Key not found: 'not_found'",
        ),
        id="dict:del_invalid_nested",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: getattr(cfg, "fail"),
            exception_type=ConfigAttributeError,
            msg="Key 'fail' not in 'ConcretePlugin'",
            key="fail",
            object_type=ConcretePlugin,
        ),
        id="structured:access_invalid_attribute",
    ),
    # getattr
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: getattr(cfg, "fail"),
            exception_type=ConfigAttributeError,
            msg="Key 'fail' is not in struct",
            key="fail",
        ),
        id="dict,struct:access_invalid_attribute",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "${missing}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationKeyError,
            msg="Interpolation key 'missing' not found",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "${missing[a].b[c]}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationKeyError,
            msg="Interpolation key 'missing[a].b[c]' not found",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_interpolation_with_full_path",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "foo_${missing}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationKeyError,
            msg="Interpolation key 'missing' not found",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_str_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": {"bar": "${.missing}"}}),
            op=lambda cfg: getattr(cfg.foo, "bar"),
            exception_type=InterpolationKeyError,
            msg="Interpolation key 'missing' not found",
            key="bar",
            full_key="foo.bar",
            child_node=lambda cfg: cfg.foo._get_node("bar"),
            parent_node=lambda cfg: cfg.foo,
        ),
        id="dict,accessing_missing_relative_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "${..missing}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationKeyError,
            msg="ConfigKeyError while resolving interpolation: Error resolving key '..missing'",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_invalid_double_relative_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "${int.missing}", "int": 0}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationResolutionError,
            msg=(
                "ConfigTypeError raised while resolving interpolation: Error trying to access int.missing: "
                "node `int` is not a container and thus cannot contain `missing`"
            ),
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_non_container_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create(
                {"foo": "${${missing_val}}", "missing_val": "???"}
            ),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=InterpolationToMissingValueError,
            msg=(
                "MissingMandatoryValue while resolving interpolation: "
                "Missing mandatory value: missing_val"
            ),
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_nested_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredInterpolationValidationError),
            op=lambda cfg: getattr(cfg, "y"),
            exception_type=InterpolationValidationError,
            object_type=StructuredInterpolationValidationError,
            msg=(
                "While dereferencing interpolation '${.x}': "
                "Incompatible value 'None' for field of type 'int'"
            ),
            key="y",
            child_node=lambda cfg: cfg._get_node("y"),
        ),
        id="dict,non_optional_field_with_interpolation_to_none",
    ),
    # setattr
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: setattr(cfg, "zlonk", "zlank"),
            exception_type=ConfigAttributeError,
            msg="Key 'zlonk' is not in struct",
            key="zlonk",
        ),
        id="dict,struct:set_invalid_attribute",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: setattr(cfg, "params", 20),
            exception_type=ValidationError,
            msg="Invalid type assigned: int is not a subclass of FoobarParams. value: 20",
            key="params",
            object_type=ConcretePlugin,
            child_node=lambda cfg: cfg.params,
        ),
        id="structured:setattr,invalid_type_assigned_to_structured",
    ),
    param(
        Expected(
            create=lambda: create_readonly({"foo": "bar"}),
            op=lambda cfg: setattr(cfg, "foo", 20),
            exception_type=ReadonlyConfigError,
            msg="Cannot change read-only config container",
            key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict,readonly:set_attribute",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create(
                {"foo": DictConfig(is_optional=False, content={})}
            ),
            op=lambda cfg: setattr(cfg, "foo", None),
            exception_type=ValidationError,
            msg="field 'foo' is not Optional",
            key="foo",
            full_key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict:setattr:not_optional:set_none",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: cfg.params.__setattr__("foo", "bar"),
            exception_type=ValidationError,
            msg="Value 'bar' of type 'str' could not be converted to Integer",
            key="foo",
            full_key="params.foo",
            object_type=ConcretePlugin.FoobarParams,
            ref_type=ConcretePlugin.FoobarParams,
            child_node=lambda cfg: cfg.params.foo,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:setattr,invalid_type_assigned_to_field",
    ),
    # setitem
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.__setitem__("zoo", "zonk"),
            exception_type=KeyError,
            msg="Key 'zoo' is not in struct",
            key="zoo",
        ),
        id="dict,struct:setitem_on_none_existing_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=Color, element_type=str, content={}),
            op=lambda cfg: cfg.__setitem__("foo", "bar"),
            exception_type=KeyValidationError,
            msg="Key 'foo' is incompatible with the enum type 'Color', valid: [RED, GREEN, BLUE]",
            full_key="foo",
            key="foo",
        ),
        id="DictConfig[Color,str]:setitem_bad_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=Color, element_type=str, content={}),
            op=lambda cfg: cfg.__setitem__(None, "bar"),
            exception_type=KeyValidationError,
            msg="Key 'None' is incompatible with the enum type 'Color', valid: [RED, GREEN, BLUE]",
            key=None,
        ),
        id="DictConfig[Color,str]:setitem_bad_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=str, element_type=Color, content={}),
            op=lambda cfg: cfg.__setitem__("foo", "bar"),
            exception_type=ValidationError,
            msg="Invalid value 'bar', expected one of [RED, GREEN, BLUE]",
            full_key="foo",
            key="foo",
        ),
        id="DictConfig[str,Color]:setitem_bad_value",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(User),
            op=lambda cfg: cfg.__setitem__("name", [1, 2]),
            exception_type=ValidationError,
            msg="Cannot convert 'list' to string: '[1, 2]'",
            full_key="name",
            key="name",
            low_level=True,
        ),
        id="DictConfig[Any,Any]:setitem_stringnode_bad_value",
    ),
    # getitem
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.__getitem__("zoo"),
            exception_type=KeyError,
            msg="Key 'zoo' is not in struct",
            key="zoo",
        ),
        id="dict,struct:getitem_key_not_in_struct",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=Color, element_type=str, content={}),
            op=lambda cfg: cfg.__getitem__("foo"),
            exception_type=KeyValidationError,
            msg="Key 'foo' is incompatible with the enum type 'Color', valid: [RED, GREEN, BLUE]",
            key="foo",
        ),
        id="DictConfig[Color,str]:getitem_str_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=Color, element_type=str, content={}),
            op=lambda cfg: cfg.__getitem__(None),
            exception_type=KeyValidationError,
            msg="Key 'None' is incompatible with the enum type 'Color', valid: [RED, GREEN, BLUE]",
            key=None,
        ),
        id="DictConfig[Color,str]:getitem_str_key_None",
    ),
    param(
        Expected(
            create=lambda: DictConfig(key_type=str, element_type=str, content={}),
            op=lambda cfg: cfg.__getitem__(Color.RED),
            exception_type=KeyValidationError,
            msg="Key Color.RED (Color) is incompatible with (str)",
            full_key="RED",
            key=Color.RED,
        ),
        id="DictConfig[str,str]:getitem_color_key",
    ),
    param(
        Expected(
            create=lambda: create_readonly({"foo1": "bar"}),
            op=lambda cfg: cfg.merge_with({"foo2": "bar"}),
            exception_type=ReadonlyConfigError,
            key="foo2",
            msg="Cannot change read-only config container",
        ),
        id="dict,readonly:merge_with",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: OmegaConf.merge(cfg, {"params": {"foo": "bar"}}),
            exception_type=ValidationError,
            msg="Value 'bar' of type 'str' could not be converted to Integer",
            key="foo",
            full_key="params.foo",
            object_type=ConcretePlugin.FoobarParams,
            ref_type=tests.ConcretePlugin.FoobarParams,
            child_node=lambda cfg: cfg.params.foo,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:merge,invalid_field_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: OmegaConf.merge(cfg, {"params": {"zlonk": 10}}),
            exception_type=ConfigKeyError,
            msg="Key 'zlonk' not in 'FoobarParams'",
            key="zlonk",
            full_key="params.zlonk",
            object_type=ConcretePlugin.FoobarParams,
            ref_type=ConcretePlugin.FoobarParams,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:merge,adding_an_invalid_key",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(Package),
            op=lambda cfg: OmegaConf.merge(cfg, {"modules": [{"foo": "var"}]}),
            exception_type=ConfigKeyError,
            msg="Key 'foo' not in 'Module'",
            key="foo",
            full_key="modules[0].foo",
            object_type=Module,
            low_level=True,
        ),
        id="structured:merge,bad_key_merge",
    ),
    # merge_with
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: cfg.merge_with(Plugin),
            exception_type=ValidationError,
            msg="Plugin is not a subclass of ConcretePlugin. value: {'name': '???', 'params': '???'}",
            object_type=ConcretePlugin,
        ),
        id="structured:merge_invalid_dataclass",
    ),
    # get
    param(
        Expected(
            create=lambda: OmegaConf.create(),
            op=lambda cfg: cfg.get(IllegalType),
            exception_type=KeyValidationError,
            msg="Incompatible key type 'type'",
            key=IllegalType,
            full_key="",
        ),
        id="dict:get_illegal_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create(),
            op=lambda cfg: cfg.get(IllegalType()),
            exception_type=KeyValidationError,
            msg="Incompatible key type 'IllegalType'",
            key=IllegalType(),
        ),
        id="dict:get_object_of_illegal_type",
    ),
    param(
        Expected(
            create=lambda: DictConfig({}, key_type=int),
            op=lambda cfg: cfg.get("foo"),
            exception_type=KeyValidationError,
            msg="Key foo (str) is incompatible with (int)",
            key="foo",
            full_key="foo",
        ),
        id="dict[int,Any]:mistyped_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig({}, key_type=float),
            op=lambda cfg: cfg.get("foo"),
            exception_type=KeyValidationError,
            msg="Key foo (str) is incompatible with (float)",
            key="foo",
            full_key="foo",
        ),
        id="dict[float,Any]:mistyped_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig({}, key_type=bool),
            op=lambda cfg: cfg.get("foo"),
            exception_type=KeyValidationError,
            msg="Key foo (str) is incompatible with (bool)",
            key="foo",
            full_key="foo",
        ),
        id="dict[bool,Any]:mistyped_key",
    ),
    param(
        Expected(
            create=lambda: DictConfig({}, key_type=bytes),
            op=lambda cfg: cfg.get("foo"),
            exception_type=KeyValidationError,
            msg="Key foo (str) is incompatible with (bytes)",
            key="foo",
            full_key="foo",
        ),
        id="dict[bool,Any]:mistyped_key",
    ),
    # dict:create
    param(
        Expected(
            create=lambda: None,
            op=lambda _: OmegaConf.structured(NotOptionalInt),
            exception_type=ValidationError,
            msg="Incompatible value 'None' for field of type 'int'",
            key="foo",
            full_key="foo",
            parent_node=lambda _: {},
            object_type=NotOptionalInt,
        ),
        id="dict:create_non_optional_with_none",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda _: OmegaConf.structured(NotOptionalInt),
            exception_type=ValidationError,
            msg="Incompatible value 'None' for field of type 'int'",
            key="foo",
            full_key="foo",
            parent_node=lambda _: {},
            object_type=NotOptionalInt,
        ),
        id="dict:create:not_optional_int_field_with_none",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(NotOptionalA),
            exception_type=ValidationError,
            object_type=None,
            key=None,
            full_key="x",
            msg="field 'x' is not Optional",
            object_type_str="NotOptionalInt",
            ref_type=A,
        ),
        id="dict:create:not_optional_A_field_with_none",
    ),
    param(
        Expected(
            create=lambda: DictConfig({}, element_type=str),
            op=lambda cfg: OmegaConf.merge(cfg, {"foo": None}),
            exception_type=ValidationError,
            key="foo",
            msg="field 'foo' is not Optional",
        ),
        id="dict:merge_none_into_not_optional_element_type",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(IllegalType),
            exception_type=ValidationError,
            msg="Input class 'IllegalType' is not a structured config. did you forget to decorate it as a dataclass?",
            object_type_str=None,
            ref_type_str=None,
        ),
        id="dict_create_from_illegal_type",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda _: OmegaConf.structured(
                ConcretePlugin(params=ConcretePlugin.FoobarParams(foo="x"))  # type: ignore
            ),
            exception_type=ValidationError,
            msg="Value 'x' of type 'str' could not be converted to Integer",
            key="foo",
            full_key="foo",
            parent_node=lambda _: {},
            object_type=ConcretePlugin.FoobarParams,
        ),
        id="structured:create_with_invalid_value,int",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": FloatNode(123.456)}),
            op=lambda cfg: cfg.__setattr__("bar", "x"),
            exception_type=ValidationError,
            msg="Value 'x' of type 'str' could not be converted to Float",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,str_to_float",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": FloatNode(123.456)}),
            op=lambda cfg: cfg.__setattr__("bar", Path("hello.txt")),
            exception_type=ValidationError,
            msg="Value 'hello.txt' of type 'pathlib.(Posix|Windows)Path' could not be converted to Float",
            msg_is_regex=True,
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,path_to_float",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": BytesNode(b"binary")}),
            op=lambda cfg: cfg.__setattr__("bar", 123.4),
            exception_type=ValidationError,
            msg="Value '123.4' of type 'float' is not of type 'bytes'",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,string_to_bytes",
    ),
    param(
        Expected(
            create=lambda: DictConfig(
                {"bar": BytesNode(b"binary", flags={"convert": False})}
            ),
            op=lambda cfg: cfg.__setattr__("bar", 123.4),
            exception_type=ValidationError,
            msg="Value '123.4' of type 'float' is incompatible with type hint 'Optional[bytes]'",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,string_to_bytes,no_convert",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": PathNode(Path("hello.txt"))}),
            op=lambda cfg: cfg.__setattr__("bar", 123.4),
            exception_type=ValidationError,
            msg="Value '123.4' of type 'float' could not be converted to Path",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,string_to_path",
    ),
    param(
        Expected(
            create=lambda: DictConfig(
                {"bar": PathNode(Path("hello.txt"), flags={"convert": False})}
            ),
            op=lambda cfg: cfg.__setattr__("bar", 123.4),
            exception_type=ValidationError,
            msg="Value '123.4' of type 'float' is not an instance of 'pathlib.Path'",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,string_to_path,no_convert",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": StringNode("abc123")}),
            op=lambda cfg: cfg.__setattr__("bar", b"binary"),
            exception_type=ValidationError,
            msg=r"Cannot convert 'bytes' to string: 'b'binary''",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,bytes_to_string",
    ),
    param(
        Expected(
            create=lambda: DictConfig(
                {"bar": StringNode("abc123")}, flags={"convert": False}
            ),
            op=lambda cfg: cfg.__setattr__("bar", b"binary"),
            exception_type=ValidationError,
            msg=r"Value 'b'binary'' of type 'bytes' is incompatible with type hint 'Optional[str]'",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,bytes_to_string,parent_no_convert",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"bar": FloatNode(123.456)}),
            op=lambda cfg: cfg.__setattr__("bar", Color.BLUE),
            exception_type=ValidationError,
            msg="Value 'Color.BLUE' of type 'tests.Color' could not be converted to Float",
            key="bar",
            full_key="bar",
            child_node=lambda cfg: cfg._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value,full_module_in_error",
    ),
    param(
        Expected(
            create=lambda: DictConfig(
                {"foo": {"bar": UnionNode(123.456, Union[bool, float])}}
            ),
            op=lambda cfg: cfg.foo.__setattr__("bar", "abc"),
            exception_type=ValidationError,
            msg=re.escape(
                "Value 'abc' of type 'str' is incompatible with type hint 'Optional[Union["
            )
            + r"(bool, float)|(float, bool)\]\]'",
            msg_is_regex=True,
            key="bar",
            full_key="foo.bar",
            parent_node=lambda cfg: cfg.foo,
            child_node=lambda cfg: cfg.foo._get_node("bar"),
        ),
        id="typed_DictConfig:assign_with_invalid_value-string_to_union[bool-float]",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(IllegalType()),
            exception_type=ValidationError,
            msg="Object of unsupported type: 'IllegalType'",
            object_type_str=None,
            ref_type_str=None,
        ),
        id="structured:create_from_unsupported_object",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda _: DictConfig({}, element_type=IllegalType),
            exception_type=ValidationError,
            msg="Unsupported value type: 'tests.IllegalType'",
        ),
        id="structured:create_with_unsupported_element_type",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(UnionError),
            exception_type=ValueError,
            msg="Unions of containers are not supported:\nx: Union[int, List[str]]",
            num_lines=3,
        ),
        id="structured:create_with_union_error",
    ),
    # assign
    param(
        Expected(
            create=lambda: DictConfig(ref_type=ConcretePlugin, content="???"),
            op=lambda cfg: cfg._set_value(1),
            exception_type=ValidationError,
            msg="Invalid type assigned: int is not a subclass of ConcretePlugin. value: 1",
            low_level=True,
            ref_type=Optional[ConcretePlugin],
        ),
        id="dict:set_value:reftype_mismatch",
    ),
    param(
        Expected(
            create=lambda: DictConfig(
                key_type=str, element_type=int, content={"foo": 10, "bar": 20}
            ),
            op=lambda cfg: cfg.__setitem__("baz", "fail"),
            exception_type=ValidationError,
            msg="Value 'fail' of type 'str' could not be converted to Integer",
            key="baz",
        ),
        id="DictConfig[str,int]:assigned_str_value",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(SubscriptedDict),
            op=lambda cfg: cfg.__setitem__("dict_str", 1),
            exception_type=ValidationError,
            msg="Cannot assign int to Dict[str, int]",
            key="dict_str",
            ref_type=Optional[Dict[str, int]],
            low_level=True,
        ),
        id="DictConfig[str,int]:assigned_primitive_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(SubscriptedDict),
            op=lambda cfg: cfg.__setitem__("dict_str", User(age=2, name="bar")),
            exception_type=ValidationError,
            msg="Cannot assign User to Dict[str, int]",
            key="dict_str",
            ref_type=Optional[Dict[str, int]],
            low_level=True,
        ),
        id="DictConfig[str,int]:assigned_structured_config",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(SubscriptedDict),
            op=lambda cfg: cfg.__setitem__("dict_int", "fail"),
            exception_type=ValidationError,
            msg="Cannot assign str to Dict[int, int]",
            key="dict_int",
            ref_type=Optional[Dict[int, int]],
            low_level=True,
        ),
        id="DictConfig[int,int]:assigned_primitive_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(SubscriptedDict),
            op=lambda cfg: cfg.__setitem__("dict_int", User(age=2, name="bar")),
            exception_type=ValidationError,
            msg="Cannot assign User to Dict[int, int]",
            key="dict_int",
            ref_type=Optional[Dict[int, int]],
            low_level=True,
        ),
        id="DictConfig[int,int]:assigned_structured_config",
    ),
    # delete
    param(
        Expected(
            create=lambda: create_readonly({"foo": "bar"}),
            op=lambda cfg: cfg.__delitem__("foo"),
            exception_type=ReadonlyConfigError,
            msg="DictConfig in read-only mode does not support deletion",
            key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict,readonly:del",
    ),
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.__delitem__("foo"),
            exception_type=ConfigTypeError,
            msg="DictConfig in struct mode does not support deletion",
            key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict,struct:del",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(User(name="bond")),
            op=lambda cfg: cfg.__delitem__("name"),
            exception_type=ConfigTypeError,
            msg="User (DictConfig) does not support deletion",
            object_type=User,
            key="name",
            child_node=lambda cfg: cfg.name,
        ),
        id="dict,structured:del",
    ),
    param(
        Expected(
            create=lambda: create_readonly({"foo": "bar"}),
            op=lambda cfg: cfg.__delattr__("foo"),
            exception_type=ReadonlyConfigError,
            msg="DictConfig in read-only mode does not support deletion",
            key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict,readonly:delattr",
    ),
    # creating structured config
    param(
        Expected(
            create=lambda: None,
            op=lambda _: OmegaConf.structured(StructuredWithBadDict),
            exception_type=ValidationError,
            msg="Cannot assign int to Dict[str, str]",
            key="foo",
        ),
        id="structured,bad_default_value_for_dict",
    ),
    param(
        Expected(
            create=lambda: None,
            op=lambda _: OmegaConf.structured(StructuredWithBadList),
            exception_type=ValidationError,
            msg="Invalid value assigned: int is not a ListConfig, list or tuple.",
            key="foo",
        ),
        id="structured,bad_default_value_for_list",
    ),
    ##############
    # ListConfig #
    ##############
    # getattr
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: setattr(cfg, "foo", 10),
            exception_type=ConfigAttributeError,
            key="foo",
            full_key="[foo]",
            msg="ListConfig does not support attribute access",
        ),
        id="list:setattr",
    ),
    # setattr
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=ConfigAttributeError,
            key="foo",
            full_key="[foo]",
            msg="ListConfig does not support attribute access",
        ),
        id="list:setattr",
    ),
    # get node
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg._get_node("foo"),
            exception_type=KeyValidationError,
            key="foo",
            full_key="[foo]",
            msg="ListConfig indices must be integers or slices, not str",
        ),
        id="list:get_nox_ex:invalid_index_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg._get_node(20),
            exception_type=IndexError,
            msg="list index out of range",
            key=20,
            full_key="[20]",
        ),
        id="list:get_node_ex:index_out_of_range",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg._get_node(20),
            exception_type=TypeError,
            msg="Cannot get_node from a ListConfig object representing None",
            key=20,
            full_key="[20]",
        ),
        id="list:get_node_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg._get_node(20),
            exception_type=MissingMandatoryValue,
            msg="Cannot get_node from a missing ListConfig",
            key=20,
            full_key="[20]",
        ),
        id="list:get_node_missing",
    ),
    # list:create
    param(
        Expected(
            create=lambda: None,
            op=lambda cfg: ListConfig(is_optional=False, content=None),
            exception_type=ValidationError,
            object_type=None,
            msg="Non optional ListConfig cannot be constructed from None",
            object_type_str=None,
            ref_type_str=None,
        ),
        id="list:create:not_optional_with_none",
    ),
    # append
    param(
        Expected(
            create=lambda: OmegaConf.create([]),
            op=lambda cfg: cfg.append(IllegalType()),
            exception_type=UnsupportedValueType,
            msg="Value 'IllegalType' is not a supported primitive type",
            key=0,
            full_key="[0]",
        ),
        id="list:append_value_of_illegal_type",
    ),
    # pop
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.pop(0),
            exception_type=ReadonlyConfigError,
            msg="Cannot pop from read-only ListConfig",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
        ),
        id="list:readonly:pop",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg.pop("Invalid_key_type"),
            exception_type=ConfigTypeError,
            msg="ListConfig indices must be integers or slices, not str",
            key="Invalid_key_type",
            full_key="[Invalid_key_type]",
        ),
        id="list:pop_invalid_key",
    ),
    param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.pop("foo"),
            exception_type=ConfigTypeError,
            msg="DictConfig in struct mode does not support pop",
            key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict,struct:pop",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: cfg.pop("name"),
            exception_type=ConfigTypeError,
            msg="ConcretePlugin (DictConfig) does not support pop",
            key="name",
            child_node=lambda cfg: cfg.name,
        ),
        id="dict,structured:pop",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.pop(0),
            exception_type=TypeError,
            msg="Cannot pop from a ListConfig object representing None",
            key=0,
            full_key="[0]",
        ),
        id="list:pop_from_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.pop(0),
            exception_type=MissingMandatoryValue,
            msg="Cannot pop from a missing ListConfig",
            key=0,
            full_key="[0]",
        ),
        id="list:pop_from_missing",
    ),
    # getitem
    param(
        Expected(
            create=lambda: OmegaConf.create(["???"]),
            op=lambda cfg: cfg.__getitem__(slice(0, 1)),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value: [0:1]",
            key=slice(0, 1),
            full_key="[0:1]",
            child_node=lambda cfg: cfg._get_node(slice(0, 1)),
        ),
        id="list:subscript_slice_with_missing",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([10, "???"]),
            op=lambda cfg: cfg.__getitem__(1),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value: [1]",
            key=1,
            full_key="[1]",
            child_node=lambda cfg: cfg._get_node(1),
        ),
        id="list:subscript_index_with_missing",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg.__getitem__(20),
            exception_type=IndexError,
            msg="list index out of range",
            key=20,
            full_key="[20]",
        ),
        id="list:subscript:index_out_of_range",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg.__getitem__("foo"),
            exception_type=KeyValidationError,
            msg="ListConfig indices must be integers or slices, not str",
            key="foo",
            full_key="[foo]",
        ),
        id="list:getitem,illegal_key_type",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.__getitem__(0),
            exception_type=TypeError,
            msg="ListConfig object representing None is not subscriptable",
            key=0,
            full_key="[0]",
        ),
        id="list:getitem,illegal_key_type",
    ),
    # setitem
    param(
        Expected(
            create=lambda: OmegaConf.create([None]),
            op=lambda cfg: cfg.__setitem__(0, IllegalType()),
            exception_type=UnsupportedValueType,
            msg="Value 'IllegalType' is not a supported primitive type",
            key=0,
            full_key="[0]",
        ),
        id="list:setitem,illegal_value_type",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg.__setitem__("foo", 4),
            exception_type=KeyValidationError,
            msg="ListConfig indices must be integers or slices, not str",
            key="foo",
            full_key="[foo]",
        ),
        id="list:setitem,illegal_key_type",
    ),
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.__setitem__(0, 4),
            exception_type=ReadonlyConfigError,
            msg="ListConfig is read-only",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
        ),
        id="list,readonly:setitem",
    ),
    # _set_value
    param(
        Expected(
            create=lambda: ListConfig(is_optional=False, element_type=int, content=[]),
            op=lambda cfg: cfg._set_value(None),
            exception_type=ValidationError,
            object_type=None,
            msg="Non optional ListConfig cannot be constructed from None",
            low_level=True,
        ),
        id="list:create_not_optional:_set_value(None)",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=[1, 2]),
            op=lambda cfg: cfg._set_value(True),
            exception_type=ValidationError,
            object_type=None,
            msg="Invalid value assigned: bool is not a ListConfig, list or tuple.",
            ref_type=List[int],
            low_level=True,
        ),
        id="list:create_not_optional:_set_value(True)",
    ),
    # assign
    param(
        Expected(
            create=lambda: ListConfig(element_type=int, content=[1, 2, 3]),
            op=lambda cfg: cfg.__setitem__(0, "foo"),
            exception_type=ValidationError,
            msg="Value 'foo' of type 'str' could not be converted to Integer",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
        ),
        id="list,int_elements:assigned_str_element",
    ),
    param(
        Expected(
            # make sure OmegaConf.create is not losing critical metadata.
            create=lambda: OmegaConf.create(
                ListConfig(element_type=int, content=[1, 2, 3])
            ),
            op=lambda cfg: cfg.__setitem__(0, "foo"),
            exception_type=ValidationError,
            msg="Value 'foo' of type 'str' could not be converted to Integer",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
        ),
        id="list,int_elements:assigned_str_element",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.create(
                [IntegerNode(is_optional=False, value=0), 2, 3]
            ),
            op=lambda cfg: cfg.__setitem__(0, None),
            exception_type=ValidationError,
            msg="[0] is not optional and cannot be assigned None",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
        ),
        id="list,not_optional:null_assignment",
    ),
    # index
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.index(99),
            exception_type=ConfigValueError,
            msg="Item not found in ListConfig",
        ),
        id="list,readonly:index_not_found",
    ),
    # insert
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.insert(1, 99),
            exception_type=ReadonlyConfigError,
            msg="Cannot insert into a read-only ListConfig",
            key=1,
            full_key="[1]",
            child_node=lambda cfg: cfg[1],
        ),
        id="list,readonly:insert",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.insert(1, 99),
            exception_type=ConfigTypeError,
            msg="Cannot insert into ListConfig object representing None",
            key=1,
            full_key="[1]",
        ),
        id="list:insert_into_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.insert(1, 99),
            exception_type=MissingMandatoryValue,
            msg="Cannot insert into missing ListConfig",
            key=1,
            full_key="[1]",
            child_node=lambda _cfg: None,
        ),
        id="list:insert_into_missing",
    ),
    # get
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.get(0),
            exception_type=TypeError,
            msg="Cannot get from a ListConfig object representing None",
            key=0,
            full_key="[0]",
        ),
        id="list:get_from_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.get(0),
            exception_type=MissingMandatoryValue,
            msg="Cannot get from a missing ListConfig",
            key=0,
            full_key="[0]",
        ),
        id="list:get_from_missing",
    ),
    # sort
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.sort(),
            exception_type=ReadonlyConfigError,
            msg="Cannot sort a read-only ListConfig",
        ),
        id="list:readonly:sort",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.sort(),
            exception_type=TypeError,
            msg="Cannot sort a ListConfig object representing None",
        ),
        id="list:sort_from_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.sort(),
            exception_type=MissingMandatoryValue,
            msg="Cannot sort a missing ListConfig",
        ),
        id="list:sort_from_missing",
    ),
    #     # iter
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.sort(),
            exception_type=ReadonlyConfigError,
            msg="Cannot sort a read-only ListConfig",
        ),
        id="list:readonly:sort",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: iter(cfg),
            exception_type=TypeError,
            msg="Cannot iterate a ListConfig object representing None",
        ),
        id="list:iter_none",
    ),
    param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: iter(cfg),
            exception_type=MissingMandatoryValue,
            msg="Cannot iterate a missing ListConfig",
        ),
        id="list:iter_missing",
    ),
    # delete
    param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.__delitem__(0),
            exception_type=ReadonlyConfigError,
            msg="Cannot delete item from read-only ListConfig",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg._get_node(0),
        ),
        id="list,readonly:del",
    ),
    # to_object
    param(
        Expected(
            create=lambda: OmegaConf.structured(User),
            op=lambda cfg: OmegaConf.to_object(cfg),
            exception_type=MissingMandatoryValue,
            msg="Structured config of type `User` has missing mandatory value: name",
            key="name",
            child_node=lambda cfg: cfg._get_node("name"),
        ),
        id="to_object:structured-missing-field",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(NestedInterpolationToMissing),
            op=lambda cfg: OmegaConf.to_object(cfg),
            exception_type=InterpolationToMissingValueError,
            msg=(
                "MissingMandatoryValue while resolving interpolation: "
                "Missing mandatory value: name"
            ),
            key="baz",
            full_key="subcfg.baz",
            object_type=NestedInterpolationToMissing.BazParams,
            parent_node=lambda cfg: cfg.subcfg,
            child_node=lambda cfg: cfg.subcfg._get_node("baz"),
            num_lines=3,
        ),
        id="to_object:structured,throw_on_missing_interpolation",
    ),
    param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredInterpolationKeyError),
            op=lambda cfg: OmegaConf.to_object(cfg),
            exception_type=InterpolationKeyError,
            key="name",
            msg=("Interpolation key 'bar' not found"),
            child_node=lambda cfg: cfg._get_node("name"),
        ),
        id="to_object:structured,throw_on_interpolation_key_error",
    ),
    # to_container throw_on_missing
    param(
        Expected(
            create=lambda: OmegaConf.create(
                {"subcfg": {"x": "${missing_val}"}, "missing_val": "???"}
            ),
            op=lambda cfg: OmegaConf.to_container(
                cfg, resolve=True, throw_on_missing=True
            ),
            exception_type=InterpolationToMissingValueError,
            msg=(
                "MissingMandatoryValue while resolving interpolation: "
                "Missing mandatory value: missing_val"
            ),
            key="x",
            full_key="subcfg.x",
            parent_node=lambda cfg: cfg.subcfg,
            child_node=lambda cfg: cfg.subcfg._get_node("x"),
        ),
        id="to_container:throw_on_missing_interpolation",
    ),
    param(
        Expected(
            create=lambda: DictConfig("???"),
            op=lambda cfg: OmegaConf.to_container(cfg, throw_on_missing=True),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value",
        ),
        id="to_container:throw_on_missing,dict",
    ),
    param(
        Expected(
            create=lambda: ListConfig("???"),
            op=lambda cfg: OmegaConf.to_container(cfg, throw_on_missing=True),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value",
        ),
        id="to_container:throw_on_missing,list",
    ),
    param(
        Expected(
            create=lambda: DictConfig({"a": "???"}),
            op=lambda cfg: OmegaConf.to_container(cfg, throw_on_missing=True),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value: a",
            key="a",
            child_node=lambda cfg: cfg._get_node("a"),
        ),
        id="to_container:throw_on_missing,dict_value",
    ),
    param(
        Expected(
            create=lambda: ListConfig(["???"]),
            op=lambda cfg: OmegaConf.to_container(cfg, throw_on_missing=True),
            exception_type=MissingMandatoryValue,
            msg="Missing mandatory value: 0",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg._get_node(0),
        ),
        id="to_container:throw_on_missing,list_item",
    ),
]


def create_struct(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_struct(cfg, True)
    return cfg


def create_readonly(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_readonly(cfg, True)
    return cfg


@mark.parametrize("expected", params)
def test_errors(expected: Expected, monkeypatch: Any) -> None:
    monkeypatch.setenv("OC_CAUSE", "0")
    cfg = expected.create()
    expected.finalize(cfg)
    if expected.msg_is_regex:
        match = expected.msg
    else:
        match = re.escape(expected.msg)

    with raises(expected.exception_type, match=match) as einfo:
        try:
            expected.op(cfg)
        except Exception as e:
            # helps in debugging
            raise e
    ex = einfo.value
    assert isinstance(ex, OmegaConfBaseException)

    assert ex.object_type == expected.object_type
    assert ex.key == expected.key
    if not expected.low_level:
        assert ex.parent_node == expected.parent_node(cfg)
        assert ex.child_node == expected.child_node(cfg)
        assert ex.full_key == expected.full_key
        assert isinstance(expected.full_key, str)

        if expected.ref_type is not None:
            assert ex.ref_type == expected.ref_type

        if expected.ref_type is not None:
            assert ex.ref_type_str == expected.ref_type_str

        if expected.object_type is not None:
            assert ex.object_type_str == expected.object_type_str

        if isinstance(ex, OmegaConfBaseException):
            assert str(ex).count("\n") == expected.num_lines

        with monkeypatch.context() as m:
            m.setenv("OC_CAUSE", "1")
            try:
                expected.op(cfg)
            except Exception as e:
                assert e.__cause__ is not None

        with monkeypatch.context() as m:
            m.setenv("OC_CAUSE", "0")
            try:
                expected.op(cfg)
            except Exception as e:
                assert e.__cause__ is None


def test_assertion_error() -> None:
    """Test the case where an `AssertionError` is processed in `format_and_raise()`"""
    try:
        assert False
    except AssertionError as exc:
        try:
            format_and_raise(node=None, key=None, value=None, msg=str(exc), cause=exc)
        except AssertionError as exc2:
            assert exc2 is exc  # we expect the original exception to be raised
        else:
            assert False


@mark.parametrize(
    "register_func",
    [OmegaConf.legacy_register_resolver, OmegaConf.register_new_resolver],
)
def test_resolver_error(restore_resolvers: Any, register_func: Any) -> None:
    def div(x: Any, y: Any) -> float:
        return float(x) / float(y)

    register_func("div", div)
    c = OmegaConf.create({"div_by_zero": "${div:1,0}"})
    expected_msg = dedent(
        """\
        ZeroDivisionError raised while resolving interpolation: float division( by zero)?
            full_key: div_by_zero
            object_type=dict"""
    )
    with raises(InterpolationResolutionError, match=expected_msg):
        c.div_by_zero


@mark.parametrize(
    ["create_func", "arg"],
    [
        (OmegaConf.create, {"a": "${b"}),
        (DictConfig, "${b"),
        (ListConfig, "${b"),
    ],
)
def test_parse_error_on_creation(create_func: Any, arg: Any) -> None:
    with raises(
        GrammarParseError, match=re.escape("no viable alternative at input '${b'")
    ):
        create_func(arg)


@mark.parametrize(
    ["create_func", "obj"],
    [
        param(DictConfig, {"zz": 10}, id="dict"),
        param(DictConfig, {}, id="dict_empty"),
        param(DictConfig, User, id="structured"),
        param(ListConfig, ["zz"], id="list"),
        param(ListConfig, [], id="list_empty"),
        param(OmegaConf.create, {"zz": 10}, id="create"),
    ],
)
def test_parent_type_error_on_creation(create_func: Any, obj: Any) -> None:
    with raises(ConfigTypeError, match=re.escape("Parent type is not omegaconf.Box")):
        create_func(obj, parent={"a"})  # bad parent


def test_union_must_not_be_parent_of_union() -> None:
    bad_parent = UnionNode(123, Union[int, str])
    with raises(
        ConfigTypeError, match=re.escape("Parent type is not omegaconf.Container")
    ):
        UnionNode(456, Union[int, str], parent=bad_parent)

    good_parent = DictConfig({})
    UnionNode(456, Union[int, str], parent=good_parent)  # ok


def test_cycle_when_iterating_over_parents() -> None:
    c = OmegaConf.create({"x": {}})
    x_node = c._get_node("x")
    assert isinstance(x_node, DictConfig)
    c._set_parent(x_node)
    with raises(
        OmegaConfBaseException,
        match=re.escape("Cycle when iterating over parents of key `x`"),
    ):
        c._get_full_key("x")


def test_get_full_key_failure_in_format_and_raise() -> None:
    c = OmegaConf.create({"x": {}})
    x_node = c._get_node("x")
    assert isinstance(x_node, DictConfig)
    # We create a cycle in the parent relationship that will trigger a RecursionError
    # when trying to access `c.x`. This test verifies that this RecursionError is properly
    # raised even if another exception occurs in `format_and_raise()` when trying to
    # obtain the full key.
    c._set_parent(x_node)

    # The exception message may vary depending on the Python version and seemingly
    # irrelevant code changes. As a result, we only test the "full_key" part of the
    # message (which we have control on).
    match = re.escape(
        "full_key: <unresolvable due to ConfigCycleDetectedException: "
        "Cycle when iterating over parents of key `x`>"
    )

    with raises(RecursionError, match=match):
        c.x


def test_dict_subclass_error() -> None:
    """
    Test calling OmegaConf.structured(malformed_dict_subclass).
    We expect a ValueError and a UserWarning (deprecation) to be raised simultaneously.
    We are using a separate function instead of adding
    warning support to the giant `test_errors` function above,
    """
    src = Str2Int()
    src["bar"] = "qux"  # type: ignore
    with raises(
        ValidationError,
        match=re.escape("Value 'qux' of type 'str' could not be converted to Integer"),
    ) as einfo:
        with warns_dict_subclass_deprecated(Str2Int):
            OmegaConf.structured(src)
    ex = einfo.value
    assert isinstance(ex, OmegaConfBaseException)

    assert ex.key == "bar"
    assert ex.full_key == "bar"
    assert ex.ref_type is None
    assert ex.object_type is None
    assert ex.parent_node is None
    assert ex.child_node is None
