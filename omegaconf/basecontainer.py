import copy
import sys
import warnings
from abc import ABC, abstractmethod
from enum import Enum
from textwrap import dedent
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple, Union

import yaml

from ._utils import (
    ValueKind,
    _ensure_container,
    _get_value,
    _is_interpolation,
    _resolve_optional,
    get_ref_type,
    get_structured_config_data,
    get_value_kind,
    get_yaml_loader,
    is_container_annotation,
    is_dict_annotation,
    is_list_annotation,
    is_primitive_dict,
    is_primitive_type,
    is_structured_config,
)
from .base import Container, ContainerMetadata, DictKeyType, Node, SCMode
from .errors import MissingMandatoryValue, ReadonlyConfigError, ValidationError

if TYPE_CHECKING:
    from .dictconfig import DictConfig  # pragma: no cover

DEFAULT_VALUE_MARKER: Any = str("__DEFAULT_VALUE_MARKER__")


class BaseContainer(Container, ABC):
    # static
    _resolvers: Dict[str, Any] = {}

    def __init__(self, parent: Optional["Container"], metadata: ContainerMetadata):
        super().__init__(parent=parent, metadata=metadata)
        self.__dict__["_content"] = None

    def _resolve_with_default(
        self,
        key: Union[DictKeyType, int],
        value: Any,
        default_value: Any = DEFAULT_VALUE_MARKER,
    ) -> Any:
        """returns the value with the specified key, like obj.key and obj['key']"""

        def is_mandatory_missing(val: Any) -> bool:
            return bool(get_value_kind(val) == ValueKind.MANDATORY_MISSING)

        val = _get_value(value)
        has_default = default_value is not DEFAULT_VALUE_MARKER
        if has_default and (val is None or is_mandatory_missing(val)):
            return default_value

        resolved = self._maybe_resolve_interpolation(
            parent=self,
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
        dict_copy = copy.copy(self.__dict__)

        # no need to serialize the flags cache, it can be re-constructed later
        dict_copy.pop("_flags_cache", None)

        dict_copy["_metadata"] = copy.copy(dict_copy["_metadata"])
        ref_type = self._metadata.ref_type
        if is_container_annotation(ref_type):
            if is_dict_annotation(ref_type):
                dict_copy["_metadata"].ref_type = Dict
            elif is_list_annotation(ref_type):
                dict_copy["_metadata"].ref_type = List
            else:
                assert False
        return dict_copy

    # Support pickle
    def __setstate__(self, d: Dict[str, Any]) -> None:
        from omegaconf import DictConfig
        from omegaconf._utils import is_generic_dict, is_generic_list

        if isinstance(self, DictConfig):
            key_type = d["_metadata"].key_type
        element_type = d["_metadata"].element_type
        ref_type = d["_metadata"].ref_type
        if is_container_annotation(ref_type):
            if is_generic_dict(ref_type):
                d["_metadata"].ref_type = Dict[key_type, element_type]  # type: ignore
            elif is_generic_list(ref_type):
                d["_metadata"].ref_type = List[element_type]  # type: ignore
            else:
                assert False

        d["_flags_cache"] = None
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

            OmegaConf.update(self, key, value, merge=True)

    def select(self, key: str, throw_on_missing: bool = False) -> Any:
        from omegaconf import OmegaConf

        warnings.warn(
            "select() is deprecated, use OmegaConf.select(). (Since 2.0)",
            category=UserWarning,
            stacklevel=2,
        )

        return OmegaConf.select(self, key, throw_on_missing=throw_on_missing)

    def update_node(self, key: str, value: Any = None) -> None:
        from omegaconf import OmegaConf

        warnings.warn(
            "update_node() is deprecated, use OmegaConf.update(). (Since 2.0)",
            category=UserWarning,
            stacklevel=2,
        )

        OmegaConf.update(self, key, value, merge=False)

    def is_empty(self) -> bool:
        """return true if config is empty"""
        return len(self.__dict__["_content"]) == 0

    @staticmethod
    def _to_content(
        conf: Container,
        resolve: bool,
        enum_to_str: bool = False,
        structured_config_mode: SCMode = SCMode.DICT,
    ) -> Union[None, Any, str, Dict[DictKeyType, Any], List[Any]]:
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
            if (
                conf._metadata.object_type is not None
                and structured_config_mode == SCMode.DICT_CONFIG
            ):
                return conf

            retdict: Dict[str, Any] = {}
            for key in conf.keys():
                node = conf._get_node(key)
                assert isinstance(node, Node)
                if resolve:
                    node = node._dereference_node(
                        throw_on_missing=False, throw_on_resolution_failure=True
                    )

                assert node is not None
                if enum_to_str and isinstance(key, Enum):
                    key = f"{key.name}"
                if isinstance(node, Container):
                    retdict[key] = BaseContainer._to_content(
                        node,
                        resolve=resolve,
                        enum_to_str=enum_to_str,
                        structured_config_mode=structured_config_mode,
                    )
                else:
                    retdict[key] = convert(node)
            return retdict
        elif isinstance(conf, ListConfig):
            retlist: List[Any] = []
            for index in range(len(conf)):
                node = conf._get_node(index)
                assert isinstance(node, Node)
                if resolve:
                    node = node._dereference_node(
                        throw_on_missing=False, throw_on_resolution_failure=True
                    )
                assert node is not None
                if isinstance(node, Container):
                    item = BaseContainer._to_content(
                        node,
                        resolve=resolve,
                        enum_to_str=enum_to_str,
                        structured_config_mode=structured_config_mode,
                    )
                    retlist.append(item)
                else:
                    retlist.append(convert(node))

            return retlist

        assert False

    def pretty(self, resolve: bool = False, sort_keys: bool = False) -> str:
        from omegaconf import OmegaConf

        warnings.warn(
            dedent(
                """\
            cfg.pretty() is deprecated and will be removed in a future version.
            Use OmegaConf.to_yaml(cfg)
            """
            ),
            category=UserWarning,
        )

        return OmegaConf.to_yaml(self, resolve=resolve, sort_keys=sort_keys)

    @staticmethod
    def _map_merge(dest: "BaseContainer", src: "BaseContainer") -> None:
        """merge src into dest and return a new copy, does not modified input"""
        from omegaconf import AnyNode, DictConfig, OmegaConf, ValueNode

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)
        src_type = src._metadata.object_type
        src_ref_type = get_ref_type(src)
        assert src_ref_type is not None

        # If source DictConfig is:
        #  - an interpolation => set the destination DictConfig to be the same interpolation
        #  - None => set the destination DictConfig to None
        if src._is_interpolation() or src._is_none():
            dest._set_value(src._value())
            _update_types(node=dest, ref_type=src_ref_type, object_type=src_type)
            return

        dest._validate_merge(value=src)

        def expand(node: Container) -> None:
            rt = node._metadata.ref_type
            val: Any
            if rt is not Any:
                if is_dict_annotation(rt):
                    val = {}
                elif is_list_annotation(rt):
                    val = []
                else:
                    val = rt
            elif isinstance(node, DictConfig):
                val = {}
            else:
                assert False

            node._set_value(val)

        if (
            src._is_missing()
            and not dest._is_missing()
            and is_structured_config(src_ref_type)
        ):
            # Replace `src` with a prototype of its corresponding structured config
            # whose fields are all missing (to avoid overwriting fields in `dest`).
            src = _create_structured_with_missing_fields(
                ref_type=src_ref_type, object_type=src_type
            )

        if (dest._is_interpolation() or dest._is_missing()) and not src._is_missing():
            expand(dest)

        for key, src_value in src.items_ex(resolve=False):
            src_node = src._get_node(key, validate_access=False)
            dest_node = dest._get_node(key, validate_access=False)
            assert src_node is None or isinstance(src_node, Node)
            assert dest_node is None or isinstance(dest_node, Node)

            if isinstance(dest_node, DictConfig):
                dest_node._validate_merge(value=src_node)

            missing_src_value = _is_missing_value(src_value)

            if (
                isinstance(dest_node, Container)
                and OmegaConf.is_none(dest, key)
                and not missing_src_value
                and not OmegaConf.is_none(src_value)
            ):
                expand(dest_node)

            if dest_node is not None and dest_node._is_interpolation():
                target_node = dest_node._dereference_node(
                    throw_on_resolution_failure=False
                )
                if isinstance(target_node, Container):
                    dest[key] = target_node
                    dest_node = dest._get_node(key)

            if (
                dest_node is None
                and is_structured_config(dest._metadata.element_type)
                and not missing_src_value
            ):
                # merging into a new node. Use element_type as a base
                dest[key] = DictConfig(content=dest._metadata.element_type, parent=dest)
                dest_node = dest._get_node(key)

            if dest_node is not None:
                if isinstance(dest_node, BaseContainer):
                    if isinstance(src_value, BaseContainer):
                        dest_node._merge_with(src_value)
                    elif not missing_src_value:
                        dest.__setitem__(key, src_value)
                else:
                    if isinstance(src_value, BaseContainer):
                        dest.__setitem__(key, src_value)
                    else:
                        assert isinstance(dest_node, ValueNode)
                        assert isinstance(src_node, ValueNode)
                        # Compare to literal missing, ignoring interpolation
                        src_node_missing = src_value == "???"
                        try:
                            if isinstance(dest_node, AnyNode):
                                if src_node_missing:
                                    node = copy.copy(src_node)
                                    # if src node is missing, use the value from the dest_node,
                                    # but validate it against the type of the src node before assigment
                                    node._set_value(dest_node._value())
                                else:
                                    node = src_node
                                dest.__setitem__(key, node)
                            else:
                                if not src_node_missing:
                                    dest_node._set_value(src_value)

                        except (ValidationError, ReadonlyConfigError) as e:
                            dest._format_and_raise(key=key, value=src_value, cause=e)
            else:
                from omegaconf import open_dict

                if is_structured_config(src_type):
                    # verified to be compatible above in _validate_merge
                    with open_dict(dest):
                        dest[key] = src._get_node(key)
                else:
                    dest[key] = src._get_node(key)

        _update_types(node=dest, ref_type=src_ref_type, object_type=src_type)

        # explicit flags on the source config are replacing the flag values in the destination
        flags = src._metadata.flags
        assert flags is not None
        for flag, value in flags.items():
            if value is not None:
                dest._set_flag(flag, value)

    @staticmethod
    def _list_merge(dest: Any, src: Any) -> None:
        from omegaconf import DictConfig, ListConfig, OmegaConf

        assert isinstance(dest, ListConfig)
        assert isinstance(src, ListConfig)

        if src._is_interpolation():
            dest._set_value(src._value())
        elif src._is_none():
            dest._set_value(None)
        elif src._is_missing():
            # do not change dest if src is MISSING.
            if dest._metadata.element_type is Any:
                dest._metadata.element_type = src._metadata.element_type
        else:
            temp_target = ListConfig(content=[], parent=dest._get_parent())
            temp_target.__dict__["_metadata"] = copy.deepcopy(
                dest.__dict__["_metadata"]
            )
            et = dest._metadata.element_type
            if is_structured_config(et):
                prototype = OmegaConf.structured(et)
                for item in src._iter_ex(resolve=False):
                    if isinstance(item, DictConfig):
                        item = OmegaConf.merge(prototype, item)
                    temp_target.append(item)
            else:
                for item in src._iter_ex(resolve=False):
                    temp_target.append(item)

            dest.__dict__["_content"] = temp_target.__dict__["_content"]

        # explicit flags on the source config are replacing the flag values in the destination
        flags = src._metadata.flags
        assert flags is not None
        for flag, value in flags.items():
            if value is not None:
                dest._set_flag(flag, value)

    def merge_with(
        self,
        *others: Union[
            "BaseContainer", Dict[str, Any], List[Any], Tuple[Any, ...], Any
        ],
    ) -> None:
        try:
            self._merge_with(*others)
        except Exception as e:
            self._format_and_raise(key=None, value=None, cause=e)

    def _merge_with(
        self,
        *others: Union[
            "BaseContainer", Dict[str, Any], List[Any], Tuple[Any, ...], Any
        ],
    ) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if other is None:
                raise ValueError("Cannot merge with a None config")

            my_flags = {}
            if self._get_flag("allow_objects") is True:
                my_flags = {"allow_objects": True}
            other = _ensure_container(other, flags=my_flags)

            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                BaseContainer._map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                BaseContainer._list_merge(self, other)
            else:
                raise TypeError("Cannot merge DictConfig with ListConfig")

        # recursively correct the parent hierarchy after the merge
        self._re_parent()

    # noinspection PyProtectedMember
    def _set_item_impl(self, key: Any, value: Any) -> None:
        """
        Changes the value of the node key with the desired value. If the node key doesn't
        exist it creates a new one.
        """
        from omegaconf.omegaconf import _maybe_wrap

        from .nodes import AnyNode, ValueNode

        if isinstance(value, Node):
            do_deepcopy = not self._get_flag("no_deepcopy_set_nodes")
            if not do_deepcopy and isinstance(value, Container):
                # if value is from the same config, perform a deepcopy no matter what.
                if self._get_root() is value._get_root():
                    do_deepcopy = True

            if do_deepcopy:
                value = copy.deepcopy(value)
            value._set_parent(None)

            try:
                old = value._key()
                value._set_key(key)
                self._validate_set(key, value)
            finally:
                value._set_key(old)
        else:
            self._validate_set(key, value)

        if self._get_flag("readonly"):
            raise ReadonlyConfigError("Cannot change read-only config container")

        input_config = isinstance(value, Container)
        target_node_ref = self._get_node(key)
        special_value = value is None or value == "???"

        input_node = isinstance(value, ValueNode)
        if isinstance(self.__dict__["_content"], dict):
            target_node = key in self.__dict__["_content"] and isinstance(
                target_node_ref, ValueNode
            )

        elif isinstance(self.__dict__["_content"], list):
            target_node = isinstance(target_node_ref, ValueNode)
        # We use set_value if:
        # 1. Target node is a container and the value is MISSING or None
        # 2. Target node is a container and has an explicit ref_type
        # 3. If the target is a NodeValue then it should set his value.
        #    Furthermore if it's an AnyNode it should wrap when the input is
        # a container and set when the input is an compatible type(primitive type).

        should_set_value = target_node_ref is not None and (
            (
                isinstance(target_node_ref, Container)
                and (special_value or target_node_ref._has_ref_type())
            )
            or (target_node and not isinstance(target_node_ref, AnyNode))
            or (isinstance(target_node_ref, AnyNode) and is_primitive_type(value))
        )

        def wrap(key: Any, val: Any) -> Node:
            is_optional = True
            if not is_structured_config(val):
                ref_type = self._metadata.element_type
            else:
                target = self._get_node(key)
                if target is None:
                    if is_structured_config(val):
                        ref_type = self._metadata.element_type
                else:
                    assert isinstance(target, Node)
                    is_optional = target._is_optional()
                    ref_type = target._metadata.ref_type
            return _maybe_wrap(
                ref_type=ref_type,
                key=key,
                value=val,
                is_optional=is_optional,
                parent=self,
            )

        def assign(value_key: Any, val: ValueNode) -> None:
            assert val._get_parent() is None
            v = val
            v._set_parent(self)
            v._set_key(value_key)
            self.__dict__["_content"][value_key] = v

        if input_node and target_node:
            # both nodes, replace existing node with new one
            assign(key, value)
        elif not input_node and target_node:
            # input is not node, can be primitive or config
            if should_set_value:
                self.__dict__["_content"][key]._set_value(value)
            elif input_config:
                assign(key, value)
            else:
                self.__dict__["_content"][key] = wrap(key, value)
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
        c1: Container,
        k1: Union[DictKeyType, int],
        c2: Container,
        k2: Union[DictKeyType, int],
    ) -> bool:
        v1 = c1._get_node(k1)
        v2 = c2._get_node(k2)
        assert v1 is not None and v2 is not None

        assert isinstance(v1, Node)
        assert isinstance(v2, Node)

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
            ret = v1 == v2
            assert isinstance(ret, bool)
            return ret
        else:
            dv1 = _get_value(dv1)
            dv2 = _get_value(dv2)
            ret = dv1 == dv2
            assert isinstance(ret, bool)
            return ret

    def _is_none(self) -> bool:
        return self.__dict__["_content"] is None

    def _is_missing(self) -> bool:
        try:
            self._dereference_node(
                throw_on_resolution_failure=False, throw_on_missing=True
            )
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

    def _get_full_key(self, key: Union[DictKeyType, int, slice, None]) -> str:
        from .listconfig import ListConfig
        from .omegaconf import _select_one

        if not isinstance(key, (int, str, Enum, float, bool, slice, type(None))):
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
            elif isinstance(key, (int, float, bool)):
                key = str(key)

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
                c=self, key=str(key), throw_on_missing=False, throw_on_type_error=False
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


def _create_structured_with_missing_fields(
    ref_type: type, object_type: Optional[type] = None
) -> "DictConfig":
    from .dictconfig import DictConfig

    cfg_data = get_structured_config_data(ref_type)
    for v in cfg_data.values():
        v._set_value("???")

    cfg = DictConfig(cfg_data)
    cfg._metadata.optional, cfg._metadata.ref_type = _resolve_optional(ref_type)
    cfg._metadata.object_type = object_type

    return cfg


def _is_missing_value(value: Any) -> bool:
    if isinstance(value, Container):
        value = value._value()
    ret = isinstance(value, str) and value == "???"
    assert isinstance(ret, bool)
    return ret


def _update_types(node: Node, ref_type: type, object_type: Optional[type]) -> None:
    if object_type is not None and not is_primitive_dict(object_type):
        node._metadata.object_type = object_type

    if node._metadata.ref_type is Any:
        new_is_optional, new_ref_type = _resolve_optional(ref_type)
        if new_ref_type is not Any:
            node._metadata.ref_type = new_ref_type
            node._metadata.optional = new_is_optional
