"""OmegaConf module"""
import copy
import io
import os
import re
import sys
from contextlib import contextmanager
from enum import Enum
from typing import Any, Callable, Dict, Generator, List, Match, Optional, Tuple, Union

import yaml

from . import DictConfig, ListConfig
from ._utils import decode_primitive, is_structured_config, isint
from .base import Container, Node
from .basecontainer import BaseContainer
from .errors import MissingMandatoryValue, ValidationError
from .nodes import (
    AnyNode,
    BooleanNode,
    EnumNode,
    FloatNode,
    IntegerNode,
    StringNode,
    ValueNode,
)

MISSING: Any = "???"


def II(interpolation: str) -> Any:
    """
    Equivalent to ${interpolation}
    :param interpolation:
    :return: input ${node} with type Any
    """
    return "${" + interpolation + "}"


def SI(interpolation: str) -> Any:
    """
    Use this for String interpolation, for example "http://${host}:${port}"
    :param interpolation: interpolation string
    :return: input interpolation with type Any
    """
    assert interpolation.find("${") != -1
    return interpolation


def register_default_resolvers() -> None:
    def env(key: str) -> Any:
        try:
            return decode_primitive(os.environ[key])
        except KeyError:
            raise KeyError("Environment variable '{}' not found".format(key))

    OmegaConf.register_resolver("env", env)


