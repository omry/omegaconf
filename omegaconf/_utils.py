from enum import Enum

import re
import yaml
from typing import Any, Dict, List

from .errors import ValidationError
from .node import Node
from .nodes import (
    ValueNode,
    StringNode,
    IntegerNode,
    BooleanNode,
    FloatNode,
    AnyNode,
    EnumNode,
)

try:
    import dataclasses
except ImportError:
    dataclasses = None

try:
    import attr
except ImportError:
    attr = None


def isint(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_yaml_loader():
    loader = yaml.SafeLoader
    loader.add_implicit_resolver(
        "tag:yaml.org,2002:float",
        re.compile(
            """^(?:
         [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
        |\\.[0-9_]+(?:[eE][-+][0-9]+)?
        |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
        |[-+]?\\.(?:inf|Inf|INF)
        |\\.(?:nan|NaN|NAN))$""",
            re.X,
        ),
        list("-+0123456789."),
    )
    loader.yaml_implicit_resolvers = {
        key: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:timestamp"
        ]
        for key, resolvers in loader.yaml_implicit_resolvers.items()
    }
    return loader


def _is_primitive_type(type_):
    if not isinstance(type_, type):
        type_ = type(type_)

    return issubclass(type_, Enum) or type_ in (int, float, bool, str, type(None))


def _valid_value_annotation_type(type_):
    return type_ is Any or _is_primitive_type(type_) or is_structured_config(type_)


def _valid_input_value_type(value):
    if isinstance(value, Enum) or (isinstance(value, type) and issubclass(value, Enum)):
        return True
    return type(value) in (int, float, bool, str, dict, list, tuple, type(None))


def _node_wrap(type_, parent, is_optional, value):
    if type_ == Any:
        node = AnyNode(value=value, parent=parent, is_optional=is_optional)
    elif issubclass(type_, Enum):
        node = EnumNode(enum_type=type_, parent=parent, is_optional=is_optional)
        node.set_value(value)
    elif type_ == int:
        node = IntegerNode(value=value, parent=parent, is_optional=is_optional)
    elif type_ == float:
        node = FloatNode(value=value, parent=parent, is_optional=is_optional)
    elif type_ == bool:
        node = BooleanNode(value=value, parent=parent, is_optional=is_optional)
    elif type_ == str:
        node = StringNode(value=value, parent=parent, is_optional=is_optional)
    else:
        raise ValueError("Unexpected object type : {}".format(type_.__name__))
    return node


def _resolve_optional(type_):
    from typing import Union

    if getattr(type_, "__origin__", None) is Union:
        args = type_.__args__
        if len(args) == 2 and args[1] == type(None):  # noqa E721
            return True, args[0]
    return False, type_


def _maybe_wrap(annotated_type, value, is_optional, parent):
    if isinstance(value, ValueNode):
        return value

    from omegaconf import Config, OmegaConf

    if isinstance(value, Config):
        value = OmegaConf.to_container(value)

    origin = getattr(annotated_type, "__origin__", None)
    args = getattr(annotated_type, "__args__", None)
    is_dict = type(value) is dict or origin is dict
    is_list = type(value) in (list, tuple) or origin in (list, tuple)

    if is_dict or origin is dict:
        from .dictconfig import DictConfig

        if annotated_type is not Dict and args is not None:
            element_type = args[1]
        else:
            element_type = Any

        if not _valid_value_annotation_type(element_type) and not is_structured_config(
            element_type
        ):
            raise ValidationError(f"Unsupported value type : {element_type}")

        value = DictConfig(parent=None, content=value, element_type=element_type)
        # noinspection PyProtectedMember
        value._set_parent(parent=parent)
    elif is_list:
        from .listconfig import ListConfig

        if annotated_type is not List and args is not None:
            element_type = args[0]
        else:
            element_type = Any

        if not (_valid_value_annotation_type(element_type)):
            raise ValidationError(f"Unsupported value type : {element_type}")

        value = ListConfig(parent=None, content=value, element_type=element_type)
        # noinspection PyProtectedMember
        value._set_parent(parent=parent)

    elif (
        is_dict and is_structured_config(annotated_type) and is_structured_config(value)
    ) or is_structured_config(value):
        from . import DictConfig

        value = DictConfig(content=value, parent=parent)
    else:
        if is_structured_config(annotated_type) and not is_structured_config(value):
            raise ValidationError(
                f"Value type {type(value).__name__} does not match declared type {annotated_type}"
            )

        value = _node_wrap(
            type_=annotated_type, parent=parent, is_optional=is_optional, value=value
        )
    assert isinstance(value, Node)
    return value


def get_attr_data(obj):
    d = {}
    is_type = isinstance(obj, type)
    obj_type = obj if is_type else type(obj)
    for name, attrib in attr.fields_dict(obj_type).items():
        is_optional, type_ = _resolve_optional(attrib.type)
        is_nested = is_attr_class(type_)
        if not is_type:
            value = getattr(obj, name)
        else:
            value = attrib.default
            if value == attr.NOTHING:
                if is_nested:
                    value = type_
                else:
                    if is_optional:
                        value = None
                    else:
                        raise ValueError(
                            "Missing default value for {}, to indicate "
                            "default must be populated later use '???'".format(name)
                        )
        if is_nested and value in (None, "???"):
            raise ValueError("Nested value {} must not be None or ???".format(name))

        d[name] = _maybe_wrap(
            annotated_type=type_, is_optional=is_optional, value=value, parent=None
        )
    return d


