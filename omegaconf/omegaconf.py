"""OmegaConf module"""
import copy
import io
import os
import pathlib
import re
import sys
import warnings
from collections import defaultdict
from contextlib import contextmanager
from enum import Enum
from textwrap import dedent
from typing import (
    IO,
    Any,
    Callable,
    Dict,
    Generator,
    List,
    Match,
    Optional,
    Tuple,
    Type,
    Union,
    overload,
)

import yaml
from typing_extensions import Protocol

from . import DictConfig, ListConfig
from ._utils import (
    _ensure_container,
    _get_value,
    decode_primitive,
    format_and_raise,
    get_dict_key_value_types,
    get_list_element_type,
    get_omega_conf_dumper,
    get_type_of,
    is_attr_class,
    is_dataclass,
    is_dict_annotation,
    is_int,
    is_list_annotation,
    is_primitive_container,
    is_primitive_dict,
    is_primitive_list,
    is_structured_config,
    is_tuple_annotation,
    type_str,
)
from .base import Container, Node
from .basecontainer import BaseContainer
from .errors import (
    MissingMandatoryValue,
    OmegaConfBaseException,
    UnsupportedInterpolationType,
    ValidationError,
)
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

# A marker used in OmegaConf.create() to differentiate between creating an empty {} DictConfig
# and creating a DictConfig with None content.
_EMPTY_MARKER_ = object()


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
    return interpolation


class Resolver0(Protocol):
    def __call__(self) -> Any:
        ...


class Resolver1(Protocol):
    def __call__(self, __x1: str) -> Any:
        ...


class Resolver2(Protocol):
    def __call__(self, __x1: str, __x2: str) -> Any:
        ...


class Resolver3(Protocol):
    def __call__(self, __x1: str, __x2: str, __x3: str) -> Any:
        ...


Resolver = Union[Resolver0, Resolver1, Resolver2, Resolver3]


def register_default_resolvers() -> None:
    def env(key: str, default: Optional[str] = None) -> Any:
        try:
            return decode_primitive(os.environ[key])
        except KeyError:
            if default is not None:
                return decode_primitive(default)
            else:
                raise ValidationError(f"Environment variable '{key}' not found")

    OmegaConf.register_resolver("env", env)


