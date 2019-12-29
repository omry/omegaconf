import copy
import sys
import warnings
from abc import abstractmethod
from collections import defaultdict
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple, Union

import yaml

from ._utils import (
    ValueKind,
    _re_parent,
    get_value_kind,
    get_yaml_loader,
    is_structured_config,
)
from .base import Container, Node
from .errors import (
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
)


class BaseContainer(Container):
    # static fields
    _resolvers: Dict[str, Any] = {}

    def __init__(self, element_type: type, parent: Optional["Container"]):
        super().__init__(parent=parent)
        self.__dict__["content"] = None
        self.__dict__["_resolver_cache"] = defaultdict(dict)
        self.__dict__["_element_type"] = element_type

    @abstractmethod
    def __setitem__(self, key: Any, value: Any) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def get_node(self, key: Any) -> Node:
        ...  # pragma: no cover

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def __ne__(self, other: Any) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def __hash__(self) -> int:
        ...  # pragma: no cover

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        ...  # pragma: no cover

    @abstractmethod
    def __getitem__(self, key_or_index: Any) -> Any:
        ...  # pragma: no cover

    def save(self, f: str) -> None:
        warnings.warn(
            "Use OmegaConf.save(config, filename) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        from omegaconf import OmegaConf

        OmegaConf.save(self, f)

    def _resolve_with_default(
        self, key: Union[str, int], value: Any, default_value: Any = None
    ) -> Any:
        """returns the value with the specified key, like obj.key and obj['key']"""
        from .nodes import ValueNode

        def is_mandatory_missing(val: Any) -> bool:
            return type(val) == str and val == "???"

        if isinstance(value, ValueNode):
            value = value.value()

        if default_value is not None and (value is None or is_mandatory_missing(value)):
            value = default_value

        value = self._resolve_single(value) if isinstance(value, str) else value
        if is_mandatory_missing(value):
            raise MissingMandatoryValue(self.get_full_key(str(key)))

        return value

    def get_full_key(self, key: str) -> str:
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        full_key: Union[str, int] = ""
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
                        full_key = key
                    else:
                        full_key = "[{}]".format(key)
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
        return self.content.__str__()  # type: ignore

    def __repr__(self) -> str:
        return self.content.__repr__()  # type: ignore

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

            self.update(key, value)

    def update(self, key: str, value: Any = None) -> None:
        from .listconfig import ListConfig
        from .dictconfig import DictConfig
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
            root[last] = value
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
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        def convert(val: Any) -> Any:
            if enum_to_str:
                if isinstance(val, Enum):
                    val = "{}.{}".format(type(val).__name__, val.name)

            return val

        assert isinstance(conf, Container)
        if isinstance(conf, DictConfig):
            retdict: Dict[str, Any] = {}
            for key, value in conf.items(resolve=resolve):
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
        return yaml.dump(container, default_flow_style=False, allow_unicode=True)  # type: ignore

    @staticmethod
    def _map_merge(dest: "BaseContainer", src: "BaseContainer") -> None:
        """merge src into dest and return a new copy, does not modified input"""
        from .dictconfig import DictConfig
        from .nodes import ValueNode

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)
        src = copy.deepcopy(src)

        for key, value in src.items(resolve=False):
            dest_type = dest.__dict__["_element_type"]
            typed = dest_type not in (None, Any)
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

    def merge_with(
        self,
        *others: Union["BaseContainer", Dict[str, Any], List[Any], Tuple[Any], Any],
    ) -> None:
        from .omegaconf import OmegaConf
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if isinstance(other, (dict, list, tuple)) or is_structured_config(other):
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
        _re_parent(self)

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
    def _set_item_impl(self, key: Union[str, int], value: Any) -> None:
        from omegaconf.omegaconf import _maybe_wrap
        from .nodes import ValueNode

        must_wrap = isinstance(value, (dict, list))
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
        if isinstance(v1, ValueNode):
            v1 = v1.value()
            if isinstance(v1, str):
                v1 = c1._resolve_single(v1)
        if isinstance(v2, ValueNode):
            v2 = v2.value()
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
        k1 = sorted(d1.keys())
        k2 = sorted(d2.keys())
        if k1 != k2:
            return False
        for k in k1:
            if not BaseContainer._item_eq(d1, k, d2, k):
                return False

        return True

    @staticmethod
    def _config_eq(c1: "BaseContainer", c2: "BaseContainer") -> bool:
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        assert isinstance(c1, Container)
        assert isinstance(c2, Container)
        if isinstance(c1, DictConfig) and isinstance(c2, DictConfig):
            return DictConfig._dict_conf_eq(c1, c2)
        if isinstance(c1, ListConfig) and isinstance(c2, ListConfig):
            return BaseContainer._list_eq(c1, c2)
        # if type does not match objects are different
        return False
