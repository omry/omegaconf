import copy
import os
import re
import string
import sys
from enum import Enum
from functools import cmp_to_key
from textwrap import dedent
from typing import Any, Dict, List, Optional, Tuple, Type, Union, get_type_hints

import yaml

from .errors import (
    ConfigIndexError,
    ConfigTypeError,
    ConfigValueError,
    OmegaConfBaseException,
)
from .grammar_parser import parse

try:
    import dataclasses

except ImportError:  # pragma: no cover
    dataclasses = None  # type: ignore # pragma: no cover

try:
    import attr

except ImportError:  # pragma: no cover
    attr = None  # type: ignore # pragma: no cover

# Build regex pattern to efficiently identify typical interpolations.
# See test `test_match_simple_interpolation_pattern` for examples.
_id = "[a-zA-Z_]\\w*"  # foo, foo_bar, abc123
_dot_path = f"{_id}(\\.{_id})*"  # foo, foo.bar3, foo_.b4r.b0z
_inter_node = f"\\${{\\s*{_dot_path}\\s*}}"  # node interpolation
_arg = "[a-zA-Z_0-9/\\-\\+.$%*@]+"  # string representing a resolver argument
_args = f"{_arg}(\\s*,\\s*{_arg})*"  # list of resolver arguments
_inter_res = f"\\${{\\s*{_dot_path}\\s*:\\s*{_args}?\\s*}}"  # resolver interpolation
_inter = f"({_inter_node}|{_inter_res})"  # any kind of interpolation
_outer = "([^$]|\\$(?!{))+"  # any character except $ (unless not followed by {)
SIMPLE_INTERPOLATION_PATTERN = re.compile(
    f"({_outer})?({_inter}({_outer})?)+$", flags=re.ASCII
)

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

# Define an arbitrary (but fixed) ordering over the types of dictionary keys
# that may be encountered when calling `_make_hashable()` on a dict.
_CMP_TYPES = {t: i for i, t in enumerate([float, int, bool, str, type(None)])}


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
    class OmegaConfLoader(yaml.SafeLoader):  # type: ignore
        def construct_mapping(self, node: yaml.Node, deep: bool = False) -> Any:
            keys = set()
            for key_node, value_node in node.value:
                if key_node.tag != yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG:
                    continue
                if key_node.value in keys:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found duplicate key {key_node.value}",
                        key_node.start_mark,
                    )
                keys.add(key_node.value)
            return super().construct_mapping(node, deep=deep)

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
        if is_dict_annotation(type_):
            kt, vt = get_dict_key_value_types(type_)
            if kt is not None:
                kt = _resolve_forward(kt, module=module)
            if vt is not None:
                vt = _resolve_forward(vt, module=module)
            return Dict[kt, vt]  # type: ignore
        if is_list_annotation(type_):
            et = get_list_element_type(type_)
            if et is not None:
                et = _resolve_forward(et, module=module)
            return List[et]  # type: ignore

        return type_


def get_attr_data(obj: Any, allow_objects: Optional[bool] = None) -> Dict[str, Any]:
    from omegaconf.omegaconf import OmegaConf, _maybe_wrap

    flags = {"allow_objects": allow_objects} if allow_objects is not None else {}
    dummy_parent = OmegaConf.create(flags=flags)
    from omegaconf import MISSING

    d = {}
    is_type = isinstance(obj, type)
    obj_type = obj if is_type else type(obj)
    for name, attrib in attr.fields_dict(obj_type).items():
        is_optional, type_ = _resolve_optional(attrib.type)
        type_ = _resolve_forward(type_, obj.__module__)
        if not is_type:
            value = getattr(obj, name)
        else:
            value = attrib.default
            if value == attr.NOTHING:
                value = MISSING
        if _is_union(type_):
            e = ConfigValueError(
                f"Union types are not supported:\n{name}: {type_str(type_)}"
            )
            format_and_raise(node=None, key=None, value=value, cause=e, msg=str(e))

        d[name] = _maybe_wrap(
            ref_type=type_,
            is_optional=is_optional,
            key=name,
            value=value,
            parent=dummy_parent,
        )
        d[name]._set_parent(None)
    return d