class OmegaConf:
    """OmegaConf primary class"""

    def __init__(self) -> None:
        raise NotImplementedError("Use one of the static construction functions")

    @staticmethod
    def structured(obj: Any, parent: Optional[BaseContainer] = None) -> Any:
        return OmegaConf.create(obj, parent)

    @staticmethod
    @overload
    def create(
        obj: str, parent: Optional[BaseContainer] = None
    ) -> Union[DictConfig, ListConfig]:
        ...

    @staticmethod
    @overload
    def create(
        obj: Union[List[Any], Tuple[Any, ...]], parent: Optional[BaseContainer] = None
    ) -> ListConfig:
        ...

    @staticmethod
    @overload
    def create(obj: DictConfig, parent: Optional[BaseContainer] = None) -> DictConfig:
        ...

    @staticmethod
    @overload
    def create(obj: ListConfig, parent: Optional[BaseContainer] = None) -> ListConfig:
        ...

    @staticmethod
    @overload
    def create(
        obj: Union[Dict[str, Any], None] = None, parent: Optional[BaseContainer] = None
    ) -> DictConfig:
        ...

    @staticmethod
    def create(  # noqa F811
        obj: Any = _EMPTY_MARKER_, parent: Optional[BaseContainer] = None
    ) -> Union[DictConfig, ListConfig]:
        return OmegaConf._create_impl(obj=obj, parent=parent)

    @staticmethod
    def _create_impl(  # noqa F811
        obj: Any = _EMPTY_MARKER_, parent: Optional[BaseContainer] = None
    ) -> Union[DictConfig, ListConfig]:
        try:
            from ._utils import get_yaml_loader
            from .dictconfig import DictConfig
            from .listconfig import ListConfig

            if obj is _EMPTY_MARKER_:
                obj = {}
            if isinstance(obj, str):
                obj = yaml.load(obj, Loader=get_yaml_loader())
                if obj is None:
                    return OmegaConf.create({})
                elif isinstance(obj, str):
                    return OmegaConf.create({obj: None})
                else:
                    assert isinstance(obj, (list, dict))
                    return OmegaConf.create(obj)

            else:
                if (
                    is_primitive_dict(obj)
                    or OmegaConf.is_dict(obj)
                    or is_structured_config(obj)
                    or obj is None
                ):
                    ref_type = None
                    if is_structured_config(obj):
                        ref_type = get_type_of(obj)
                    elif OmegaConf.is_dict(obj):
                        ref_type = obj._metadata.ref_type

                    if ref_type is None:
                        ref_type = OmegaConf.get_type(obj)

                    if isinstance(obj, DictConfig):
                        key_type = obj._metadata.key_type
                        element_type = obj._metadata.element_type
                    else:
                        key_type, element_type = get_dict_key_value_types(ref_type)
                    return DictConfig(
                        content=obj,
                        parent=parent,
                        ref_type=ref_type,
                        key_type=key_type,
                        element_type=element_type,
                    )
                elif is_primitive_list(obj) or OmegaConf.is_list(obj):
                    ref_type = OmegaConf.get_type(obj)
                    element_type = get_list_element_type(ref_type)
                    return ListConfig(
                        element_type=element_type, content=obj, parent=parent
                    )
                else:
                    if isinstance(obj, type):
                        raise ValidationError(
                            f"Input class '{obj.__name__}' is not a structured config. "
                            "did you forget to decorate it as a dataclass?"
                        )
                    else:
                        raise ValidationError(
                            f"Object of unsupported type: '{type(obj).__name__}'"
                        )
        except OmegaConfBaseException as e:
            format_and_raise(node=None, key=None, value=None, msg=str(e), cause=e)
            assert False

    @staticmethod
    def load(file_: Union[str, pathlib.Path, IO[Any]]) -> Union[DictConfig, ListConfig]:
        from ._utils import get_yaml_loader

        if isinstance(file_, (str, pathlib.Path)):
            with io.open(os.path.abspath(file_), "r", encoding="utf-8") as f:
                obj = yaml.load(f, Loader=get_yaml_loader())
                if obj is None:
                    res = OmegaConf.create()
                else:
                    res = OmegaConf.create(obj)
                assert isinstance(res, (ListConfig, DictConfig))
                return res
        elif getattr(file_, "read", None):
            obj = yaml.load(file_, Loader=get_yaml_loader())
            assert isinstance(
                obj, (list, dict, str)
            ), f"Invalid loaded object type : {type(obj).__name__}"
            return OmegaConf.create(obj)
        else:
            raise TypeError("Unexpected file type")

    @staticmethod
    def save(
        config: Any, f: Union[str, pathlib.Path, IO[Any]], resolve: bool = False
    ) -> None:
        """
        Save as configuration object to a file
        :param config: omegaconf.Config object (DictConfig or ListConfig).
        :param f: filename or file object
        :param resolve: True to save a resolved config (defaults to False)
        """
        if is_dataclass(config) or is_attr_class(config):
            config = OmegaConf.create(config)
        data = OmegaConf.to_yaml(config, resolve=resolve)
        if isinstance(f, (str, pathlib.Path)):
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
        return conf

    @staticmethod
    def merge(
        *others: Union[BaseContainer, Dict[str, Any], List[Any], Tuple[Any, ...], Any]
    ) -> Union[ListConfig, DictConfig]:
        """Merge a list of previously created configs into a single one"""
        assert len(others) > 0
        target = copy.deepcopy(others[0])
        target = _ensure_container(target)
        assert isinstance(target, (DictConfig, ListConfig))

        with flag_override(target, "readonly", False):
            target.merge_with(*others[1:])
            turned_readonly = target._get_flag("readonly") is True

        if turned_readonly:
            OmegaConf.set_readonly(target, True)

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
    def register_resolver(name: str, resolver: Resolver) -> None:
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

    @staticmethod
    def get_resolver(name: str) -> Optional[Callable[[Container, Any], Any]]:
        # noinspection PyProtectedMember
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
        return conf._metadata.resolver_cache

    @staticmethod
    def set_cache(conf: BaseContainer, cache: Dict[str, Any]) -> None:
        conf._metadata.resolver_cache = copy.deepcopy(cache)

    @staticmethod
    def clear_cache(conf: BaseContainer) -> None:
        OmegaConf.set_cache(conf, defaultdict(dict, {}))

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
        content = {key: value for key, value in conf.items_ex(resolve=False, keys=keys)}
        return DictConfig(content=content)

    @staticmethod
    def to_container(
        cfg: Any, resolve: bool = False, enum_to_str: bool = False
    ) -> Union[Dict[str, Any], List[Any], None, str]:
        """
        Resursively converts an OmegaConf config to a primitive container (dict or list).
        :param cfg: the config to convert
        :param resolve: True to resolve all values
        :param enum_to_str: True to convert Enum values to strings
        :return: A dict or a list representing this config as a primitive container.
        """
        assert isinstance(cfg, Container)
        # noinspection PyProtectedMember
        return BaseContainer._to_content(cfg, resolve=resolve, enum_to_str=enum_to_str)

    @staticmethod
    def is_missing(cfg: Any, key: Union[int, str]) -> bool:
        assert isinstance(cfg, Container)
        try:
            node = cfg._get_node(key)
            if node is None:
                return False
            return node._is_missing()
        except (UnsupportedInterpolationType, KeyError, AttributeError):
            return False

    @staticmethod
    def is_optional(obj: Any, key: Optional[Union[int, str]] = None) -> bool:
        if key is not None:
            assert isinstance(obj, Container)
            obj = obj._get_node(key)
        if isinstance(obj, Node):
            return obj._is_optional()
        else:
            return True

    @staticmethod
    def is_none(obj: Any, key: Optional[Union[int, str]] = None) -> bool:
        if key is not None:
            assert isinstance(obj, Container)
            obj = obj._get_node(key)
        if isinstance(obj, Node):
            return obj._is_none()
        else:
            return obj is None

    @staticmethod
    def is_interpolation(node: Any, key: Optional[Union[int, str]] = None) -> bool:
        if key is not None:
            assert isinstance(node, Container)
            target = node._get_node(key)
        else:
            target = node
        if target is not None:
            assert isinstance(target, Node)
            return target._is_interpolation()
        return False

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
        from . import Container

        return isinstance(obj, Container)

    @staticmethod
    def get_type(obj: Any, key: Optional[str] = None) -> Optional[Type[Any]]:
        if key is not None:
            c = obj._get_node(key)
        else:
            c = obj
        return OmegaConf._get_obj_type(c)

    @staticmethod
    def _get_obj_type(c: Any) -> Optional[Type[Any]]:
        if is_structured_config(c):
            return get_type_of(c)
        elif c is None:
            return None
        elif isinstance(c, DictConfig):
            if c._is_none():
                return None
            elif c._is_missing():
                return None
            else:
                if is_structured_config(c._metadata.object_type):
                    return c._metadata.object_type
                else:
                    return dict
        elif isinstance(c, ListConfig):
            return list
        elif isinstance(c, ValueNode):
            return type(c._value())
        elif isinstance(c, dict):
            return dict
        elif isinstance(c, (list, tuple)):
            return list
        else:
            return get_type_of(c)

    @staticmethod
    def select(cfg: Container, key: str, throw_on_missing: bool = False) -> Any:
        try:
            _root, _last_key, value = cfg._select_impl(
                key, throw_on_missing=throw_on_missing, throw_on_resolution_failure=True
            )
            if value is not None and value._is_missing():
                # throw_on_missing must be False
                return None

            return _get_value(value)
        except Exception as e:
            format_and_raise(node=cfg, key=key, value=None, cause=e, msg=str(e))

    @staticmethod
    def update(
        cfg: Container, key: str, value: Any = None, merge: Optional[bool] = None
    ) -> None:
        """
        Updates a dot separated key sequence to a value

        :param cfg: input config to update
        :param key: key to update (can be a dot separated path)
        :param value: value to set, if value if a list or a dict it will be merged or set
            depending on merge_config_values
        :param merge: If value is a dict or a list, True for merge, False for set.
            True to merge
            False to set
            None (default) : deprecation warning and default to False
        """

        if merge is None:
            warnings.warn(
                dedent(
                    """\
                update() merge flag is is not specified, defaulting to False.
                For more details, see https://github.com/omry/omegaconf/issues/367"""
                ),
                category=UserWarning,
                stacklevel=1,
            )
            merge = False

        split = key.split(".")
        root = cfg
        for i in range(len(split) - 1):
            k = split[i]
            # if next_root is a primitive (string, int etc) replace it with an empty map
            next_root, key_ = _select_one(root, k, throw_on_missing=False)
            if not isinstance(next_root, Container):
                root[key_] = {}
            root = root[key_]

        last = split[-1]

        assert isinstance(
            root, Container
        ), f"Unexpected type for root : {type(root).__name__}"

        last_key: Union[str, int] = last
        if isinstance(root, ListConfig):
            last_key = int(last)

        if merge and (OmegaConf.is_config(value) or is_primitive_container(value)):
            assert isinstance(root, BaseContainer)
            node = root._get_node(last_key)
            if OmegaConf.is_config(node):
                assert isinstance(node, BaseContainer)
                node.merge_with(value)
                return

        if OmegaConf.is_dict(root):
            assert isinstance(last_key, str)
            root.__setattr__(last_key, value)
        elif OmegaConf.is_list(root):
            assert isinstance(last_key, int)
            root.__setitem__(last_key, value)
        else:
            assert False

    @staticmethod
    def to_yaml(cfg: Any, *, resolve: bool = False, sort_keys: bool = False) -> str:
        """
        returns a yaml dump of this config object.
        :param cfg: Config object, Structured Config type or instance
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :param sort_keys: If True, will print dict keys in sorted order. default False.
        :return: A string containing the yaml representation.
        """
        cfg = _ensure_container(cfg)
        container = OmegaConf.to_container(cfg, resolve=resolve, enum_to_str=True)
        return yaml.dump(  # type: ignore
            container,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=sort_keys,
            Dumper=get_omega_conf_dumper(),
        )


