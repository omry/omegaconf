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
    is_primitive_dict,
    is_structured_config,
)
from .base import Container, ContainerMetadata, Node
from .errors import MissingMandatoryValue, ReadonlyConfigError, ValidationError

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
        has_default = default_value is not DEFAULT_VALUE_MARKER
        if has_default and (value is None or is_mandatory_missing(value)):
            return default_value

        resolved = self._resolve_interpolation(
            key=key,
            value=value,
            throw_on_missing=not has_default,
            throw_on_resolution_failure=not has_default,
        )
        if resolved is None and has_default:
            return default_value

        if is_mandatory_missing(resolved):
            if has_default:
                return default_value
            else:
                raise MissingMandatoryValue("Missing mandatory value: $FULL_KEY")

        return _get_value(resolved)

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
        ...

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

    def select(self, key: str, throw_on_missing: bool = False) -> Any:
        from omegaconf import OmegaConf

        warnings.warn(
            "select() is deprecated, use OmegaConf.select(). (Since 2.0)",
            category=UserWarning,
            stacklevel=2,
        )

        return OmegaConf.select(self, key, throw_on_missing)

    def update_node(self, key: str, value: Any = None) -> None:
        from omegaconf import OmegaConf

        warnings.warn(
            "update_node() is deprecated, use OmegaConf.update(). (Since 2.0)",
            category=UserWarning,
            stacklevel=2,
        )

        OmegaConf.update(self, key, value)

    def is_empty(self) -> bool:
        """return true if config is empty"""
        return len(self.__dict__["_content"]) == 0

    @staticmethod
    def _to_content(
        conf: Container, resolve: bool, enum_to_str: bool = False
    ) -> Union[None, str, Dict[str, Any], List[Any]]:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        def convert(val: Node) -> Any:
            value = val._value()
            if enum_to_str and isinstance(value, Enum):
                value = f"{value.name}"

            return value

        assert isinstance(conf, Container)
        if conf._is_none():
            return None
        elif conf._is_interpolation() and not resolve:
            inter = conf._value()
            assert isinstance(inter, str)
            return inter
        elif conf._is_missing():
            return "???"
        elif isinstance(conf, DictConfig):
            retdict: Dict[str, Any] = {}
            for key in conf.keys():
                node = conf._get_node(key)
                assert node is not None
                if resolve:
                    node = node._dereference_node(
                        throw_on_missing=False, throw_on_resolution_failure=True
                    )

                assert node is not None
                if isinstance(node, Container):
                    retdict[key] = BaseContainer._to_content(
                        node, resolve=resolve, enum_to_str=enum_to_str
                    )
                else:
                    retdict[key] = convert(node)
            return retdict
        elif isinstance(conf, ListConfig):
            retlist: List[Any] = []
            for index in range(len(conf)):
                node = conf._get_node(index)
                assert node is not None
                if resolve:
                    node = node._dereference_node(
                        throw_on_missing=False, throw_on_resolution_failure=True
                    )
                assert node is not None
                if isinstance(node, Container):
                    item = BaseContainer._to_content(
                        node, resolve=resolve, enum_to_str=enum_to_str
                    )
                    retlist.append(item)
                else:
                    retlist.append(convert(node))

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
        src_type = src._metadata.object_type

        dest._validate_set_merge_impl(key=None, value=src, is_assign=False)
        for key, src_value in src.items_ex(resolve=False):
            if OmegaConf.is_missing(dest, key):
                if isinstance(src_value, DictConfig):
                    if OmegaConf.is_missing(dest, key):
                        dest[key] = src_value

            dest_node = dest._get_node(key, validate_access=False)
            if dest_node is not None:
                if dest_node._is_interpolation():
                    target_node = dest_node._dereference_node(
                        throw_on_resolution_failure=False
                    )
                    if isinstance(target_node, Container):
                        dest[key] = target_node
                        dest_node = dest._get_node(key)

            if is_structured_config(dest._metadata.element_type):
                dest[key] = DictConfig(content=dest._metadata.element_type, parent=dest)
                dest_node = dest._get_node(key)

            if dest_node is not None:
                if isinstance(dest_node, BaseContainer):
                    if isinstance(src_value, BaseContainer):
                        dest._validate_merge(key=key, value=src_value)
                        dest_node._merge_with(src_value)
                    else:
                        dest.__setitem__(key, src_value)
                else:
                    if isinstance(src_value, BaseContainer):
                        dest.__setitem__(key, src_value)
                    else:
                        assert isinstance(dest_node, ValueNode)
                        try:
                            dest_node._set_value(src_value)
                        except ValidationError as e:
                            dest._format_and_raise(key=key, value=src_value, cause=e)
            else:
                dest[key] = src._get_node(key)

        if src_type is not None and not is_primitive_dict(src_type):
            dest._metadata.object_type = src_type

    def merge_with(
        self,
        *others: Union["BaseContainer", Dict[str, Any], List[Any], Tuple[Any], Any],
    ) -> None:
        try:
            self._merge_with(*others)
        except Exception as e:
            self._format_and_raise(key=None, value=None, cause=e)

    def _merge_with(
        self,
        *others: Union["BaseContainer", Dict[str, Any], List[Any], Tuple[Any], Any],
    ) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig
        from .omegaconf import OmegaConf

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if other is None:
                raise ValueError("Cannot merge with a None config")
            if is_primitive_container(other):
                assert isinstance(other, (list, dict))
                other = OmegaConf.create(other)
            elif is_structured_config(other):
                other = OmegaConf.structured(other)
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                BaseContainer._map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                if self._get_flag("readonly"):
                    raise ReadonlyConfigError(self._get_full_key(""))
                if self._is_none() or self._is_missing() or self._is_interpolation():
                    self.__dict__["_content"] = []
                else:
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
            is_optional = True
            if not is_structured_config(val):
                ref_type = self._metadata.element_type
            else:
                target = self._get_node(key)
                if target is None:
                    if is_structured_config(val):
                        ref_type = OmegaConf.get_type(val)
                else:
                    is_optional = target._is_optional()
                    ref_type = target._metadata.ref_type
            return _maybe_wrap(
                ref_type=ref_type,
                key=key,
                value=val,
                is_optional=is_optional,
                parent=self,
            )

        def assign(value_key: Any, value_to_assign: Any) -> None:
            v = copy.deepcopy(value_to_assign)
            v._set_parent(self)
            v._set_key(value_key)
            self.__dict__["_content"][value_key] = v

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
        c1: Container, k1: Union[str, int], c2: Container, k2: Union[str, int],
    ) -> bool:
        v1 = c1._get_node(k1)
        v2 = c2._get_node(k2)
        assert v1 is not None and v2 is not None

        if v1._is_none() and v2._is_none():
            return True

        if v1._is_missing() and v2._is_missing():
            return True

        v1_inter = v1._is_interpolation()
        v2_inter = v2._is_interpolation()
        dv1: Optional[Node] = v1
        dv2: Optional[Node] = v2

        if v1_inter:
            dv1 = v1._dereference_node(
                throw_on_missing=False, throw_on_resolution_failure=False
            )
        if v2_inter:
            dv2 = v2._dereference_node(
                throw_on_missing=False, throw_on_resolution_failure=False
            )

        if v1_inter and v2_inter:
            if dv1 is None or dv2 is None:
                return v1 == v2
            else:
                # both are not none, if both are containers compare as container
                if isinstance(dv1, Container) and isinstance(dv2, Container):
                    if dv1 != dv2:
                        return False
                dv1 = _get_value(dv1)
                dv2 = _get_value(dv2)
                return dv1 == dv2
        elif not v1_inter and not v2_inter:
            v1 = _get_value(v1)
            v2 = _get_value(v2)
            return v1 == v2
        else:
            dv1 = _get_value(dv1)
            dv2 = _get_value(dv2)
            return dv1 == dv2

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
        ...

    @abstractmethod
    def _validate_set(self, key: Any, value: Any) -> None:
        ...

    def _value(self) -> Any:
        return self.__dict__["_content"]

    def _get_full_key(
        self, key: Union[str, Enum, int, slice, None], disable_warning: bool = False
    ) -> str:
        from .listconfig import ListConfig
        from .omegaconf import _select_one

        if not isinstance(key, (int, str, Enum, slice, type(None))):
            return ""

        def _slice_to_str(x: slice) -> str:
            if x.step is not None:
                return f"{x.start}:{x.stop}:{x.step}"
            else:
                return f"{x.start}:{x.stop}"

        def prepand(full_key: str, parent_type: Any, cur_type: Any, key: Any) -> str:
            if isinstance(key, slice):
                key = _slice_to_str(key)
            elif isinstance(key, Enum):
                key = key.name

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
                c=self,
                key=str(key),
                throw_on_missing=False,
                throw_on_type_error=False,
                disable_warning=disable_warning,
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
