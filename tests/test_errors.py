import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Type, Union

import pytest

from omegaconf import (
    DictConfig,
    IntegerNode,
    ListConfig,
    OmegaConf,
    ReadonlyConfigError,
    UnsupportedValueType,
    ValidationError,
)
from omegaconf.errors import (
    ConfigAttributeError,
    ConfigKeyError,
    ConfigTypeError,
    ConfigValueError,
    KeyValidationError,
    MissingMandatoryValue,
    OmegaConfBaseException,
)

from . import (
    A,
    Color,
    ConcretePlugin,
    IllegalType,
    Module,
    Package,
    Plugin,
    StructuredWithMissing,
    UnionError,
    User,
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
    num_lines: int = 3

    def finalize(self, cfg: Any) -> None:
        if self.object_type == "AUTO":
            self.object_type = OmegaConf.get_type(cfg)

        if self.full_key == "AUTO":
            if self.key is None:
                self.full_key = ""
            else:
                if isinstance(self.key, (str, int, Enum, slice)):
                    self.full_key = self.key
                else:
                    self.full_key = ""


params = [
    ##############
    # DictConfig #
    ##############
    # update
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredWithMissing),
            op=lambda cfg: OmegaConf.update(cfg, "num", "hello", merge=True),
            exception_type=ValidationError,
            msg="Value 'hello' could not be converted to Integer",
            parent_node=lambda cfg: cfg,
            child_node=lambda cfg: cfg._get_node("num"),
            object_type=StructuredWithMissing,
            ref_type=Optional[StructuredWithMissing],
            key="num",
        ),
        id="structured:update_with_invalid_value",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(StructuredWithMissing),
            op=lambda cfg: OmegaConf.update(cfg, "num", None, merge=True),
            exception_type=ValidationError,
            msg="child 'num' is not Optional",
            parent_node=lambda cfg: cfg,
            child_node=lambda cfg: cfg._get_node("num"),
            object_type=StructuredWithMissing,
            ref_type=Optional[StructuredWithMissing],
            key="num",
        ),
        id="structured:update:none_to_non_optional",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create({}),
            op=lambda cfg: OmegaConf.update(cfg, "a", IllegalType(), merge=True),
            key="a",
            exception_type=UnsupportedValueType,
            ref_type=Optional[Dict[Union[str, Enum], Any]],
            msg="Value 'IllegalType' is not a supported primitive type",
        ),
        id="dict:update:object_of_illegal_type",
    ),
    # pop
    pytest.param(
        Expected(
            create=lambda: create_readonly({"foo": "bar"}),
            op=lambda cfg: cfg.pop("foo"),
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
            exception_type=ReadonlyConfigError,
            ref_type=Optional[Dict[Union[str, Enum], Any]],
            msg="Cannot pop from read-only node",
        ),
        id="dict,readonly:pop",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "bar"}),
            op=lambda cfg: cfg.pop("nevermind"),
            key="nevermind",
            exception_type=ConfigKeyError,
            msg="Key not found: 'nevermind'",
        ),
        id="dict:pop_invalid",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create({"foo": {}}),
            op=lambda cfg: cfg.foo.pop("nevermind"),
            key="nevermind",
            full_key="foo.nevermind",
            parent_node=lambda cfg: cfg.foo,
            exception_type=ConfigKeyError,
            msg="Key not found: 'nevermind' (path: 'foo.nevermind')",
        ),
        id="dict:pop_invalid_nested",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: getattr(cfg, "fail"),
            exception_type=ConfigAttributeError,
            msg="Key 'fail' not in 'ConcretePlugin'",
            key="fail",
            object_type=ConcretePlugin,
            ref_type=Optional[ConcretePlugin],
        ),
        id="structured:access_invalid_attribute",
    ),
    # getattr
    pytest.param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: getattr(cfg, "fail"),
            exception_type=ConfigAttributeError,
            msg="Key 'fail' is not in struct",
            key="fail",
        ),
        id="dict,struct:access_invalid_attribute",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "${missing}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=ConfigKeyError,
            msg="str interpolation key 'missing' not found",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_interpolation",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create({"foo": "foo_${missing}"}),
            op=lambda cfg: getattr(cfg, "foo"),
            exception_type=ConfigKeyError,
            msg="str interpolation key 'missing' not found",
            key="foo",
            child_node=lambda cfg: cfg._get_node("foo"),
        ),
        id="dict,accessing_missing_str_interpolation",
    ),
    # setattr
    pytest.param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: setattr(cfg, "zlonk", "zlank"),
            exception_type=ConfigAttributeError,
            msg="Key 'zlonk' is not in struct",
            key="zlonk",
        ),
        id="dict,struct:set_invalid_attribute",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: setattr(cfg, "params", 20),
            exception_type=ValidationError,
            msg="Invalid type assigned : int is not a subclass of FoobarParams. value: 20",
            key="params",
            object_type=ConcretePlugin,
            ref_type=Optional[ConcretePlugin],
            child_node=lambda cfg: cfg.params,
        ),
        id="structured:setattr,invalid_type_assigned_to_structured",
    ),
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create(
                {"foo": DictConfig(is_optional=False, content={})}
            ),
            op=lambda cfg: setattr(cfg, "foo", None),
            exception_type=ValidationError,
            msg="child 'foo' is not Optional",
            key="foo",
            full_key="foo",
            child_node=lambda cfg: cfg.foo,
        ),
        id="dict:setattr:not_optional:set_none",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: cfg.params.__setattr__("foo", "bar"),
            exception_type=ValidationError,
            msg="Value 'bar' could not be converted to Integer",
            key="foo",
            full_key="params.foo",
            object_type=ConcretePlugin.FoobarParams,
            child_node=lambda cfg: cfg.params.foo,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:setattr,invalid_type_assigned_to_field",
    ),
    # setitem
    pytest.param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.__setitem__("zoo", "zonk"),
            exception_type=KeyError,
            msg="Key 'zoo' is not in struct",
            key="zoo",
        ),
        id="dict,struct:setitem_on_none_existing_key",
    ),
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(User),
            op=lambda cfg: cfg.__setitem__("name", [1, 2]),
            exception_type=ValidationError,
            msg="Cannot convert 'list' to string : '[1, 2]'",
            full_key="name",
            key="name",
            low_level=True,
        ),
        id="DictConfig[Any,Any]:setitem_stringnode_bad_value",
    ),
    # getitem
    pytest.param(
        Expected(
            create=lambda: create_struct({"foo": "bar"}),
            op=lambda cfg: cfg.__getitem__("zoo"),
            exception_type=KeyError,
            msg="Key 'zoo' is not in struct",
            key="zoo",
        ),
        id="dict,struct:getitem_key_not_in_struct",
    ),
    pytest.param(
        Expected(
            create=lambda: DictConfig(key_type=Color, element_type=str, content={}),
            op=lambda cfg: cfg.__getitem__("foo"),
            exception_type=KeyValidationError,
            msg="Key 'foo' is incompatible with the enum type 'Color', valid: [RED, GREEN, BLUE]",
            key="foo",
            num_lines=3,
        ),
        id="DictConfig[Color,str]:getitem_str_key",
    ),
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: create_readonly({"foo1": "bar"}),
            op=lambda cfg: cfg.merge_with({"foo2": "bar"}),
            exception_type=ReadonlyConfigError,
            key="foo2",
            msg="Cannot change read-only config container",
        ),
        id="dict,readonly:merge_with",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: OmegaConf.merge(cfg, {"params": {"foo": "bar"}}),
            exception_type=ValidationError,
            msg="Value 'bar' could not be converted to Integer",
            key="foo",
            full_key="params.foo",
            object_type=ConcretePlugin.FoobarParams,
            child_node=lambda cfg: cfg.params.foo,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:merge,invalid_field_type",
    ),
    pytest.param(
        Expected(
            create=lambda: OmegaConf.structured(ConcretePlugin),
            op=lambda cfg: OmegaConf.merge(cfg, {"params": {"zlonk": 10}}),
            exception_type=ConfigKeyError,
            msg="Key 'zlonk' not in 'FoobarParams'",
            key="zlonk",
            full_key="params.zlonk",
            object_type=ConcretePlugin.FoobarParams,
            parent_node=lambda cfg: cfg.params,
        ),
        id="structured:merge,adding_an_invalid_key",
    ),
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create(),
            op=lambda cfg: cfg.get(IllegalType()),
            exception_type=KeyValidationError,
            msg="Incompatible key type 'IllegalType'",
            key=IllegalType(),
        ),
        id="dict:get_object_of_illegal_type",
    ),
    # dict:create
    pytest.param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(NotOptionalInt),
            exception_type=ValidationError,
            msg="Non optional field cannot be assigned None",
            object_type_str=None,
            ref_type_str=None,
        ),
        id="dict:create_none_optional_with_none",
    ),
    pytest.param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(NotOptionalInt),
            exception_type=ValidationError,
            object_type=None,
            msg="Non optional field cannot be assigned None",
            object_type_str="NotOptionalInt",
            ref_type_str=None,
        ),
        id="dict:create:not_optional_int_field_with_none",
    ),
    pytest.param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(NotOptionalA),
            exception_type=ValidationError,
            object_type=None,
            key=None,
            full_key="x",
            msg="field 'x' is not Optional",
            object_type_str="NotOptionalInt",
            ref_type_str=None,
        ),
        id="dict:create:not_optional_A_field_with_none",
    ),
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: None,
            op=lambda cfg: OmegaConf.structured(UnionError),
            exception_type=ValueError,
            msg="Union types are not supported:\nx: Union[int, str]",
            object_type_str=None,
            ref_type_str=None,
            num_lines=4,
        ),
        id="structured:create_with_union_error",
    ),
    # assign
    pytest.param(
        Expected(
            create=lambda: DictConfig(ref_type=ConcretePlugin, content="???"),
            op=lambda cfg: cfg._set_value(1),
            exception_type=ValidationError,
            msg="Invalid type assigned : int is not a subclass of ConcretePlugin. value: 1",
            low_level=True,
            ref_type=Optional[ConcretePlugin],
        ),
        id="dict:set_value:reftype_mismatch",
    ),
    pytest.param(
        Expected(
            create=lambda: DictConfig(
                key_type=str, element_type=int, content={"foo": 10, "bar": 20}
            ),
            op=lambda cfg: cfg.__setitem__("baz", "fail"),
            exception_type=ValidationError,
            msg="Value 'fail' could not be converted to Integer",
            key="baz",
            ref_type=Optional[Dict[str, int]],
        ),
        id="DictConfig[str,int]:assigned_str_value",
    ),
    # delete
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    ##############
    # ListConfig #
    ##############
    # getattr
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: OmegaConf.create([1, 2, 3]),
            op=lambda cfg: cfg._get_node("foo"),
            exception_type=KeyValidationError,
            key="foo",
            full_key="[foo]",
            msg="ListConfig indices must be integers or slices, not str",
            ref_type=Optional[List[Any]],
        ),
        id="list:get_nox_ex:invalid_index_type",
    ),
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg._get_node(20),
            exception_type=TypeError,
            msg="Cannot get_node from a ListConfig object representing None",
            key=20,
            full_key="[20]",
            ref_type=Optional[List[Any]],
        ),
        id="list:get_node_none",
    ),
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: ListConfig(is_optional=False, element_type=int, content=[]),
            op=lambda cfg: cfg._set_value(None),
            exception_type=ValidationError,
            object_type=None,
            msg="Non optional ListConfig cannot be constructed from None",
            ref_type=List[int],
            low_level=True,
        ),
        id="list:create_not_optional:_set_value(None)",
    ),
    pytest.param(
        Expected(
            create=lambda: ListConfig(content=[1, 2]),
            op=lambda cfg: cfg._set_value(True),
            exception_type=ValidationError,
            object_type=None,
            msg="Invalid value assigned : bool is not a subclass of ListConfig or list",
            ref_type=List[int],
            low_level=True,
        ),
        id="list:create_not_optional:_set_value(True)",
    ),
    # assign
    pytest.param(
        Expected(
            create=lambda: ListConfig(element_type=int, content=[1, 2, 3]),
            op=lambda cfg: cfg.__setitem__(0, "foo"),
            exception_type=ValidationError,
            msg="Value 'foo' could not be converted to Integer",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
            ref_type=Optional[List[int]],
        ),
        id="list,int_elements:assigned_str_element",
    ),
    pytest.param(
        Expected(
            # make sure OmegaConf.create is not losing critical metadata.
            create=lambda: OmegaConf.create(
                ListConfig(element_type=int, content=[1, 2, 3])
            ),
            op=lambda cfg: cfg.__setitem__(0, "foo"),
            exception_type=ValidationError,
            msg="Value 'foo' could not be converted to Integer",
            key=0,
            full_key="[0]",
            child_node=lambda cfg: cfg[0],
            ref_type=Optional[List[int]],
        ),
        id="list,int_elements:assigned_str_element",
    ),
    pytest.param(
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
            ref_type=Optional[List[Any]],
        ),
        id="list,not_optional:null_assignment",
    ),
    # index
    pytest.param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.index(99),
            exception_type=ConfigValueError,
            msg="Item not found in ListConfig",
        ),
        id="list,readonly:index_not_found",
    ),
    # insert
    pytest.param(
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
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.insert(1, 99),
            exception_type=MissingMandatoryValue,
            msg="Cannot insert into missing ListConfig",
            key=1,
            full_key="[1]",
            child_node=lambda _cfg: None,
            ref_type=Optional[List[Any]],
        ),
        id="list:insert_into_missing",
    ),
    # get
    pytest.param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.get(0),
            exception_type=TypeError,
            msg="Cannot get from a ListConfig object representing None",
            key=0,
            full_key="[0]",
            ref_type=Optional[List[Any]],
        ),
        id="list:get_from_none",
    ),
    pytest.param(
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
    pytest.param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.sort(),
            exception_type=ReadonlyConfigError,
            msg="Cannot sort a read-only ListConfig",
        ),
        id="list:readonly:sort",
    ),
    pytest.param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: cfg.sort(),
            exception_type=TypeError,
            msg="Cannot sort a ListConfig object representing None",
        ),
        id="list:sort_from_none",
    ),
    pytest.param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: cfg.sort(),
            exception_type=MissingMandatoryValue,
            msg="Cannot sort a missing ListConfig",
        ),
        id="list:sort_from_missing",
    ),
    #     # iter
    pytest.param(
        Expected(
            create=lambda: create_readonly([1, 2, 3]),
            op=lambda cfg: cfg.sort(),
            exception_type=ReadonlyConfigError,
            msg="Cannot sort a read-only ListConfig",
        ),
        id="list:readonly:sort",
    ),
    pytest.param(
        Expected(
            create=lambda: ListConfig(content=None),
            op=lambda cfg: iter(cfg),
            exception_type=TypeError,
            msg="Cannot iterate a ListConfig object representing None",
        ),
        id="list:iter_none",
    ),
    pytest.param(
        Expected(
            create=lambda: ListConfig(content="???"),
            op=lambda cfg: iter(cfg),
            exception_type=MissingMandatoryValue,
            msg="Cannot iterate a missing ListConfig",
        ),
        id="list:iter_missing",
    ),
    # delete
    pytest.param(
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
]


def create_struct(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_struct(cfg, True)
    return cfg


def create_readonly(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_readonly(cfg, True)
    return cfg


@pytest.mark.parametrize(  # type:ignore
    "expected", params
)
def test_errors(expected: Expected, monkeypatch: Any) -> None:
    monkeypatch.setenv("OC_CAUSE", "0")
    cfg = expected.create()
    expected.finalize(cfg)
    msg = expected.msg
    with pytest.raises(expected.exception_type, match=re.escape(msg)) as einfo:
        try:
            expected.op(cfg)
        except Exception as e:
            # helps in debugging
            raise e
    ex = einfo.value

    assert ex.object_type == expected.object_type
    assert ex.key == expected.key
    if not expected.low_level:
        if isinstance(ex, OmegaConfBaseException):
            assert str(ex).count("\n") == expected.num_lines
        assert ex.parent_node == expected.parent_node(cfg)
        assert ex.child_node == expected.child_node(cfg)
        assert ex.full_key == expected.full_key
        assert isinstance(expected.full_key, str)

        if expected.ref_type is not None:
            assert ex.ref_type == expected.ref_type

        if expected.object_type is not None:
            assert ex.object_type == expected.object_type

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
