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
    is_dict_annotation,
    is_dict_subclass,
    is_primitive_container,
    is_primitive_dict,
    is_structured_config,
)
from .base import Container, ContainerMetadata, Node
from .errors import MissingMandatoryValue, ReadonlyConfigError

DEFAULT_VALUE_MARKER: Any = str("__DEFAULT_VALUE_MARKER__")


class BaseContainer(Container, ABC):
    # static
    _resolvers: Dict[str, Any] = {}

    def __init__(self, parent: Optional["Container"], metadata: ContainerMetadata):
        super().__init__(
            parent=parent, metadata=metadata,
        )
        self.__dict__["_content"] = None

    def _resolve_with_default(
        self,
        key: Union[str, int, Enum],
        value: Any,
        default_value: Any = DEFAULT_VALUE_MARKER,
    ) -> Any:
        """returns the value with the specified key, like obj.key and obj['key']"""

        def is_mandatory_missing(val: Any) -> bool:
            return get_value_kind(val) == ValueKind.MANDATORY_MISSING  # type: ignore

        value = _get_value(value)

        if default_value is not DEFAULT_VALUE_MARKER and (
            value is None or is_mandatory_missing(value)
        ):
            value = default_value

        resolved = self._resolve_str_interpolation(
            key=key, value=value, throw_on_missing=True
        )
        if is_mandatory_missing(resolved):
            raise MissingMandatoryValue("Missing mandatory value: $FULL_KEY")
        resolved2 = _get_value(resolved)

        return resolved2

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

    @abstractmethod
    def __delitem__(self, key: Any) -> None:
        ...  # pragma: no cover

    def __len__(self) -> int:
        return self.__dict__["_content"].__len__()  # type: ignore

    def merge_with_cli(self) -> None:
        args_list = sys.argv[1:]
        self.merge_with_dotlist(args_list)

    def merge_with_dotlist(self, dotlist: List[str]) -> None:
        from omegaconf import OmegaConf

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

            OmegaConf.update(self, key, value)

    def update(self, key: str, value: Any = None) -> None:
        from omegaconf import OmegaConf

        warnings.warn(
            "update() is deprecated, use OmegaConf.update(). (Since 2.0)",
            category=DeprecationWarning,
        )

        return OmegaConf.update(self, key, value)

    def select(self, key: str, throw_on_missing: bool = False) -> Any:
        from omegaconf import OmegaConf

        warnings.warn(
            "select() is deprecated, use OmegaConf.select(). (Since 2.0)",
            category=DeprecationWarning,
        )

        return OmegaConf.select(self, key, throw_on_missing)

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

        assert False

    def pretty(self, resolve: bool = False, sort_keys: bool = False) -> str:
        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :param sort_keys: If True, will print dict keys in sorted order. default False.
        :return: A string containing the yaml representation.
        """
        from omegaconf import OmegaConf

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

        # disable object time during the merge
        type_backup = dest._metadata.object_type
        dest._metadata.object_type = None

        dest._validate_set_merge_impl(key=None, value=src, is_assign=False)
        for key, src_value in src.items_ex(resolve=False):
            dest_element_type = dest._metadata.element_type
            element_typed = dest_element_type not in (None, Any)
            if OmegaConf.is_missing(dest, key):
                if isinstance(src_value, DictConfig):
                    if OmegaConf.is_missing(dest, key):
                        dest[key] = src_value

            if (dest._get_node(key) is not None) or element_typed:
                dest_node = dest._get_node(key)
                if dest_node is None and element_typed:
                    dest[key] = DictConfig(content=dest_element_type, parent=dest)
                    dest_node = dest._get_node(key)

                if isinstance(dest_node, BaseContainer):
                    if isinstance(src_value, BaseContainer):
                        dest._validate_merge(key=key, value=src_value)
                        dest_node.merge_with(src_value)
                    else:
                        dest.__setitem__(key, src_value)
                else:
                    if isinstance(src_value, BaseContainer):
                        dest.__setitem__(key, src_value)
                    else:
                        assert isinstance(dest_node, ValueNode)
                        dest_node._set_value(src_value)
            else:
                dest[key] = src._get_node(key)

        if src_type is not Any and not is_primitive_dict(src_type):
            dest._metadata.object_type = src_type
        else:
            dest._metadata.object_type = type_backup

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
                raise TypeError("Cannot merge DictConfig with ListConfig")

        # recursively correct the parent hierarchy after the merge
        self._re_parent()

    # noinspection PyProtectedMember
    def _set_item_impl(self, key: Any, value: Any) -> None:
        from omegaconf.omegaconf import OmegaConf, _maybe_wrap

        from .nodes import ValueNode

        if isinstance(value, Node):
            try:
                old = value._key()
                value._set_key(key)
                self._validate_set(key, value)
            finally:
                value._set_key(old)
        else:
            self._validate_set(key, value)

        input_config = isinstance(value, Container)
        target_node_ref = self._get_node(key)
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
            if is_dict_annotation(self._metadata.ref_type) or (
                not is_primitive_dict(self._metadata.ref_type)
                and is_dict_subclass(self._metadata.ref_type)
            ):
                ref_type = self._metadata.element_type
            else:
                target = self._get_node(key)
                if target is None:
                    if is_structured_config(val):
                        ref_type = OmegaConf.get_type(val)
                    else:
                        # assignment
                        ref_type = OmegaConf.get_ref_type(val)
                else:
                    ref_type = OmegaConf.get_ref_type(target)
            return _maybe_wrap(
                ref_type=ref_type, key=key, value=val, is_optional=True, parent=self
            )

        def assign(value_key: Any, value_to_assign: Any) -> None:
            value_to_assign._set_parent(self)
            value_to_assign._set_key(value_key)
            self.__dict__["_content"][value_key] = value_to_assign

        if is_primitive_container(value):
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

    @staticmethod
    def _item_eq(
        c1: "BaseContainer",
        k1: Union[str, int],
        c2: "BaseContainer",
        k2: Union[str, int],
    ) -> bool:
        v1 = c1._get_node(k1)
        v2 = c2._get_node(k2)
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
    def _validate_get(self, key: Any, value: Any = None) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def _validate_set(self, key: Any, value: Any) -> None:
        ...  # pragma: no cover

    def _value(self) -> Any:
        return self.__dict__["_content"]

    def _get_full_key(self, key: Union[str, Enum, int, None]) -> str:
        from .listconfig import ListConfig
        from .omegaconf import _select_one

        def prepand(full_key: str, parent_type: Any, cur_type: Any, key: Any) -> str:
            if issubclass(parent_type, ListConfig):
                if full_key != "":
                    if issubclass(cur_type, ListConfig):
                        full_key = f"[{key}]{full_key}"
                    else:
                        full_key = f"[{key}].{full_key}"
                else:
                    full_key = f"[{key}]"
            else:
                if full_key == "":
                    full_key = key
                else:
                    if issubclass(cur_type, ListConfig):
                        full_key = f"{key}{full_key}"
                    else:
                        full_key = f"{key}.{full_key}"
            return full_key

        if key is not None and key != "":
            assert isinstance(self, Container)
            cur, _ = _select_one(
                c=self, key=str(key), throw_on_missing=False, throw_on_type_error=False,
            )
            if cur is None:
                cur = self
                full_key = prepand("", type(cur), None, key)
                if cur._key() is not None:
                    full_key = prepand(
                        full_key, type(cur._get_parent()), type(cur), cur._key()
                    )
            else:
                full_key = prepand("", type(cur._get_parent()), type(cur), cur._key())
        else:
            cur = self
            if cur._key() is None:
                return ""
            full_key = self._key()

        assert cur is not None
        while cur._get_parent() is not None:
            cur = cur._get_parent()
            assert cur is not None
            key = cur._key()
            if key is not None:
                full_key = prepand(
                    full_key, type(cur._get_parent()), type(cur), cur._key()
                )

        return full_key
