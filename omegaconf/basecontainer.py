import copy
import sys
import warnings
from abc import ABC
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple, Union

import yaml

from ._utils import (
    ValueKind,
    get_value_kind,
    get_yaml_loader,
    is_primitive_container,
    is_structured_config,
)
from .base import Container, Node
from .errors import (
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
    ValidationError,
)


class BaseContainer(Container, ABC):
    # static fields
    _resolvers: Dict[str, Any] = {}
    missing: bool

    def __init__(self, element_type: type, parent: Optional["Container"]):
        super().__init__(parent=parent)
        self.__dict__["content"] = None
        self.__dict__["_resolver_cache"] = defaultdict(dict)
        self.__dict__["_element_type"] = element_type

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
        from .nodes import ValueNode

        def is_mandatory_missing(val: Any) -> bool:
            return get_value_kind(val) == ValueKind.MANDATORY_MISSING  # type: ignore

        if isinstance(value, ValueNode):
            value = value.value()

        if default_value is not None and (value is None or is_mandatory_missing(value)):
            value = default_value

        value = self._resolve_single(value) if isinstance(value, str) else value
        if is_mandatory_missing(value):
            raise MissingMandatoryValue(self.get_full_key(str(key)))

        return value

    def get_full_key(self, key: Union[str, Enum, int]) -> str:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        full_key = ""
        child = None
        parent: Container = self
        while parent is not None:
            assert isinstance(parent, (DictConfig, ListConfig))
            if isinstance(parent, DictConfig):
                if child is None:
                    full_key = "{}".format(key)
                else:
                    # find which the key for child in the parent
                    for parent_key in parent.keys():
                        if id(parent.get_node(parent_key)) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "{}{}".format(parent_key, full_key)
                            else:
                                full_key = "{}.{}".format(parent_key, full_key)
                            break
            elif isinstance(parent, ListConfig):
                if child is None:
                    if key == "":
                        full_key = f"{key}"
                    else:
                        full_key = f"[{key}]"
                else:
                    for idx, v in enumerate(parent):
                        if id(v) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "[{}]{}".format(idx, full_key)
                            else:
                                full_key = "[{}].{}".format(idx, full_key)
                            break
            child = parent
            parent = child._get_parent()

        return full_key

    def __str__(self) -> str:
        return self.__repr__()

    def __repr__(self) -> str:
        if self._is_missing():
            return "'???'"
        else:
            return self.__dict__["content"].__repr__()  # type: ignore

    # Support pickle
    def __getstate__(self) -> Dict[str, Any]:
        return self.__dict__

    # Support pickle
    def __setstate__(self, d: Dict[str, Any]) -> None:
        self.__dict__.update(d)

    def __delitem__(self, key: Union[str, int, slice]) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(str(key)))
        del self.__dict__["content"][key]

    def __len__(self) -> int:
        if self._is_missing():
            return 0
        return self.__dict__["content"].__len__()  # type: ignore

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
        return value

    def _select_impl(self, key: str) -> Any:
        """
        Select a value using dot separated key sequence
        :param key:
        :return:
        """
        from .omegaconf import _select_one

        if key == "":
            return self, "", self

        split = key.split(".")
        root = self
        for i in range(len(split) - 1):
            if root is None:
                break
            k = split[i]
            root, _ = _select_one(root, k)

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = _select_one(root, last_key)
        return root, last_key, value

    def is_empty(self) -> bool:
        """return true if config is empty"""
        return len(self.__dict__["content"]) == 0

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

    def pretty(self, resolve: bool = False) -> str:
        from omegaconf import OmegaConf

        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :return: A string containing the yaml representation.
        """
        container = OmegaConf.to_container(self, resolve=resolve, enum_to_str=True)
        return yaml.dump(  # type: ignore
            container, default_flow_style=False, allow_unicode=True
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
        result_type = None
        if (
            src.__dict__["_type"] is not None
            and src.__dict__["_type"] is not dest.__dict__["_type"]
        ):
            prototype = DictConfig(content={})
            result_type = src.__dict__["_type"]
            src.__dict__["_type"] = None
            prototype.merge_with(src)
            prototype.merge_with(dest)

            for k in {"content", "_resolver_cache", "_key_type", "_missing"}:
                dest.__dict__[k] = prototype.__dict__[k]

        for key, value in src.items_ex(resolve=False):
            dest_type = dest.__dict__["_element_type"]
            typed = dest_type not in (None, Any)
            if OmegaConf.is_missing(dest, key):
                if isinstance(value, DictConfig):
                    if OmegaConf.is_missing(src, key):
                        dest[key] = DictConfig(content="???")
                    else:
                        dest[key] = {}

            if (dest.get_node(key) is not None) or typed:
                dest_node = dest.get_node(key)
                if dest_node is None and typed:
                    dest[key] = DictConfig(content=dest_type, parent=dest)
                    dest_node = dest.get_node(key)

                if isinstance(dest_node, BaseContainer):
                    if isinstance(value, BaseContainer):
                        dest_node.merge_with(value)
                    else:
                        dest.__setitem__(key, value)
                else:
                    if isinstance(value, BaseContainer):
                        dest.__setitem__(key, value)
                    else:
                        assert isinstance(dest_node, ValueNode)
                        dest_node.set_value(value)
            else:
                dest[key] = src.get_node(key)

            if result_type is not None:
                dest.__dict__["_type"] = result_type

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
                    raise ReadonlyConfigError(self.get_full_key(""))
                self.__dict__["content"].clear()
                for item in other:
                    self.append(item)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        # recursively correct the parent hierarchy after the merge
        self._re_parent()

    @staticmethod
    def _resolve_value(root_node: Container, inter_type: str, inter_key: str) -> Any:
        from omegaconf import OmegaConf

        inter_type = ("str:" if inter_type is None else inter_type)[0:-1]
        if inter_type == "str":
            parent, last_key, value = root_node._select_impl(inter_key)  # type: ignore
            if parent is None or (value is None and last_key not in parent):
                raise KeyError(
                    "{} interpolation key '{}' not found".format(inter_type, inter_key)
                )
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                value = resolver(root_node, inter_key)
            else:
                raise UnsupportedInterpolationType(
                    "Unsupported interpolation type {}".format(inter_type)
                )

        return value

    def _resolve_single(self, value: Any) -> Any:
        value_kind, match_list = get_value_kind(value=value, return_match_list=True)

        if value_kind in (ValueKind.VALUE, ValueKind.MANDATORY_MISSING):
            return value

        root = self._get_root()
        if value_kind == ValueKind.INTERPOLATION:
            # simple interpolation, inherit type
            match = match_list[0]
            return BaseContainer._resolve_value(root, match.group(1), match.group(2))
        elif value_kind == ValueKind.STR_INTERPOLATION:
            # Concatenated interpolation, always a string
            orig = value
            new = ""
            last_index = 0
            for match in match_list:
                new_val = BaseContainer._resolve_value(
                    root, match.group(1), match.group(2)
                )
                new += orig[last_index : match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return new

    # noinspection PyProtectedMember
    def _set_item_impl(self, key: Union[str, Enum, int], value: Any) -> None:
        from omegaconf.omegaconf import _maybe_wrap

        from .nodes import ValueNode

        must_wrap = is_primitive_container(value)
        input_config = isinstance(value, Container)
        input_node = isinstance(value, ValueNode)
        if isinstance(self.__dict__["content"], dict):
            target_node = key in self.__dict__["content"] and isinstance(
                self.get_node(key), ValueNode
            )

        elif isinstance(self.__dict__["content"], list):
            target_node = isinstance(self.get_node(key), ValueNode)

        def wrap(val: Any) -> Node:
            return _maybe_wrap(
                annotated_type=self.__dict__["_element_type"],
                value=val,
                is_optional=True,
                parent=self,
            )

        try:
            if must_wrap:
                self.__dict__["content"][key] = wrap(value)
            elif input_node and target_node:
                # both nodes, replace existing node with new one
                value._set_parent(self)
                self.__dict__["content"][key] = value
            elif not input_node and target_node:
                # input is not node, can be primitive or config
                if input_config:
                    value._set_parent(self)
                    self.__dict__["content"][key] = value
                else:
                    self.__dict__["content"][key].set_value(value)
            elif input_node and not target_node:
                # target must be config, replace target with input node
                value._set_parent(self)
                self.__dict__["content"][key] = value
            elif not input_node and not target_node:
                # target must be config.
                # input can be primitive or config
                if input_config:
                    value._set_parent(self)
                    self.__dict__["content"][key] = value
                else:
                    self.__dict__["content"][key] = wrap(value)
        except ValidationError as ve:
            import sys

            raise type(ve)(
                f"Error setting '{self.get_full_key(str(key))} = {value}' : {ve}"
            ).with_traceback(sys.exc_info()[2]) from None

    @staticmethod
    def _item_eq(
        c1: "BaseContainer",
        k1: Union[str, int],
        c2: "BaseContainer",
        k2: Union[str, int],
    ) -> bool:
        from .nodes import ValueNode

        v1 = c1.get_node(k1)
        v2 = c2.get_node(k2)
        v1_kind = get_value_kind(v1)
        v2_kind = get_value_kind(v2)

        if v1_kind == v2_kind and v1_kind == ValueKind.MANDATORY_MISSING:
            return True

        if isinstance(v1, ValueNode):
            v1 = v1.value()
        if isinstance(v2, ValueNode):
            v2 = v2.value()

        # special case for two interpolations. just compare them literally.
        # This is helping in cases where the two interpolations are not resolvable
        # but the objects are still considered equal.
        if v1_kind in (
            ValueKind.STR_INTERPOLATION,
            ValueKind.INTERPOLATION,
        ) and v2_kind in (ValueKind.STR_INTERPOLATION, ValueKind.INTERPOLATION):
            return True
        if isinstance(v1, str):
            v1 = c1._resolve_single(v1)
        if isinstance(v2, str):
            v2 = c2._resolve_single(v2)

        if isinstance(v1, BaseContainer) and isinstance(v2, BaseContainer):
            if not BaseContainer._config_eq(v1, v2):
                return False
        return v1 == v2

    @staticmethod
    def _list_eq(l1: "BaseContainer", l2: "BaseContainer") -> bool:
        from .listconfig import ListConfig

        assert isinstance(l1, ListConfig)
        assert isinstance(l2, ListConfig)
        if len(l1) != len(l2):
            return False
        for i in range(len(l1)):
            if not BaseContainer._item_eq(l1, i, l2, i):
                return False

        return True

    @staticmethod
    def _dict_conf_eq(d1: "BaseContainer", d2: "BaseContainer") -> bool:
        from .dictconfig import DictConfig

        assert isinstance(d1, DictConfig)
        assert isinstance(d2, DictConfig)
        if len(d1) != len(d2):
            return False
        d1keys = sorted(d1.keys(), key=str)
        d2keys = sorted(d2.keys(), key=str)
        assert len(d1keys) == len(d2keys)
        for index, k1 in enumerate(d1keys):
            k2 = d2keys[index]
            if k1 != k2:
                return False
            if not BaseContainer._item_eq(d1, k1, d2, k2):
                return False

        return True

    @staticmethod
    def _config_eq(c1: "BaseContainer", c2: "BaseContainer") -> bool:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        assert isinstance(c1, Container)
        assert isinstance(c2, Container)
        if isinstance(c1, DictConfig) and isinstance(c2, DictConfig):
            return DictConfig._dict_conf_eq(c1, c2)
        if isinstance(c1, ListConfig) and isinstance(c2, ListConfig):
            return BaseContainer._list_eq(c1, c2)
        # if type does not match objects are different
        return False

    def _re_parent(self) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        # update parents of first level Config nodes to self

        if isinstance(self, Container) and not self._is_missing():
            if isinstance(self, DictConfig):
                for _key, value in self.__dict__["content"].items():
                    value._set_parent(self)
                    BaseContainer._re_parent(value)
            elif isinstance(self, ListConfig):
                for item in self.__dict__["content"]:
                    item._set_parent(self)
                    BaseContainer._re_parent(item)

    def _is_missing(self) -> bool:
        return self.__dict__["_missing"] is True

    @staticmethod
    def _validate_node_type(node: Node, value: Any) -> None:
        from .dictconfig import DictConfig

        type_ = node.__dict__["_type"] if isinstance(node, DictConfig) else None
        is_typed = type_ is not None
        mismatch_type = is_typed and not issubclass(type(value), type_)

        if mismatch_type and not get_value_kind(value) == ValueKind.MANDATORY_MISSING:
            raise ValidationError(
                f"Invalid type assigned : {type_.__name__} is not a subclass of {type(value).__name__}"
            )
