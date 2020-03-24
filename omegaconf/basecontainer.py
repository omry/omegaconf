import copy
import sys
import warnings
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from ._utils import (
    ValueKind,
    _get_value,
    _is_interpolation,
    get_value_kind,
    get_yaml_loader,
    is_primitive_container,
    is_structured_config,
)
from .base import Container, ContainerMetadata, Node
from .errors import MissingMandatoryValue, ReadonlyConfigError, ValidationError


class BaseContainer(Container, ABC):
    # static
    _resolvers: Dict[str, Any] = {}

    def __init__(self, parent: Optional["Container"], metadata: ContainerMetadata):
        super().__init__(
            parent=parent, metadata=metadata,
        )
        self.__dict__["_content"] = None

    def save(self, f: str) -> None:
        warnings.warn(
            "Use OmegaConf.save(config, filename) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        from omegaconf import OmegaConf

        OmegaConf.save(self, f)

    def _resolve_with_default(
        self, key: Union[str, int, Enum], value: Any, default_value: Any = None
    ) -> Any:
        """returns the value with the specified key, like obj.key and obj['key']"""

        def is_mandatory_missing(val: Any) -> bool:
            return get_value_kind(val) == ValueKind.MANDATORY_MISSING  # type: ignore

        value = _get_value(value)

        if default_value is not None and (value is None or is_mandatory_missing(value)):
            value = default_value

        value = self._resolve_str_interpolation(
            key=key, value=value, throw_on_missing=True
        )
        if is_mandatory_missing(value):
            raise MissingMandatoryValue(self._get_full_key(str(key)))

        value = _get_value(value)

        return value

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        if self.__dict__["_content"] is None:
            return "None"
        elif self._is_interpolation() or self._is_missing():
            v = self.__dict__["_content"]
            return f"'{v}'"
        else:
            return self.__dict__["_content"].__repr__()  # type: ignore

    # Support pickle
    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    # Support pickle
    def __setstate__(self, d: Dict[str, Any]) -> None:
        self.__dict__.update(d)

    def __delitem__(self, key: Union[str, int, slice]) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self._get_full_key(str(key)))
        del self.__dict__["_content"][key]

    def __len__(self) -> int:
        return self.__dict__["_content"].__len__()  # type: ignore

    def merge_with_cli(self) -> None:
        args_list = sys.argv[1:]
        self.merge_with_dotlist(args_list)

    def merge_with_dotlist(self, dotlist: List[str]) -> None:
        def fail() -> None:
            raise ValueError("Input list must be a list or a tuple of strings")

        if not isinstance(dotlist, (list, tuple)):
            fail()

        for arg in dotlist:
            if not isinstance(arg, str):
                fail()

            idx = arg.find("=")
            if idx == -1:
                key = arg
                value = None
            else:
                key = arg[0:idx]
                value = arg[idx + 1 :]
                value = yaml.load(value, Loader=get_yaml_loader())

            self.update_node(key, value)

    def update_node(self, key: str, value: Any = None) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig
        from .omegaconf import _select_one

        """Updates a dot separated key sequence to a value"""
        split = key.split(".")
        root = self
        for i in range(len(split) - 1):
            k = split[i]
            # if next_root is a primitive (string, int etc) replace it with an empty map
            next_root, key_ = _select_one(root, k)
            if not isinstance(next_root, Container):
                root[key_] = {}
            root = root[key_]

        last = split[-1]

        assert isinstance(
            root, Container
        ), f"Unexpected type for root : {type(root).__name__}"

        if isinstance(root, DictConfig):
            setattr(root, last, value)
        elif isinstance(root, ListConfig):
            idx = int(last)
            root[idx] = value

    def select(self, key: str) -> Any:
        _root, _last_key, value = self._select_impl(key)
        return _get_value(value)

    def _select_impl(
        self, key: str
    ) -> Tuple[Optional[Container], Optional[str], Optional[Node]]:
        """
        Select a value using dot separated key sequence
        :param key:
        :return:
        """
        from .omegaconf import _select_one

        if key == "":
            return self, "", self

        split = key.split(".")
        root: Optional[Container] = self
        for i in range(len(split) - 1):
            if root is None:
                break
            k = split[i]
            ret, _ = _select_one(root, k)
            assert ret is None or isinstance(ret, Container)
            root = ret

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = _select_one(root, last_key)
        if value is None:
            return root, last_key, value
        value = self._resolve_str_interpolation(
            key=last_key, value=value, throw_on_missing=False
        )
        return root, last_key, value

    def is_empty(self) -> bool:
        """return true if config is empty"""
        return len(self.__dict__["_content"]) == 0

    @staticmethod
    def _to_content(
        conf: Container, resolve: bool, enum_to_str: bool = False
    ) -> Union[Dict[str, Any], List[Any]]:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        def convert(val: Any) -> Any:
            if enum_to_str:
                if isinstance(val, Enum):
                    val = "{}.{}".format(type(val).__name__, val.name)

            return val

        assert isinstance(conf, Container)
        if isinstance(conf, DictConfig):
            retdict: Dict[str, Any] = {}
            for key, value in conf.items_ex(resolve=resolve):
                if isinstance(value, Container):
                    retdict[key] = BaseContainer._to_content(
                        value, resolve=resolve, enum_to_str=enum_to_str
                    )
                else:
                    retdict[key] = convert(value)
            return retdict
        elif isinstance(conf, ListConfig):
            retlist: List[Any] = []
            for index, item in enumerate(conf):
                if resolve:
                    item = conf[index]
                item = convert(item)
                if isinstance(item, Container):
                    item = BaseContainer._to_content(
                        item, resolve=resolve, enum_to_str=enum_to_str
                    )
                retlist.append(item)
            return retlist

        assert False  # pragma: no cover

    def to_container(self, resolve: bool = False) -> Union[Dict[str, Any], List[Any]]:
        warnings.warn(
            "Use OmegaConf.to_container(config, resolve) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        return BaseContainer._to_content(self, resolve)

    def pretty(self, resolve: bool = False, sort_keys: bool = False) -> str:
        from omegaconf import OmegaConf

        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :param sort_keys: If True, will print dict keys in sorted order. default False.
        :return: A string containing the yaml representation.
        """
        container = OmegaConf.to_container(self, resolve=resolve, enum_to_str=True)
        return yaml.dump(  # type: ignore
            container, default_flow_style=False, allow_unicode=True, sort_keys=sort_keys
        )

    @staticmethod
    def _map_merge(dest: "BaseContainer", src: "BaseContainer") -> None:
        """merge src into dest and return a new copy, does not modified input"""
        from omegaconf import OmegaConf

        from .dictconfig import DictConfig
        from .nodes import ValueNode

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)
        src = copy.deepcopy(src)
        src_type = src._metadata.object_type
        dest_type = dest._metadata.object_type

        if src_type is not None and src_type is not dest_type:
            prototype = DictConfig(annotated_type=src_type, content=src_type,)

            dest.__dict__["_content"] = copy.deepcopy(prototype.__dict__["_content"])
            dest.__dict__["_metadata"] = copy.deepcopy(prototype._metadata)

        for key, value in src.items_ex(resolve=False):

            dest_element_type = dest._metadata.element_type
            typed = dest_element_type not in (None, Any)
            if OmegaConf.is_missing(dest, key):
                if isinstance(value, DictConfig):
                    if OmegaConf.is_missing(src, key):
                        dest[key] = DictConfig(content="???")
                    else:
                        dest[key] = {}
            if (dest.get_node(key) is not None) or typed:
                dest_node = dest.get_node(key)
                if dest_node is None and typed:
                    dest[key] = DictConfig(content=dest_element_type, parent=dest)
                    dest_node = dest.get_node(key)

                if isinstance(dest_node, BaseContainer):
                    if isinstance(value, BaseContainer):
                        dest._validate_set(key=key, value=value)
                        dest_node.merge_with(value)
                    else:
                        dest.__setitem__(key, value)
                else:
                    if isinstance(value, BaseContainer):
                        dest.__setitem__(key, value)
                    else:
                        assert isinstance(dest_node, ValueNode)
                        dest_node._set_value(value)
            else:
                dest[key] = src.get_node(key)

    def merge_with(
        self,
        *others: Union["BaseContainer", Dict[str, Any], List[Any], Tuple[Any], Any],
    ) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig
        from .omegaconf import OmegaConf

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if is_primitive_container(other) or is_structured_config(other):
                other = OmegaConf.create(other)

            if other is None:
                raise ValueError("Cannot merge with a None config")
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                BaseContainer._map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                if self._get_flag("readonly"):
                    raise ReadonlyConfigError(self._get_full_key(""))
                self.__dict__["_content"].clear()
                for item in other:
                    self.append(item)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        # recursively correct the parent hierarchy after the merge
        self._re_parent()

    # noinspection PyProtectedMember
    def _set_item_impl(self, key: Any, value: Any) -> None:
        from omegaconf.omegaconf import OmegaConf, _maybe_wrap

        from .nodes import ValueNode

        self._validate_get(key)
        self._validate_set(key, value)

        must_wrap = is_primitive_container(value)
        input_config = isinstance(value, Container)
        target_node_ref = self.get_node(key)
        special_value = value is None or value == "???"
        should_set_value = (
            target_node_ref is not None
            and isinstance(target_node_ref, Container)
            and special_value
        )

        input_node = isinstance(value, ValueNode)
        if isinstance(self.__dict__["_content"], dict):
            target_node = key in self.__dict__["_content"] and isinstance(
                target_node_ref, ValueNode
            )

        elif isinstance(self.__dict__["_content"], list):
            target_node = isinstance(target_node_ref, ValueNode)

        def wrap(key: Any, val: Any) -> Node:
            if is_structured_config(val):
                type_ = OmegaConf.get_type(val)
            else:
                type_ = self._metadata.element_type
            return _maybe_wrap(
                annotated_type=type_, key=key, value=val, is_optional=True, parent=self,
            )

        def assign(value_key: Any, value_to_assign: Any) -> None:
            value_to_assign._set_parent(self)
            value_to_assign._set_key(value_key)
            self.__dict__["_content"][value_key] = value_to_assign

        try:
            if must_wrap:
                self.__dict__["_content"][key] = wrap(key, value)
            elif input_node and target_node:
                # both nodes, replace existing node with new one
                assign(key, value)
            elif not input_node and target_node:
                # input is not node, can be primitive or config
                if input_config:
                    assign(key, value)
                else:
                    self.__dict__["_content"][key]._set_value(value)
            elif input_node and not target_node:
                # target must be config, replace target with input node
                assign(key, value)
            elif not input_node and not target_node:
                if should_set_value:
                    self.__dict__["_content"][key]._set_value(value)
                elif input_config:
                    assign(key, value)
                else:
                    self.__dict__["_content"][key] = wrap(key, value)
        except ValidationError as ve:
            import sys

            raise type(ve)(
                f"Error setting '{self._get_full_key(str(key))} = {value}' : {ve}"
            ).with_traceback(sys.exc_info()[2]) from None

    @staticmethod
    def _item_eq(
        c1: "BaseContainer",
        k1: Union[str, int],
        c2: "BaseContainer",
        k2: Union[str, int],
    ) -> bool:
        v1 = c1.get_node(k1)
        v2 = c2.get_node(k2)
        v1_kind = get_value_kind(v1)
        v2_kind = get_value_kind(v2)

        if v1_kind == v2_kind and v1_kind == ValueKind.MANDATORY_MISSING:
            return True

        v1 = _get_value(v1)
        v2 = _get_value(v2)

        # special case for two interpolations. just compare them literally.
        # This is helping in cases where the two interpolations are not resolvable
        # but the objects are still considered equal.
        if v1_kind in (
            ValueKind.STR_INTERPOLATION,
            ValueKind.INTERPOLATION,
        ) and v2_kind in (ValueKind.STR_INTERPOLATION, ValueKind.INTERPOLATION):
            return True
        if isinstance(v1, str):
            v1 = c1._resolve_str_interpolation(key=k1, value=v1, throw_on_missing=False)
        if isinstance(v2, str):
            v2 = c2._resolve_str_interpolation(key=k2, value=v2, throw_on_missing=False)

        if isinstance(v1, BaseContainer) and isinstance(v2, BaseContainer):
            if not BaseContainer._config_eq(v1, v2):
                return False
        return v1 == v2

    @staticmethod
    def _config_eq(c1: "BaseContainer", c2: "BaseContainer") -> bool:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        assert isinstance(c1, Container)
        assert isinstance(c2, Container)
        if isinstance(c1, DictConfig) and isinstance(c2, DictConfig):
            return DictConfig._dict_conf_eq(c1, c2)
        if isinstance(c1, ListConfig) and isinstance(c2, ListConfig):
            return ListConfig._list_eq(c1, c2)
        # if type does not match objects are different
        return False

    def _re_parent(self) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        # update parents of first level Config nodes to self

        if isinstance(self, Container) and not self._is_missing():
            if isinstance(self, DictConfig):
                if (
                    self.__dict__["_content"] is not None
                    and not self._is_interpolation()
                ):
                    for _key, value in self.__dict__["_content"].items():
                        value._set_parent(self)
                        BaseContainer._re_parent(value)
            elif isinstance(self, ListConfig):
                for item in self.__dict__["_content"]:
                    item._set_parent(self)
                    BaseContainer._re_parent(item)

    def _is_none(self) -> bool:
        return self.__dict__["_content"] is None

    def _is_missing(self) -> bool:
        try:
            self._dereference_node(throw_on_missing=True)
            return False
        except MissingMandatoryValue:
            ret = True

        assert isinstance(ret, bool)
        return ret

    def _is_optional(self) -> bool:
        return self.__dict__["_metadata"].optional is True

    def _is_interpolation(self) -> bool:
        return _is_interpolation(self.__dict__["_content"])

    @abstractmethod
    def _validate_get(self, key: Any) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def _validate_set(self, key: Any, value: Any) -> None:
        ...  # pragma: no cover

    def _value(self) -> Any:
        return self.__dict__["_content"]