def get_dataclass_data(obj):
    d = {}
    for field in dataclasses.fields(obj):
        name = field.name
        is_optional, type_ = _resolve_optional(field.type)
        is_nested = is_structured_config(type_)
        if hasattr(obj, name):
            value = getattr(obj, name)
        else:
            if field.default_factory != dataclasses.MISSING:
                value = field.default_factory()
            else:
                if is_nested:
                    value = type_
                else:
                    if is_optional:
                        value = None
                    else:
                        raise ValueError(
                            "Missing default value for {}, to indicate "
                            "default must be populated later use '???'".format(name)
                        )
        if is_nested and value in (None, "???"):
            raise ValueError("Nested value {} must not be None or ???".format(name))

        d[name] = _maybe_wrap(
            annotated_type=type_, is_optional=is_optional, value=value, parent=None
        )
    return d


def is_dataclass(obj):
    from omegaconf.node import Node

    if dataclasses is None or isinstance(obj, Node):
        return False
    return dataclasses.is_dataclass(obj)


def is_attr_class(obj):
    from omegaconf.node import Node

    if attr is None or isinstance(obj, Node):
        return False
    return attr.has(obj)


def is_structured_config(obj):
    return is_attr_class(obj) or is_dataclass(obj)


def is_dataclass_frozen(type_):
    return type_.__dataclass_params__.frozen


def is_attr_frozen(type_):
    # This is very hacky and probably fragile as well.
    # Unfortunately currently there isn't an official API in attr that can detect that.
    # noinspection PyProtectedMember
    return type_.__setattr__ == attr._make._frozen_setattrs


def is_structured_config_frozen(obj):
    type_ = obj
    if not isinstance(type_, type):
        type_ = type(obj)

    if is_dataclass(type_):
        return is_dataclass_frozen(type_)
    if is_attr_class(type_):
        return is_attr_frozen(type_)
    raise ValueError("Unexpected object type")


def get_structured_config_data(obj):
    if is_dataclass(obj):
        return get_dataclass_data(obj)
    if is_attr_class(obj):
        return get_attr_data(obj)
    raise ValueError(f"Unsupported type f{type(obj).__name__}")


class ValueKind(Enum):
    VALUE = 0
    MANDATORY_MISSING = 1
    INTERPOLATION = 2
    STR_INTERPOLATION = 3


def get_value_kind(value, return_match_list=False):
    """
    Determine the kind of a value
    Examples:
    MANDATORY_MISSING : "???
    VALUE : "10", "20", True,
    INTERPOLATION: "${foo}", "${foo.bar}"
    STR_INTERPOLATION: "ftp://${host}/path"

    :param value: input string to classify
    :param return_match_list: True to return the match list as well
    :return: ValueKind
    """
    if not isinstance(value, str):
        return ValueKind.VALUE

    key_prefix = r"\${(\w+:)?"
    legal_characters = r"([\w\.%_ \\,-]*?)}"
    match_list = None

    def ret(value_kind):
        if return_match_list:
            return value_kind, match_list
        else:
            return value_kind

    if value == "???":
        return ret(ValueKind.MANDATORY_MISSING)

    match_list = list(re.finditer(key_prefix + legal_characters, value))
    if len(match_list) == 0:
        return ret(ValueKind.VALUE)

    if len(match_list) == 1 and value == match_list[0].group(0):
        return ret(ValueKind.INTERPOLATION)
    else:
        return ret(ValueKind.STR_INTERPOLATION)


def decode_primitive(s):
    def is_bool(st):
        st = str.lower(st)
        return st == "true" or st == "false"

    def is_float(st):
        try:
            float(st)
            return True
        except ValueError:
            return False

    def is_int(st):
        try:
            int(st)
            return True
        except ValueError:
            return False

    if is_bool(s):
        return str.lower(s) == "true"

    if is_int(s):
        return int(s)

    if is_float(s):
        return float(s)

    return s


# noinspection PyProtectedMember
def _re_parent(node):
    from .listconfig import ListConfig
    from .dictconfig import DictConfig
    from .node import Node

    # update parents of first level Config nodes to self
    assert isinstance(node, Node)
    if isinstance(node, DictConfig):
        for _key, value in node.__dict__["content"].items():
            value._set_parent(node)
            _re_parent(value)
    elif isinstance(node, ListConfig):
        for item in node.__dict__["content"]:
            item._set_parent(node)
            _re_parent(item)


def _select_one(c, key_):
    from .listconfig import ListConfig
    from .dictconfig import DictConfig

    assert isinstance(c, (DictConfig, ListConfig)), f"Unexpected type : {c}"

    if isinstance(c, DictConfig):
        if c.get_node(key_, validate_access=False) is not None:
            val = c[key_]
        else:
            val = None
    elif isinstance(c, ListConfig):
        if not isint(key_):
            raise TypeError("Index {} is not an int".format(key_))
        key_ = int(key_)
        if key_ < 0 or key_ + 1 > len(c):
            val = None
        else:
            val = c[key_]

    return val, key_
