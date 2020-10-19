import copy
import os
import re
import string
import sys
import warnings
from enum import Enum
from textwrap import dedent
from typing import Any, Dict, List, Match, Optional, Tuple, Type, Union

import yaml

from .errors import (
    ConfigIndexError,
    ConfigTypeError,
    ConfigValueError,
    KeyValidationError,
    OmegaConfBaseException,
    ValidationError,
)

try:
    import dataclasses

except ImportError:  # pragma: no cover
    dataclasses = None  # type: ignore # pragma: no cover

try:
    import attr

except ImportError:  # pragma: no cover
    attr = None  # type: ignore # pragma: no cover


# source: https://yaml.org/type/bool.html
YAML_BOOL_TYPES = [
    "y",
    "Y",
    "yes",
    "Yes",
    "YES",
    "n",
    "N",
    "no",
    "No",
    "NO",
    "true",
    "True",
    "TRUE",
    "false",
    "False",
    "FALSE",
    "on",
    "On",
    "ON",
    "off",
    "Off",
    "OFF",
]


class OmegaConfDumper(yaml.Dumper):  # type: ignore
    str_representer_added = False

    @staticmethod
    def str_representer(dumper: yaml.Dumper, data: str) -> yaml.ScalarNode:
        with_quotes = yaml_is_bool(data) or is_int(data) or is_float(data)
        return dumper.represent_scalar(
            yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG,
            data,
            style=("'" if with_quotes else None),
        )


def get_omega_conf_dumper() -> Type[OmegaConfDumper]:
    if not OmegaConfDumper.str_representer_added:
        OmegaConfDumper.add_representer(str, OmegaConfDumper.str_representer)
        OmegaConfDumper.str_representer_added = True
    return OmegaConfDumper


def yaml_is_bool(b: str) -> bool:
    return b in YAML_BOOL_TYPES


def get_yaml_loader() -> Any:
    # Custom constructor that checks for duplicate keys
    # (from https://gist.github.com/pypt/94d747fe5180851196eb)
    def no_duplicates_constructor(
        loader: yaml.Loader, node: yaml.Node, deep: bool = False
    ) -> Any:
        mapping: Dict[str, Any] = {}
        for key_node, value_node in node.value:
            key = loader.construct_object(key_node, deep=deep)
            value = loader.construct_object(value_node, deep=deep)
            if key in mapping:
                raise yaml.constructor.ConstructorError(
                    "while constructing a mapping",
                    node.start_mark,
                    f"found duplicate key {key}",
                    key_node.start_mark,
                )
            mapping[key] = value
        return loader.construct_mapping(node, deep)

    class OmegaConfLoader(yaml.SafeLoader):  # type: ignore
        pass

    loader = OmegaConfLoader
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
    loader.add_constructor(
        yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, no_duplicates_constructor
    )
    return loader


def _get_class(path: str) -> type:
    from importlib import import_module

    module_path, _, class_name = path.rpartition(".")
    mod = import_module(module_path)
    try:
        klass: type = getattr(mod, class_name)
    except AttributeError:
        raise ImportError(f"Class {class_name} is not in module {module_path}")
    return klass


def _is_union(type_: Any) -> bool:
    return getattr(type_, "__origin__", None) is Union


def _resolve_optional(type_: Any) -> Tuple[bool, Any]:
    if getattr(type_, "__origin__", None) is Union:
        args = type_.__args__
        if len(args) == 2 and args[1] == type(None):  # noqa E721
            return True, args[0]
    if type_ is Any:
        return True, Any

    return False, type_


def _resolve_forward(type_: Type[Any], module: str) -> Type[Any]:
    import typing  # lgtm [py/import-and-import-from]

    forward = typing.ForwardRef if hasattr(typing, "ForwardRef") else typing._ForwardRef  # type: ignore
    if type(type_) is forward:
        return _get_class(f"{module}.{type_.__forward_arg__}")
    else:
        return type_