# register all default resolvers
register_default_resolvers()


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


@contextmanager
def read_write(config: Node) -> Generator[Node, None, None]:
    prev_state = config._get_node_flag("readonly")
    try:
        OmegaConf.set_readonly(config, False)
        yield config
    finally:
        OmegaConf.set_readonly(config, prev_state)


@contextmanager
def open_dict(config: Container) -> Generator[Container, None, None]:
    prev_state = config._get_node_flag("struct")
    try:
        OmegaConf.set_struct(config, False)
        yield config
    finally:
        OmegaConf.set_struct(config, prev_state)


# === private === #


def _node_wrap(
    type_: Any,
    parent: Optional[BaseContainer],
    is_optional: bool,
    value: Any,
    key: Any,
    ref_type: Any = None,
) -> Node:
    node: Node
    is_dict = type(value) is dict or is_dict_annotation(type_)
    is_list = (
        type(value) in (list, tuple)
        or is_list_annotation(type_)
        or is_tuple_annotation(type_)
    )
    if is_dict:
        key_type, element_type = get_dict_key_value_types(type_)
        node = DictConfig(
            content=value,
            key=key,
            parent=parent,
            ref_type=type_,
            is_optional=is_optional,
            key_type=key_type,
            element_type=element_type,
        )
    elif is_list:
        element_type = get_list_element_type(type_)
        node = ListConfig(
            content=value,
            key=key,
            parent=parent,
            is_optional=is_optional,
            element_type=element_type,
            ref_type=ref_type,
        )
    elif is_structured_config(type_) or is_structured_config(value):
        key_type, element_type = get_dict_key_value_types(type_)
        node = DictConfig(
            ref_type=type_,
            is_optional=is_optional,
            content=value,
            key=key,
            parent=parent,
            key_type=key_type,
            element_type=element_type,
        )
    elif type_ == Any or type_ is None:
        node = AnyNode(value=value, key=key, parent=parent, is_optional=is_optional)
    elif issubclass(type_, Enum):
        node = EnumNode(
            enum_type=type_,
            value=value,
            key=key,
            parent=parent,
            is_optional=is_optional,
        )
    elif type_ == int:
        node = IntegerNode(value=value, key=key, parent=parent, is_optional=is_optional)
    elif type_ == float:
        node = FloatNode(value=value, key=key, parent=parent, is_optional=is_optional)
    elif type_ == bool:
        node = BooleanNode(value=value, key=key, parent=parent, is_optional=is_optional)
    elif type_ == str:
        node = StringNode(value=value, key=key, parent=parent, is_optional=is_optional)
    else:
        raise ValidationError(f"Unexpected object type : {type_str(type_)}")
    return node