class OmegaConf:
    """OmegaConf primary class"""

    def __init__(self) -> None:
        raise NotImplementedError("Use one of the static construction functions")

    @staticmethod
    def create(
        obj: Any = None, parent: Optional[BaseContainer] = None
    ) -> Union[DictConfig, ListConfig]:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig
        from ._utils import get_yaml_loader

        if isinstance(obj, str):
            new_obj = yaml.load(obj, Loader=get_yaml_loader())
            if new_obj is None:
                new_obj = {}
            elif isinstance(new_obj, str):
                new_obj = {obj: None}
            return OmegaConf.create(new_obj)
        else:
            if obj is None:
                obj = {}
            if isinstance(obj, BaseContainer):
                obj = OmegaConf.to_container(obj)

            if isinstance(obj, dict) or is_structured_config(obj):
                return DictConfig(obj, parent)
            elif isinstance(obj, list) or isinstance(obj, tuple):
                return ListConfig(obj, parent)
            else:
                raise ValidationError("Unsupported type {}".format(type(obj).__name__))

    @staticmethod
    def load(file_: str) -> Union[DictConfig, ListConfig]:
        from ._utils import get_yaml_loader

        if isinstance(file_, str):
            with io.open(os.path.abspath(file_), "r", encoding="utf-8") as f:
                return OmegaConf.create(yaml.load(f, Loader=get_yaml_loader()))
        elif getattr(file_, "read", None):
            return OmegaConf.create(yaml.load(file_, Loader=get_yaml_loader()))
        else:
            raise TypeError("Unexpected file type")

    @staticmethod
    def save(config: BaseContainer, f: str, resolve: bool = False) -> None:
        """
        Save as configuration object to a file
        :param config: omegaconf.Config object (DictConfig or ListConfig).
        :param f: filename or file object
        :param resolve: True to save a resolved config (defaults to False)
        """
        data = config.pretty(resolve=resolve)
        if isinstance(f, str):
            with io.open(os.path.abspath(f), "w", encoding="utf-8") as file:
                file.write(data)
        elif hasattr(f, "write"):
            f.write(data)
            f.flush()
        else:
            raise TypeError("Unexpected file type")

    @staticmethod
    def from_cli(args_list: Optional[List[str]] = None) -> DictConfig:
        if args_list is None:
            # Skip program name
            args_list = sys.argv[1:]
        return OmegaConf.from_dotlist(args_list)

    @staticmethod
    def from_dotlist(dotlist: List[str]) -> DictConfig:
        """
        Creates config from the content sys.argv or from the specified args list of not None
        :param dotlist:
        :return:
        """
        conf = OmegaConf.create()
        conf.merge_with_dotlist(dotlist)
        return conf  # type: ignore

    @staticmethod
    def merge(
        *others: Union[BaseContainer, Dict[str, Any], List[Any], Tuple[Any], Any]
    ) -> BaseContainer:
        """Merge a list of previously created configs into a single one"""
        assert len(others) > 0
        target = copy.deepcopy(others[0])
        if isinstance(target, (dict, list, tuple)) or is_structured_config(target):
            target = OmegaConf.create(target)
        target.merge_with(*others[1:])
        return target

    @staticmethod
    def _tokenize_args(string: Optional[str]) -> List[str]:
        if string is None or string == "":
            return []

        def _unescape_word_boundary(match: Match[str]) -> str:
            if match.start() == 0 or match.end() == len(match.string):
                return ""
            return match.group(0)

        escaped = re.split(r"(?<!\\),", string)
        escaped = [re.sub(r"(?<!\\) ", _unescape_word_boundary, x) for x in escaped]
        return [re.sub(r"(\\([ ,]))", lambda x: x.group(2), x) for x in escaped]

    @staticmethod
    def register_resolver(name: str, resolver: Callable[[Any], Any]) -> None:
        assert callable(resolver), "resolver must be callable"
        # noinspection PyProtectedMember
        assert (
            name not in BaseContainer._resolvers
        ), "resolved {} is already registered".format(name)

        def caching(config: BaseContainer, key: str) -> Any:
            cache = OmegaConf.get_cache(config)[name]
            val = (
                cache[key] if key in cache else resolver(*OmegaConf._tokenize_args(key))
            )
            cache[key] = val
            return val

        # noinspection PyProtectedMember
        BaseContainer._resolvers[name] = caching

    # noinspection PyProtectedMember
    @staticmethod
    def get_resolver(name: str) -> Optional[Callable[[Container, Any], Any]]:
        return (
            BaseContainer._resolvers[name] if name in BaseContainer._resolvers else None
        )

    # noinspection PyProtectedMember
    @staticmethod
    def clear_resolvers() -> None:
        BaseContainer._resolvers = {}
        register_default_resolvers()

    @staticmethod
    def get_cache(conf: BaseContainer) -> Dict[str, Any]:
        return conf.__dict__["_resolver_cache"]  # type: ignore

    @staticmethod
    def set_cache(conf: BaseContainer, cache: Dict[str, Any]) -> None:
        conf.__dict__["_resolver_cache"] = copy.deepcopy(cache)

    @staticmethod
    def copy_cache(from_config: BaseContainer, to_config: BaseContainer) -> None:
        OmegaConf.set_cache(to_config, OmegaConf.get_cache(from_config))

    @staticmethod
    def set_readonly(conf: Node, value: Optional[bool]) -> None:
        # noinspection PyProtectedMember
        conf._set_flag("readonly", value)

    @staticmethod
    def is_readonly(conf: Node) -> Optional[bool]:
        # noinspection PyProtectedMember
        return conf._get_flag("readonly")

    @staticmethod
    def set_struct(conf: Container, value: Optional[bool]) -> None:
        # noinspection PyProtectedMember
        conf._set_flag("struct", value)

    @staticmethod
    def is_struct(conf: Container) -> Optional[bool]:
        # noinspection PyProtectedMember
        return conf._get_flag("struct")

    @staticmethod
    def masked_copy(conf: DictConfig, keys: Union[str, List[str]]) -> DictConfig:
        """
        Create a masked copy of of this config that contains a subset of the keys
        :param conf: DictConfig object
        :param keys: keys to preserve in the copy
        :return:
        """
        from .dictconfig import DictConfig

        if not isinstance(conf, DictConfig):
            raise ValueError("masked_copy is only supported for DictConfig")

        if isinstance(keys, str):
            keys = [keys]
        content = {key: value for key, value in conf.items(resolve=False, keys=keys)}
        return DictConfig(content=content)

    @staticmethod
    def to_container(
        cfg: BaseContainer, resolve: bool = False, enum_to_str: bool = False
    ) -> Union[Dict[str, Any], List[Any]]:
        """
        Resursively converts an OmegaConf config to a primitive container (dict or list).
        :param cfg: the config to convert
        :param resolve: True to resolve all values
        :param enum_to_str: True to convert Enum values to strings
        :return: A dict or a list representing this config as a primitive container.
        """
        assert isinstance(cfg, BaseContainer)
        # noinspection PyProtectedMember
        return BaseContainer._to_content(cfg, resolve=resolve, enum_to_str=enum_to_str)

    @staticmethod
    def is_missing(cfg: BaseContainer, key: Union[int, str]) -> bool:
        try:
            cfg.__getitem__(key)
            return False
        except MissingMandatoryValue:
            return True

    @staticmethod
    def is_list(obj: Any) -> bool:
        from . import ListConfig

        return isinstance(obj, ListConfig)

    @staticmethod
    def is_dict(obj: Any) -> bool:
        from . import DictConfig

        return isinstance(obj, DictConfig)

    @staticmethod
    def is_config(obj: Any) -> bool:
        from . import BaseContainer

        return isinstance(obj, BaseContainer)