def _raise_missing_error(obj: Any, name: str) -> None:
    raise ValueError(
        f"Missing default value for {get_type_of(obj).__name__}.{name}, to indicate "
        "default must be populated later use OmegaConf.MISSING"
    )


def get_attr_data(obj: Any) -> Dict[str, Any]:
    from omegaconf.omegaconf import _maybe_wrap

    d = {}
    is_type = isinstance(obj, type)
    obj_type = obj if is_type else type(obj)
    for name, attrib in attr.fields_dict(obj_type).items():
        is_optional, type_ = _resolve_optional(attrib.type)
        is_nested = is_attr_class(type_)
        type_ = _resolve_forward(type_, obj.__module__)
        if not is_type:
            value = getattr(obj, name)
        else:
            value = attrib.default
            if value == attr.NOTHING:
                if is_nested:
                    msg = dedent(
                        f"""
                        The field `{name}` of type '{type_str(type_)}' does not have a default value.
                        The behavior of OmegaConf for such cases is changing in OmegaConf 2.1.
                        See https://github.com/omry/omegaconf/issues/412 for more details.
                        """
                    )
                    warnings.warn(category=UserWarning, message=msg, stacklevel=8)
                    value = type_
                else:
                    _raise_missing_error(obj, name)
                    assert False
        if _is_union(type_):
            e = ConfigValueError(
                f"Union types are not supported:\n{name}: {type_str(type_)}"
            )
            format_and_raise(node=None, key=None, value=value, cause=e, msg=str(e))

        d[name] = _maybe_wrap(
            ref_type=type_, is_optional=is_optional, key=name, value=value, parent=None
        )
    return d