def _maybe_wrap(
    ref_type: Any,
    key: Any,
    value: Any,
    is_optional: bool,
    parent: Optional[BaseContainer],
) -> Node:
    # if already a node, update key and parent and return as is.
    # NOTE: that this mutate the input node!
    if isinstance(value, Node):
        value._set_key(key)
        value._set_parent(parent)
        return value
    else:
        return _node_wrap(
            type_=ref_type,
            parent=parent,
            is_optional=is_optional,
            value=value,
            key=key,
            ref_type=ref_type,
        )


def _select_one(
    c: Container, key: str, throw_on_missing: bool, throw_on_type_error: bool = True
) -> Tuple[Optional[Node], Union[str, int]]:
    from .dictconfig import DictConfig
    from .listconfig import ListConfig

    ret_key: Union[str, int] = key
    assert isinstance(c, (DictConfig, ListConfig)), f"Unexpected type : {c}"
    if isinstance(c, DictConfig):
        assert isinstance(ret_key, str)
        val: Optional[Node] = c._get_node(ret_key, validate_access=False)
        if val is not None:
            if val._is_missing():
                if throw_on_missing:
                    raise MissingMandatoryValue(
                        f"Missing mandatory value : {c._get_full_key(ret_key)}"
                    )
                else:
                    return val, ret_key
        else:
            val = None
    elif isinstance(c, ListConfig):
        assert isinstance(ret_key, str)
        if not is_int(ret_key):
            if throw_on_type_error:
                raise TypeError(
                    f"Index '{ret_key}' ({type(ret_key).__name__}) is not an int"
                )
            else:
                val = None
        else:
            ret_key = int(ret_key)
            if ret_key < 0 or ret_key + 1 > len(c):
                val = None
            else:
                val = c._get_node(ret_key)
    else:
        assert False

    return val, ret_key