def get_dataclass_data(
    obj: Any, allow_objects: Optional[bool] = None
) -> Dict[str, Any]:
    from omegaconf.omegaconf import MISSING, OmegaConf, _maybe_wrap

    flags = {"allow_objects": allow_objects} if allow_objects is not None else {}
    dummy_parent = OmegaConf.create({}, flags=flags)
    d = {}
    resolved_hints = get_type_hints(get_type_of(obj))
    for field in dataclasses.fields(obj):
        name = field.name
        is_optional, type_ = _resolve_optional(resolved_hints[field.name])
        type_ = _resolve_forward(type_, obj.__module__)

        if hasattr(obj, name):
            value = getattr(obj, name)
            if value == dataclasses.MISSING:
                value = MISSING
        else:
            if field.default_factory == dataclasses.MISSING:  # type: ignore
                value = MISSING
            else:
                value = field.default_factory()  # type: ignore

        if _is_union(type_):
            e = ConfigValueError(
                f"Union types are not supported:\n{name}: {type_str(type_)}"
            )
            format_and_raise(node=None, key=None, value=value, cause=e, msg=str(e))
        d[name] = _maybe_wrap(
            ref_type=type_,
            is_optional=is_optional,
            key=name,
            value=value,
            parent=dummy_parent,
        )
        d[name]._set_parent(None)
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


def get_structured_config_data(
    obj: Any, allow_objects: Optional[bool] = None
) -> Dict[str, Any]:
    if is_dataclass(obj):
        return get_dataclass_data(obj, allow_objects=allow_objects)
    elif is_attr_class(obj):
        return get_attr_data(obj, allow_objects=allow_objects)
    else:
        raise ValueError(f"Unsupported type: {type(obj).__name__}")


class ValueKind(Enum):
    VALUE = 0
    MANDATORY_MISSING = 1
    INTERPOLATION = 2


def get_value_kind(
    value: Any, strict_interpolation_validation: bool = False
) -> ValueKind:
    """
    Determine the kind of a value
    Examples:
    VALUE : "10", "20", True
    MANDATORY_MISSING : "???"
    INTERPOLATION: "${foo.bar}", "${foo.${bar}}", "${foo:bar}", "[${foo}, ${bar}]",
                   "ftp://${host}/path", "${foo:${bar}, [true], {'baz': ${baz}}}"

    :param value: Input to classify.
    :param strict_interpolation_validation: If `True`, then when `value` is a string
        containing "${", it is parsed to validate the interpolation syntax. If `False`,
        this parsing step is skipped: this is more efficient, but will not detect errors.
    """

    value = _get_value(value)

    if isinstance(value, str) and value == "???":
        return ValueKind.MANDATORY_MISSING

    # We identify potential interpolations by the presence of "${" in the string.
    # Note that escaped interpolations (ex: "esc: \${bar}") are identified as
    # interpolations: this is intended, since they must be processed as interpolations
    # for the string to be properly un-escaped.
    # Keep in mind that invalid interpolations will only be detected when
    # `strict_interpolation_validation` is True.
    if isinstance(value, str) and "${" in value:
        if strict_interpolation_validation:
            # First try the cheap regex matching that detects common interpolations.
            if SIMPLE_INTERPOLATION_PATTERN.match(value) is None:
                # If no match, do the more expensive grammar parsing to detect errors.
                parse(value)
        return ValueKind.INTERPOLATION
    else:
        return ValueKind.VALUE


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
    else:  # pragma: no cover
        # type_dict is a bit hard to detect.
        # this support is tentative, if it eventually causes issues in other areas it may be dropped.
        typed_dict = hasattr(type_, "__base__") and type_.__base__ == dict
        return origin is dict or typed_dict


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


def get_list_element_type(ref_type: Optional[Type[Any]]) -> Any:
    args = getattr(ref_type, "__args__", None)
    if ref_type is not List and args is not None and args[0]:
        element_type = args[0]
    else:
        element_type = Any
    return element_type


def get_dict_key_value_types(ref_type: Any) -> Tuple[Any, Any]:
    args = getattr(ref_type, "__args__", None)
    if args is None:
        bases = getattr(ref_type, "__orig_bases__", None)
        if bases is not None and len(bases) > 0:
            args = getattr(bases[0], "__args__", None)

    key_type: Any
    element_type: Any
    if ref_type is None or ref_type == Dict:
        key_type = Any
        element_type = Any
    else:
        if args is not None:
            key_type = args[0]
            element_type = args[1]
        else:
            key_type = Any
            element_type = Any

    return key_type, element_type


def valid_value_annotation_type(type_: Any) -> bool:
    return type_ is Any or is_primitive_type(type_) or is_structured_config(type_)


def _valid_dict_key_annotation_type(type_: Any) -> bool:
    from omegaconf import DictKeyType

    return type_ is None or type_ is Any or issubclass(type_, DictKeyType.__args__)  # type: ignore


def is_primitive_type(type_: Any) -> bool:
    type_ = get_type_of(type_)
    return issubclass(type_, Enum) or type_ in (int, float, bool, str, type(None))


def _is_interpolation(v: Any, strict_interpolation_validation: bool = False) -> bool:
    if isinstance(v, str):
        ret = (
            get_value_kind(v, strict_interpolation_validation)
            == ValueKind.INTERPOLATION
        )
        assert isinstance(ret, bool)
        return ret
    return False