# register all default resolvers
register_default_resolvers()


# noinspection PyProtectedMember
@contextmanager
def flag_override(
    config: Node, name: str, value: Optional[bool]
) -> Generator[Node, None, None]:
    prev_state = config._get_flag(name)
    try:
        config._set_flag(name, value)
        yield config
    finally:
        config._set_flag(name, prev_state)


# noinspection PyProtectedMember
@contextmanager
def read_write(config: Node) -> Generator[Node, None, None]:
    # noinspection PyProtectedMember
    prev_state = config._get_node_flag("readonly")
    try:
        OmegaConf.set_readonly(config, False)
        yield config
    finally:
        OmegaConf.set_readonly(config, prev_state)


@contextmanager
def open_dict(config: Container) -> Generator[Container, None, None]:
    # noinspection PyProtectedMember
    prev_state = config._get_node_flag("struct")
    try:
        OmegaConf.set_struct(config, False)
        yield config
    finally:
        OmegaConf.set_struct(config, prev_state)


# === private === #


def _is_primitive_type(type_: Any) -> bool:
    if not isinstance(type_, type):
        type_ = type(type_)

    return issubclass(type_, Enum) or type_ in (int, float, bool, str, type(None))


def _valid_value_annotation_type(type_: Any) -> bool:
    return type_ is Any or _is_primitive_type(type_) or is_structured_config(type_)


def _node_wrap(
    type_: Any, parent: Optional[BaseContainer], is_optional: bool, value: Any
) -> ValueNode:
    node: ValueNode
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


def _maybe_wrap(
    annotated_type: Any, value: Any, is_optional: bool, parent: Optional[BaseContainer]
) -> Node:
    if isinstance(value, ValueNode):
        return value

    from omegaconf import OmegaConf

    if isinstance(value, BaseContainer):
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


def _select_one(c: BaseContainer, key: str) -> Tuple[Any, Union[str, int]]:
    from .listconfig import ListConfig
    from .dictconfig import DictConfig

    ret_key: Union[str, int] = key
    assert isinstance(c, (DictConfig, ListConfig)), f"Unexpected type : {c}"
    if isinstance(c, DictConfig):
        assert isinstance(ret_key, str)
        if c.get_node(ret_key, validate_access=False) is not None:
            val = c[ret_key]
        else:
            val = None
    elif isinstance(c, ListConfig):
        assert isinstance(ret_key, str)
        if not isint(ret_key):
            raise TypeError("Index {} is not an int".format(ret_key))
        ret_key = int(ret_key)
        if ret_key < 0 or ret_key + 1 > len(c):
            val = None
        else:
            val = c[ret_key]

    return val, ret_key
