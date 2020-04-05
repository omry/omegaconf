import re
from dataclasses import dataclass
from typing import Any, Dict, List

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
from omegaconf.errors import KeyValidationError, MissingMandatoryValue

from . import Color, ConcretePlugin, IllegalType, Plugin, StructuredWithMissing


@dataclass
class NonOptionalAssignedNone:
    foo: int = None  # type:ignore


def create_readonly(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_readonly(cfg, True)
    return cfg


params = [
    ##############
    # DictConfig #
    ##############
    # update
    pytest.param(
        lambda: OmegaConf.structured(StructuredWithMissing),
        lambda cfg: OmegaConf.update(cfg, "num", "hello"),
        ValidationError,
        "Value 'hello' could not be converted to Integer",
        id="structured:update_with_invalid_value",
    ),
    pytest.param(
        lambda: OmegaConf.structured(StructuredWithMissing),
        lambda cfg: OmegaConf.update(cfg, "num", None),
        ValidationError,
        "field 'num' is not Optional",
        id="structured:update:none_to_non_optional",
    ),
    pytest.param(
        lambda: OmegaConf.create({}),
        lambda cfg: OmegaConf.update(cfg, "a", IllegalType()),
        UnsupportedValueType,
        "Value 'IllegalType' is not a supported primitive type",
        id="dict:update:object_of_illegal_type",
    ),
    # pop
    pytest.param(
        lambda: create_readonly({"foo": "bar"}),
        lambda cfg: cfg.pop("foo"),
        ReadonlyConfigError,
        "Cannot pop from read-only node",
        id="dict,readonly:pop",
    ),
    pytest.param(
        lambda: OmegaConf.create({"foo": "bar"}),
        lambda cfg: cfg.pop("nevermind"),
        KeyError,
        "Key not found: 'nevermind'",
        id="dict:pop_invalid",
    ),
    pytest.param(
        lambda: OmegaConf.create({"foo": {}}),
        lambda cfg: cfg.foo.pop("nevermind"),
        KeyError,
        "Key not found: 'nevermind' (path: 'foo.nevermind')",
        id="dict:pop_invalid",
    ),
    pytest.param(
        lambda: OmegaConf.structured(ConcretePlugin),
        lambda cfg: getattr(cfg, "fail"),
        AttributeError,
        "Key 'fail' not in 'ConcretePlugin'",
        id="structured:access_invalid_attribute",
    ),
    # getattr
    pytest.param(
        lambda: create_struct({"foo": "bar"}),
        lambda cfg: getattr(cfg, "fail"),
        AttributeError,
        "Key 'fail' in not in struct",
        id="dict,struct:access_invalid_attribute",
    ),
    # setattr
    pytest.param(
        lambda: create_struct({"foo": "bar"}),
        lambda cfg: setattr(cfg, "zlonk", "zlank"),
        AttributeError,
        "Key 'zlonk' in not in struct",
        id="dict,struct:set_invalid_attribute",
    ),
    pytest.param(
        lambda: OmegaConf.structured(ConcretePlugin),
        lambda cfg: setattr(cfg, "params", 10),
        ValidationError,
        "Invalid type assigned : int is not a subclass of FoobarParams. value: 10",
        id="structured:setattr,invalid_type",
    ),
    pytest.param(
        lambda: create_readonly({"foo": "bar"}),
        lambda cfg: setattr(cfg, "foo", 20),
        ReadonlyConfigError,
        "Cannot assign to read-only node : 20",
        id="dict,readonly:set_attribute",
    ),
    pytest.param(
        lambda: OmegaConf.create({"foo": DictConfig(is_optional=False, content={})}),
        lambda cfg: setattr(cfg, "foo", None),
        ValidationError,
        "field 'foo' is not Optional",
        id="dict,none_optional:set_none",
    ),
    # setitem
    pytest.param(
        lambda: create_struct({"foo": "bar"}),
        lambda cfg: cfg.__setitem__("zoo", "zonk"),
        KeyError,
        "Error setting zoo=zonk : Key 'zoo' in not in struct",
        id="dict,struct:setitem_on_none_existing_key",
    ),
    # getitem
    pytest.param(
        lambda: create_struct({"foo": "bar"}),
        lambda cfg: cfg.__getitem__("zoo"),
        KeyError,
        "Error getting 'zoo' : Key 'zoo' in not in struct",
        id="dict,struct:getitem_key_not_in_struct",
    ),
    pytest.param(
        lambda: DictConfig(ref_type=Dict[Color, str], content={}),
        lambda cfg: cfg.__getitem__("foo"),
        KeyValidationError,
        "Key 'foo' is incompatible with (Color)",
        id="dict,reftype=Dict[Color,str]:,getitem_str_key",
    ),
    pytest.param(
        lambda: DictConfig(ref_type=Dict[str, str], content={}),
        lambda cfg: cfg.__getitem__(Color.RED),
        KeyValidationError,
        "Key Color.RED (Color) is incompatible with (str)",
        id="dict,reftype=Dict[str,str]:,getitem_color_key",
    ),
    # merge
    pytest.param(
        lambda: create_readonly({"foo": "bar"}),
        lambda cfg: cfg.merge_with(OmegaConf.create()),
        ReadonlyConfigError,
        "Cannot merge into read-only node",
        id="dict,readonly:merge_with",
    ),
    # merge_with
    pytest.param(
        lambda: OmegaConf.structured(ConcretePlugin),
        lambda cfg: cfg.merge_with(Plugin),
        ValidationError,
        "Plugin is not a subclass of ConcretePlugin. value: {'name': '???', 'params': '???'}",
        id="structured:merge_invalid_dataclass",
    ),
    # get
    pytest.param(
        lambda: OmegaConf.create(),
        lambda cfg: cfg.get(IllegalType),
        KeyValidationError,
        "Incompatible key type 'type'",
        id="dict:get_illegal_type",
    ),
    pytest.param(
        lambda: OmegaConf.create(),
        lambda cfg: cfg.get(IllegalType()),
        KeyValidationError,
        "Incompatible key type 'IllegalType'",
        id="dict:get_object_of_illegal_type",
    ),
    # create
    pytest.param(
        lambda: None,
        lambda cfg: OmegaConf.structured(NonOptionalAssignedNone),
        ValidationError,
        "Non optional field cannot be assigned None",
        id="dict_create_none_optional_with_none",
    ),
    pytest.param(
        lambda: None,
        lambda cfg: OmegaConf.structured(IllegalType),
        ValidationError,
        "Input class 'IllegalType' is not a structured config. did you forget to decorate it as a dataclass?",
        id="dict_create_from_illegal_type",
    ),
    pytest.param(
        lambda: None,
        lambda cfg: OmegaConf.structured(IllegalType()),
        ValidationError,
        "Object of unsupported type: 'IllegalType'",
        id="structured:create_from_unsupported_object",
    ),
    # assign
    pytest.param(
        lambda: DictConfig(ref_type=ConcretePlugin, content="???"),
        lambda cfg: cfg._set_value(1),
        ValidationError,
        "Invalid type assigned : int is not a subclass of ConcretePlugin. value: 1",
        id="dict:set_value:reftype_mismatch",
    ),
    pytest.param(
        lambda: DictConfig(ref_type=Dict[str, int], content={"foo": 10, "bar": 20}),
        lambda cfg: cfg.__setitem__("baz", "fail"),
        ValidationError,
        "Value 'fail' could not be converted to Integer",
        id="dict,int_element_type:assigned_str_value",
    ),
    # delete
    pytest.param(
        lambda: create_readonly({"foo": "bar"}),
        lambda cfg: cfg.__delitem__("foo"),
        ReadonlyConfigError,
        "Cannot delete item from read-only DictConfig",
        id="dict,readonly:del",
    ),
    ##############
    # ListConfig #
    ##############
    # get node
    pytest.param(
        lambda: OmegaConf.create([1, 2, 3]),
        lambda cfg: cfg.get_node_ex("foo"),
        TypeError,
        "list indices must be integers or slices, not str",
        id="list:get_nox_ex:invalid_index_type",
    ),
    pytest.param(
        lambda: OmegaConf.create([1, 2, 3]),
        lambda cfg: cfg.get_node_ex(20),
        IndexError,
        "list index out of range",
        id="list:get_node_ex:index_out_of_range",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.get_node_ex(20),
        TypeError,
        "Cannot get_node from a ListConfig object representing None",
        id="list:get_node_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: cfg.get_node_ex(20),
        MissingMandatoryValue,
        "Cannot get_node from a missing ListConfig",
        id="list:get_node_missing",
    ),
    # create
    pytest.param(
        lambda: None,
        lambda cfg: ListConfig(is_optional=False, content=None),
        ValidationError,
        "Non optional ListConfig cannot be constructed from None",
        id="list:create_not_optional_with_none",
    ),
    # append
    pytest.param(
        lambda: OmegaConf.create([]),
        lambda cfg: cfg.append(IllegalType()),
        UnsupportedValueType,
        "Value 'IllegalType' is not a supported primitive type",
        id="list:append_value_of_illegal_type",
    ),
    # pop
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.pop(0),
        ReadonlyConfigError,
        "Cannot pop from read-only ListConfig",
        id="dict:readonly:pop",
    ),
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.pop("Invalid key type"),
        ReadonlyConfigError,
        "Cannot pop from read-only ListConfig",
        id="dict:readonly:pop",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.pop(0),
        TypeError,
        "Cannot pop from a ListConfig object representing None",
        id="list:pop_from_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: cfg.pop(0),
        MissingMandatoryValue,
        "Cannot pop from a missing ListConfig",
        id="list:pop_from_missing",
    ),
    # getitem
    pytest.param(
        lambda: OmegaConf.create(["???"]),
        lambda cfg: cfg.__getitem__(slice(0, 1)),
        MissingMandatoryValue,
        "Missing mandatory value: [slice(0, 1, None)]",
        id="list:subscript_slice_with_missing",
    ),
    pytest.param(
        lambda: OmegaConf.create([10, "???"]),
        lambda cfg: cfg.__getitem__(1),
        MissingMandatoryValue,
        "Missing mandatory value: [1]",
        id="list:subscript_index_with_missing",
    ),
    pytest.param(
        lambda: OmegaConf.create([1, 2, 3]),
        lambda cfg: cfg.__getitem__(20),
        IndexError,
        "list index out of range",
        id="list:subscript:index_out_of_range",
    ),
    pytest.param(
        lambda: OmegaConf.create([1, 2, 3]),
        lambda cfg: cfg.__getitem__("foo"),
        KeyValidationError,
        "Invalid key type 'str'",
        id="list:getitem,illegal_key_type",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.__getitem__(0),
        TypeError,
        "ListConfig object representing None is not subscriptable",
        id="list:getitem,illegal_key_type",
    ),
    # setitem
    pytest.param(
        lambda: OmegaConf.create([None]),
        lambda cfg: cfg.__setitem__(0, IllegalType()),
        UnsupportedValueType,
        "Value 'IllegalType' is not a supported primitive type",
        id="list:setitem,illegal_value_type",
    ),
    pytest.param(
        lambda: OmegaConf.create([1, 2, 3]),
        lambda cfg: cfg.__setitem__("foo", 4),
        KeyValidationError,
        "Invalid key type 'str'",
        id="list:setitem,illegal_key_type",
    ),
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.__setitem__(0, 4),
        ReadonlyConfigError,
        "ListConfig is read-only",
        id="list,readonly:setitem",
    ),
    # assign
    pytest.param(
        lambda: ListConfig(ref_type=List[int], content=[1, 2, 3]),
        lambda cfg: cfg.__setitem__(0, "foo"),
        ValidationError,
        "Value 'foo' could not be converted to Integer",
        id="list,int_elements:assigned_str_element",
    ),
    pytest.param(
        # make sure OmegaConf.create is not losing critical metadata.
        lambda: OmegaConf.create(ListConfig(ref_type=List[int], content=[1, 2, 3])),
        lambda cfg: cfg.__setitem__(0, "foo"),
        ValidationError,
        "Value 'foo' could not be converted to Integer",
        id="list,int_elements:assigned_str_element",
    ),
    pytest.param(
        lambda: OmegaConf.create([IntegerNode(is_optional=False, value=0), 2, 3]),
        lambda cfg: cfg.__setitem__(0, None),
        ValidationError,
        "[0] is not optional and cannot be assigned None",
        id="list,not_optional:assigned_none",
    ),
    # index
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.index(99),
        ValueError,
        "Item not found in ListConfig",
        id="list,readonly:index_not_found",
    ),
    # insert
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.insert(1, 99),
        ReadonlyConfigError,
        "Cannot insert into a read-only ListConfig",
        id="list,readonly:insert",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.insert(1, 99),
        TypeError,
        "Cannot insert into ListConfig object representing None",
        id="list:insert_into_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: cfg.insert(1, 99),
        MissingMandatoryValue,
        "Cannot insert into missing ListConfig",
        id="list:insert_into_missing",
    ),
    # get
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.get(0),
        TypeError,
        "Cannot get from a ListConfig object representing None",
        id="list:get_from_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: cfg.get(0),
        MissingMandatoryValue,
        "Cannot get from a missing ListConfig",
        id="list:get_from_missing",
    ),
    # sort
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.sort(),
        ReadonlyConfigError,
        "Cannot sort a read-only ListConfig",
        id="list:readonly:sort",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: cfg.sort(),
        TypeError,
        "Cannot sort a ListConfig object representing None",
        id="list:sort_from_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: cfg.sort(),
        MissingMandatoryValue,
        "Cannot sort a missing ListConfig",
        id="list:sort_from_missing",
    ),
    # iter
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.sort(),
        ReadonlyConfigError,
        "Cannot sort a read-only ListConfig",
        id="list:readonly:sort",
    ),
    pytest.param(
        lambda: ListConfig(content=None),
        lambda cfg: iter(cfg),
        TypeError,
        "Cannot iterate on ListConfig object representing None",
        id="list:iter_none",
    ),
    pytest.param(
        lambda: ListConfig(content="???"),
        lambda cfg: iter(cfg),
        MissingMandatoryValue,
        "Cannot iterate on a missing ListConfig",
        id="list:iter_missing",
    ),
    # delete
    pytest.param(
        lambda: create_readonly([1, 2, 3]),
        lambda cfg: cfg.__delitem__(0),
        ReadonlyConfigError,
        "Cannot delete item from read-only ListConfig",
        id="list,readonly:del",
    ),
]


@pytest.mark.parametrize(  # type:ignore
    "create, op, exception_type, msg", params
)
def test_errors(create: Any, op: Any, exception_type: Any, msg: str) -> None:
    cfg = create()
    with pytest.raises(exception_type, match=re.escape(msg)):
        try:
            op(cfg)
        except Exception as e:
            # helps in debugging
            raise e


def create_struct(cfg: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    OmegaConf.set_struct(cfg, True)
    return cfg