def _get_value(value: Any) -> Any:
    from .base import Container
    from .nodes import ValueNode

    if isinstance(value, Container) and (
        value._is_none() or value._is_interpolation() or value._is_missing()
    ):
        return value._value()
    if isinstance(value, ValueNode):
        value = value._value()
    return value


def get_ref_type(obj: Any, key: Any = None) -> Optional[Type[Any]]:
    from omegaconf import Container, Node

    if isinstance(obj, Container):
        if key is not None:
            obj = obj._get_node(key)
    else:
        if key is not None:
            raise ValueError("Key must only be provided when obj is a container")

    if isinstance(obj, Node):
        ref_type = obj._metadata.ref_type
        if obj._is_optional() and ref_type is not Any:
            return Optional[ref_type]  # type: ignore
        else:
            return ref_type
    else:
        return Any  # type: ignore


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
    raise ex.with_traceback(sys.exc_info()[2])  # set end OC_CAUSE=1 for full backtrace


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

    if isinstance(cause, AssertionError):
        raise

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

    msg = string.Template(msg).safe_substitute(
        REF_TYPE=ref_type_str,
        OBJECT_TYPE=object_type_str,
        KEY=key,
        FULL_KEY=full_key,
        VALUE=value,
        VALUE_TYPE=f"{type(value).__name__}",
        KEY_TYPE=f"{type(key).__name__}",
    )

    if ref_type not in (None, Any):
        template = dedent(
            """\
            $MSG
                full_key: $FULL_KEY
                reference_type=$REF_TYPE
                object_type=$OBJECT_TYPE"""
        )
    else:
        template = dedent(
            """\
            $MSG
                full_key: $FULL_KEY
                object_type=$OBJECT_TYPE"""
        )
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
    if t is ...:
        return "..."

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
        args = ", ".join([type_str(t) for t in t.__args__])
        ret = f"{name}[{args}]"
    else:
        ret = name
    if is_optional:
        return f"Optional[{ret}]"
    else:
        return ret


def _ensure_container(target: Any, flags: Optional[Dict[str, bool]] = None) -> Any:
    from omegaconf import OmegaConf

    if is_primitive_container(target):
        assert isinstance(target, (list, dict))
        target = OmegaConf.create(target, flags=flags)
    elif is_structured_config(target):
        target = OmegaConf.structured(target, flags=flags)
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


def is_container_annotation(type_: Any) -> bool:
    return is_list_annotation(type_) or is_dict_annotation(type_)


def _make_hashable(x: Any) -> Any:
    """
    Obtain a hashable version of `x`.

    This is achieved by turning into tuples the lists and dicts that may be
    stored within `x`.
    Note that dicts are sorted, so that two dicts ordered differently will
    lead to the same resulting hashable key.

    :return: a hashable version of `x` (which may be `x` itself if already hashable).
    """
    # Hopefully it is already hashable and we have nothing to do!
    try:
        hash(x)
        return x
    except TypeError:
        pass

    if isinstance(x, (list, tuple)):
        return tuple(_make_hashable(y) for y in x)
    elif isinstance(x, dict):
        # We sort the dictionary so that the order of keys does not matter.
        # Note that since keys might be of different types, and comparisons
        # between different types are not always allowed, we use a custom
        # `_safe_items_sort_key()` function to order keys.
        return _make_hashable(tuple(sorted(x.items(), key=_safe_items_sort_key)))
    else:
        raise NotImplementedError(f"type {type(x)} cannot be made hashable")


def _safe_cmp(x: Any, y: Any) -> int:
    """
    Compare two elements `x` and `y` in a "safe" way.

    By default, this function uses regular comparison operators (== and <), but
    if an exception is raised (due to not being able to compare x and y), we instead
    use `_CMP_TYPES` to decide which order to use.
    """
    try:
        return 0 if x == y else -1 if x < y else 1
    except Exception:
        type_x, type_y = type(x), type(y)
        try:
            idx_x = _CMP_TYPES[type_x]
            idx_y = _CMP_TYPES[type_y]
        except KeyError:
            bad_type = type_x if type_y in _CMP_TYPES else type_y
            raise TypeError(f"Invalid data type: `{bad_type}`")
        if idx_x == idx_y:  # cannot compare two elements of the same type?!
            raise  # pragma: no cover
        return -1 if idx_x < idx_y else 1


_safe_key = cmp_to_key(_safe_cmp)


def _safe_items_sort_key(kv: Tuple[Any, Any]) -> Any:
    """Safe function to use as sort key when sorting items in a dictionary"""
    return _safe_key(kv[0])