def get_dataclass_data(obj: Any) -> Dict[str, Any]:
    from omegaconf.omegaconf import _maybe_wrap

    d = {}
    for field in dataclasses.fields(obj):
        name = field.name
        is_optional, type_ = _resolve_optional(field.type)
        type_ = _resolve_forward(type_, obj.__module__)
        is_nested = is_structured_config(type_)

        if hasattr(obj, name):
            value = getattr(obj, name)
            if value == dataclasses.MISSING:
                _raise_missing_error(obj, name)
                assert False
        else:
            if field.default_factory == dataclasses.MISSING:  # type: ignore
                if is_nested:
                    msg = dedent(
                        f"""
                        The field `{name}` of type '{type_str(type_)}' does not have a default value.
                        The behavior of OmegaConf for such cases is changing in OmegaConf 2.1.
                        See https://github.com/omry/omegaconf/issues/412 for more details.
                        """
                    )
                    warnings.warn(category=UserWarning, message=msg, stacklevel=8)

                    value = type_
                else:
                    _raise_missing_error(obj, name)
                    assert False
            else:
                value = field.default_factory()  # type: ignore

        if _is_union(type_):
            e = ConfigValueError(
                f"Union types are not supported:\n{name}: {type_str(type_)}"
            )
            format_and_raise(node=None, key=None, value=value, cause=e, msg=str(e))
        d[name] = _maybe_wrap(
            ref_type=type_, is_optional=is_optional, key=name, value=value, parent=None
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


def get_type_of(class_or_object: Any) -> Type[Any]:
    type_ = class_or_object
    if not isinstance(type_, type):
        type_ = type(class_or_object)
    assert isinstance(type_, type)
    return type_


def is_structured_config_frozen(obj: Any) -> bool:
    type_ = get_type_of(obj)

    if is_dataclass(type_):
        return is_dataclass_frozen(type_)
    if is_attr_class(type_):
        return is_attr_frozen(type_)
    return False


def get_structured_config_data(obj: Any) -> Dict[str, Any]:
    if is_dataclass(obj):
        return get_dataclass_data(obj)
    elif is_attr_class(obj):
        return get_attr_data(obj)
    else:
        raise ValueError(f"Unsupported type: {type(obj).__name__}")


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

    key_prefix = r"\${(\w+:)?"
    legal_characters = r"([\w\.%_ \\/:,-]*?)}"
    match_list: Optional[List[Match[str]]] = None

    def ret(
        value_kind: ValueKind,
    ) -> Union[ValueKind, Tuple[ValueKind, Optional[List[Match[str]]]]]:
        if return_match_list:
            return value_kind, match_list
        else:
            return value_kind

    from .base import Container

    if isinstance(value, Container):
        if value._is_interpolation() or value._is_missing():
            value = value._value()

    value = _get_value(value)
    if value == "???":
        return ret(ValueKind.MANDATORY_MISSING)

    if not isinstance(value, str):
        return ret(ValueKind.VALUE)

    match_list = list(re.finditer(key_prefix + legal_characters, value))
    if len(match_list) == 0:
        return ret(ValueKind.VALUE)

    if len(match_list) == 1 and value == match_list[0].group(0):
        return ret(ValueKind.INTERPOLATION)
    else:
        return ret(ValueKind.STR_INTERPOLATION)


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


def decode_primitive(s: str) -> Any:
    if is_bool(s):
        return str.lower(s) == "true"

    if is_int(s):
        return int(s)

    if is_float(s):
        return float(s)

    return s


def is_primitive_list(obj: Any) -> bool:
    from .base import Container

    return not isinstance(obj, Container) and isinstance(obj, (list, tuple))


def is_primitive_dict(obj: Any) -> bool:
    t = get_type_of(obj)
    return t is dict


def is_dict_annotation(type_: Any) -> bool:
    origin = getattr(type_, "__origin__", None)
    if sys.version_info < (3, 7, 0):
        return origin is Dict or type_ is Dict  # pragma: no cover
    else:
        return origin is dict  # pragma: no cover


def is_list_annotation(type_: Any) -> bool:
    origin = getattr(type_, "__origin__", None)
    if sys.version_info < (3, 7, 0):
        return origin is List or type_ is List  # pragma: no cover
    else:
        return origin is list  # pragma: no cover


def is_tuple_annotation(type_: Any) -> bool:
    origin = getattr(type_, "__origin__", None)
    if sys.version_info < (3, 7, 0):
        return origin is Tuple or type_ is Tuple  # pragma: no cover
    else:
        return origin is tuple  # pragma: no cover


def is_dict_subclass(type_: Any) -> bool:
    return type_ is not None and isinstance(type_, type) and issubclass(type_, Dict)


def is_dict(obj: Any) -> bool:
    return is_primitive_dict(obj) or is_dict_annotation(obj) or is_dict_subclass(obj)


def is_primitive_container(obj: Any) -> bool:
    return is_primitive_list(obj) or is_primitive_dict(obj)


def get_list_element_type(ref_type: Optional[Type[Any]]) -> Optional[Type[Any]]:
    args = getattr(ref_type, "__args__", None)
    if ref_type is not List and args is not None and args[0] is not Any:
        element_type = args[0]
    else:
        element_type = None

    if not (valid_value_annotation_type(element_type)):
        raise ValidationError(f"Unsupported value type : {element_type}")
    assert element_type is None or isinstance(element_type, type)
    return element_type


def get_dict_key_value_types(ref_type: Any) -> Tuple[Any, Any]:

    args = getattr(ref_type, "__args__", None)
    if args is None:
        bases = getattr(ref_type, "__orig_bases__", None)
        if bases is not None and len(bases) > 0:
            args = getattr(bases[0], "__args__", None)

    key_type: Any
    element_type: Any
    if ref_type is None:
        key_type = None
        element_type = None
    else:
        if args is not None:
            key_type = args[0]
            element_type = args[1]
            # None is the sentry for any type
            if key_type is Any:
                key_type = None
            if element_type is Any:
                element_type = None
        else:
            key_type = None
            element_type = None

    if not valid_value_annotation_type(element_type) and not is_structured_config(
        element_type
    ):
        raise ValidationError(f"Unsupported value type : {element_type}")

    if not _valid_dict_key_annotation_type(key_type):
        raise KeyValidationError(f"Unsupported key type {key_type}")
    return key_type, element_type


def valid_value_annotation_type(type_: Any) -> bool:
    return type_ is Any or is_primitive_type(type_) or is_structured_config(type_)


def _valid_dict_key_annotation_type(type_: Any) -> bool:
    return type_ is None or issubclass(type_, str) or issubclass(type_, Enum)


def is_primitive_type(type_: Any) -> bool:
    type_ = get_type_of(type_)
    return issubclass(type_, Enum) or type_ in (int, float, bool, str, type(None))


def _is_interpolation(v: Any) -> bool:
    if isinstance(v, str):
        ret = get_value_kind(v) in (
            ValueKind.INTERPOLATION,
            ValueKind.STR_INTERPOLATION,
        )
        assert isinstance(ret, bool)
        return ret
    return False


def _get_value(value: Any) -> Any:
    from .base import Container
    from .nodes import ValueNode

    if isinstance(value, Container) and value._is_none():
        return None
    if isinstance(value, ValueNode):
        value = value._value()
    return value


def get_ref_type(obj: Any, key: Any = None) -> Optional[Type[Any]]:
    from omegaconf import DictConfig, ListConfig
    from omegaconf.base import Container, Node
    from omegaconf.nodes import ValueNode

    def none_as_any(t: Optional[Type[Any]]) -> Union[Type[Any], Any]:
        if t is None:
            return Any
        else:
            return t

    if isinstance(obj, Container) and key is not None:
        obj = obj._get_node(key)

    is_optional = True
    ref_type = None
    if isinstance(obj, ValueNode):
        is_optional = obj._is_optional()
        ref_type = obj._metadata.ref_type
    elif isinstance(obj, Container):
        if isinstance(obj, Node):
            ref_type = obj._metadata.ref_type
        is_optional = obj._is_optional()
        kt = none_as_any(obj._metadata.key_type)
        vt = none_as_any(obj._metadata.element_type)
        if (
            ref_type is Any
            and kt is Any
            and vt is Any
            and not obj._is_missing()
            and not obj._is_none()
        ):
            ref_type = Any  # type: ignore
        elif not is_structured_config(ref_type):
            if kt is Any:
                kt = Union[str, Enum]
            if isinstance(obj, DictConfig):
                ref_type = Dict[kt, vt]  # type: ignore
            elif isinstance(obj, ListConfig):
                ref_type = List[vt]  # type: ignore
    else:
        if isinstance(obj, dict):
            ref_type = Dict[Union[str, Enum], Any]
        elif isinstance(obj, (list, tuple)):
            ref_type = List[Any]
        else:
            ref_type = get_type_of(obj)

    ref_type = none_as_any(ref_type)
    if is_optional and ref_type is not Any:
        ref_type = Optional[ref_type]  # type: ignore
    return ref_type


def _raise(ex: Exception, cause: Exception) -> None:
    # Set the environment variable OC_CAUSE=1 to get a stacktrace that includes the
    # causing exception.
    env_var = os.environ["OC_CAUSE"] if "OC_CAUSE" in os.environ else None
    debugging = sys.gettrace() is not None
    full_backtrace = (debugging and not env_var == "0") or (env_var == "1")
    if full_backtrace:
        ex.__cause__ = cause
    else:
        ex.__cause__ = None
    raise ex  # set end OC_CAUSE=1 for full backtrace


def format_and_raise(
    node: Any,
    key: Any,
    value: Any,
    msg: str,
    cause: Exception,
    type_override: Any = None,
) -> None:
    from omegaconf import OmegaConf
    from omegaconf.base import Node

    if isinstance(cause, OmegaConfBaseException) and cause._initialized:
        ex = cause
        if type_override is not None:
            ex = type_override(str(cause))
            ex.__dict__ = copy.deepcopy(cause.__dict__)
        _raise(ex, cause)

    object_type: Optional[Type[Any]]
    object_type_str: Optional[str] = None
    ref_type: Optional[Type[Any]]
    ref_type_str: Optional[str]

    child_node: Optional[Node] = None
    if node is None:
        full_key = ""
        object_type = None
        ref_type = None
        ref_type_str = None
    else:
        if key is not None and not OmegaConf.is_none(node):
            child_node = node._get_node(key, validate_access=False)

        full_key = node._get_full_key(key=key)

        object_type = OmegaConf.get_type(node)
        object_type_str = type_str(object_type)

        ref_type = get_ref_type(node)
        ref_type_str = type_str(ref_type)

    msg = string.Template(msg).substitute(
        REF_TYPE=ref_type_str,
        OBJECT_TYPE=object_type_str,
        KEY=key,
        FULL_KEY=full_key,
        VALUE=value,
        VALUE_TYPE=f"{type(value).__name__}",
        KEY_TYPE=f"{type(key).__name__}",
    )

    template = """$MSG
\tfull_key: $FULL_KEY
\treference_type=$REF_TYPE
\tobject_type=$OBJECT_TYPE"""

    s = string.Template(template=template)

    message = s.substitute(
        REF_TYPE=ref_type_str, OBJECT_TYPE=object_type_str, MSG=msg, FULL_KEY=full_key
    )
    exception_type = type(cause) if type_override is None else type_override
    if exception_type == TypeError:
        exception_type = ConfigTypeError
    elif exception_type == IndexError:
        exception_type = ConfigIndexError

    ex = exception_type(f"{message}")
    if issubclass(exception_type, OmegaConfBaseException):
        ex._initialized = True
        ex.msg = message
        ex.parent_node = node
        ex.child_node = child_node
        ex.key = key
        ex.full_key = full_key
        ex.value = value
        ex.object_type = object_type
        ex.object_type_str = object_type_str
        ex.ref_type = ref_type
        ex.ref_type_str = ref_type_str

    _raise(ex, cause)


def type_str(t: Any) -> str:
    is_optional, t = _resolve_optional(t)
    if t is None:
        return type(t).__name__
    if t is Any:
        return "Any"
    if sys.version_info < (3, 7, 0):  # pragma: no cover
        # Python 3.6
        if hasattr(t, "__name__"):
            name = str(t.__name__)
        else:
            if t.__origin__ is not None:
                name = type_str(t.__origin__)
            else:
                name = str(t)
                if name.startswith("typing."):
                    name = name[len("typing.") :]
    else:  # pragma: no cover
        # Python >= 3.7
        if hasattr(t, "__name__"):
            name = str(t.__name__)
        else:
            if t._name is None:
                if t.__origin__ is not None:
                    name = type_str(t.__origin__)
            else:
                name = str(t._name)

    args = getattr(t, "__args__", None)
    if args is not None:
        args = ", ".join([type_str(t) for t in (list(t.__args__))])
        ret = f"{name}[{args}]"
    else:
        ret = name
    if is_optional:
        return f"Optional[{ret}]"
    else:
        return ret


def _ensure_container(target: Any) -> Any:
    from omegaconf import OmegaConf

    if is_primitive_container(target):
        assert isinstance(target, (list, dict))
        target = OmegaConf.create(target)
    elif is_structured_config(target):
        target = OmegaConf.structured(target)
    assert OmegaConf.is_config(target)
    return target


def is_generic_list(type_: Any) -> bool:
    """
    Checks if a type is a generic list, for example:
    list returns False
    typing.List returns False
    typing.List[T] returns True

    :param type_: variable type
    :return: bool
    """
    return is_list_annotation(type_) and get_list_element_type(type_) is not None


def is_generic_dict(type_: Any) -> bool:
    """
    Checks if a type is a generic dict, for example:
    list returns False
    typing.List returns False
    typing.List[T] returns True

    :param type_: variable type
    :return: bool
    """
    return is_dict_annotation(type_) and len(get_dict_key_value_types(type_)) > 0
