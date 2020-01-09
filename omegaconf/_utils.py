import re
from enum import Enum
from typing import Any, Dict, List, Match, Optional, Tuple, Union

import yaml

from .base import Node

try:
    import dataclasses

except ImportError:  # pragma: no cover
    dataclasses = None  # type: ignore # pragma: no cover

try:
    import attr

except ImportError:  # pragma: no cover
    attr = None  # type: ignore # pragma: no cover


def isint(s: str) -> bool:
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_yaml_loader() -> Any:
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
    )  # type : ignore
    loader.yaml_implicit_resolvers = {
        key: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:timestamp"
        ]
        for key, resolvers in loader.yaml_implicit_resolvers.items()
    }
    return loader


def _resolve_optional(type_: Any) -> Tuple[bool, Any]:
    from typing import Union

    if getattr(type_, "__origin__", None) is Union:
        args = type_.__args__
        if len(args) == 2 and args[1] == type(None):  # noqa E721
            return True, args[0]
    if type_ is Any:
        return True, Any

    return False, type_


def get_attr_data(obj: Any) -> Dict[str, Any]:
    from omegaconf.omegaconf import _maybe_wrap

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


def get_dataclass_data(obj: Any) -> Dict[str, Any]:
    from omegaconf.omegaconf import _maybe_wrap

    d = {}
    for field in dataclasses.fields(obj):
        name = field.name
        is_optional, type_ = _resolve_optional(field.type)
        is_nested = is_structured_config(type_)
        if hasattr(obj, name):
            value = getattr(obj, name)
        else:
            if field.default_factory != dataclasses.MISSING:  # type: ignore
                value = field.default_factory()  # type: ignore
            else:
                if is_nested:
                    value = type_
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


def is_dataclass(obj: Any) -> bool:
    from omegaconf.base import Node

    if dataclasses is None or isinstance(obj, Node):
        return False
    return dataclasses.is_dataclass(obj)


def is_attr_class(obj: Any) -> bool:
    from omegaconf.base import Node

    if attr is None or isinstance(obj, Node):
        return False
    return attr.has(obj)


def is_structured_config(obj: Any) -> bool:
    return is_attr_class(obj) or is_dataclass(obj)


def is_dataclass_frozen(type_: Any) -> bool:
    return type_.__dataclass_params__.frozen  # type: ignore


def is_attr_frozen(type_: type) -> bool:
    # This is very hacky and probably fragile as well.
    # Unfortunately currently there isn't an official API in attr that can detect that.
    # noinspection PyProtectedMember
    return type_.__setattr__ == attr._make._frozen_setattrs  # type: ignore


def is_structured_config_frozen(obj: Any) -> bool:
    type_ = obj
    if not isinstance(type_, type):
        type_ = type(obj)

    if is_dataclass(type_):
        return is_dataclass_frozen(type_)
    if is_attr_class(type_):
        return is_attr_frozen(type_)
    raise ValueError("Unexpected object type")


def get_structured_config_data(obj: Any) -> Dict[str, Any]:
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


def get_value_kind(value: Any, return_match_list: bool = False) -> Any:
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
    from .nodes import ValueNode

    if isinstance(value, ValueNode):
        value = value.value()

    key_prefix = r"\${(\w+:)?"
    legal_characters = r"([\w\.%_ \\,-]*?)}"
    match_list: Optional[List[Match[str]]] = None

    def ret(
        value_kind: ValueKind,
    ) -> Union[ValueKind, Tuple[ValueKind, Optional[List[Match[str]]]]]:
        if return_match_list:

            return value_kind, match_list
        else:
            return value_kind

    if value == "???":
        return ret(ValueKind.MANDATORY_MISSING)

    if not isinstance(value, str):
        return ValueKind.VALUE

    match_list = list(re.finditer(key_prefix + legal_characters, value))
    if len(match_list) == 0:
        return ret(ValueKind.VALUE)

    if len(match_list) == 1 and value == match_list[0].group(0):
        return ret(ValueKind.INTERPOLATION)
    else:
        return ret(ValueKind.STR_INTERPOLATION)


def decode_primitive(s: str) -> Any:
    def is_bool(st: str) -> bool:
        st = str.lower(st)
        return st == "true" or st == "false"

    def is_float(st: str) -> bool:
        try:
            float(st)
            return True
        except ValueError:
            return False

    def is_int(st: str) -> bool:
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
def _re_parent(node: Node) -> None:
    from .dictconfig import DictConfig
    from .listconfig import ListConfig

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


def is_primitive_list(obj: Any) -> bool:
    from .base import Container

    return not isinstance(obj, Container) and isinstance(obj, (list, tuple))


def is_primitive_dict(obj: Any) -> bool:
    from .base import Container

    return not isinstance(obj, Container) and isinstance(obj, (dict))


def is_primitive_container(obj: Any) -> bool:
    return is_primitive_list(obj) or is_primitive_dict(obj)
