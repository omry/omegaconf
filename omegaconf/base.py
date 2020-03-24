from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Type, Union

from ._utils import ValueKind, _get_value, get_value_kind
from .errors import MissingMandatoryValue, UnsupportedInterpolationType


@dataclass
class Metadata:

    optional: bool = True

    key: Any = None

    # Flags have 3 modes:
    #   unset : inherit from parent (None if no parent specifies)
    #   set to true: flag is true
    #   set to false: flag is false
    flags: Dict[str, bool] = field(default_factory=dict)


@dataclass
class ContainerMetadata(Metadata):
    element_type: Type[Any] = None  # type:ignore
    resolver_cache: Dict[str, Any] = field(default_factory=lambda: defaultdict(dict))


class Node(ABC):
    _metadata: Metadata

    parent: Optional["Container"]

    def __init__(self, parent: Optional["Container"], metadata: Metadata):
        self.__dict__["_metadata"] = metadata
        self.__dict__["_parent"] = parent

    def _set_parent(self, parent: Optional["Container"]) -> None:
        assert parent is None or isinstance(parent, Container)
        self.__dict__["_parent"] = parent

    def _get_parent(self) -> Optional["Container"]:
        parent = self.__dict__["_parent"]
        assert parent is None or isinstance(parent, Container)
        return parent

    def _set_flag(self, flag: str, value: Optional[bool]) -> None:
        assert value is None or isinstance(value, bool)
        if value is None:
            if flag in self._metadata.flags:
                del self._metadata.flags[flag]
        else:
            self._metadata.flags[flag] = value

    def _get_node_flag(self, flag: str) -> Optional[bool]:
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        return self._metadata.flags[flag] if flag in self._metadata.flags else None

    def _get_flag(self, flag: str) -> Optional[bool]:
        """
        Returns True if this config node flag is set
        A flag is set if node.set_flag(True) was called
        or one if it's parents is flag is set
        :return:
        """
        flags = self._metadata.flags
        if flag in flags and flags[flag] is not None:
            return flags[flag]

        parent = self._get_parent()
        if parent is None:
            return None
        else:
            # noinspection PyProtectedMember
            return parent._get_flag(flag)

    # TODO: simplify now that each node has it's own key
    def _get_full_key(self, key: Union[str, Enum, int]) -> str:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        full_key = ""
        child = None
        cur: Optional[Node] = self
        while cur is not None:
            if isinstance(cur, DictConfig):
                if child is None:
                    full_key = "{}".format(key)
                else:
                    # find which the key for child in the parent
                    for parent_key in cur.keys():
                        if id(cur.get_node(parent_key)) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "{}{}".format(parent_key, full_key)
                            else:
                                if full_key == "":
                                    full_key = parent_key
                                else:
                                    full_key = "{}.{}".format(parent_key, full_key)
                            break
            elif isinstance(cur, ListConfig):
                if child is None:
                    if key == "":
                        full_key = f"{key}"
                    else:
                        full_key = f"[{key}]"
                else:
                    for idx, v in enumerate(cur):
                        if id(v) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "[{}]{}".format(idx, full_key)
                            else:
                                full_key = "[{}].{}".format(idx, full_key)
                            break
            child = cur
            parent = child._get_parent()
            assert parent is None or isinstance(parent, Container)
            cur = parent

        return full_key

    def _dereference_node(self, throw_on_missing: bool = False) -> "Node":
        from .nodes import StringNode

        if self._is_interpolation():
            value_kind, match_list = get_value_kind(
                value=self._value(), return_match_list=True
            )
            match = match_list[0]
            parent = self._get_parent()
            assert parent is not None
            key = self._key()
            if value_kind == ValueKind.INTERPOLATION:
                v = parent._resolve_interpolation(
                    key=key,
                    inter_type=match.group(1),
                    inter_key=match.group(2),
                    throw_on_missing=throw_on_missing,
                )
                return v
            elif value_kind == ValueKind.STR_INTERPOLATION:
                ret = parent._resolve_str_interpolation(
                    key=key, value=self, throw_on_missing=throw_on_missing
                )
                return StringNode(
                    value=ret,
                    key=key,
                    parent=parent,
                    is_optional=self._metadata.optional,
                )
            assert False  # pragma: no cover
        else:
            # not interpolation, compare directly
            if throw_on_missing:

                if isinstance(self, Container):
                    value = self.__dict__["_content"]  # TODO normalize
                else:
                    value = self._value()
                if value == "???":
                    raise MissingMandatoryValue(self._get_full_key(""))
            return self

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
    def _value(self) -> Any:
        ...  # pragma: no cover

    @abstractmethod
    def _set_value(self, value: Any) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def _is_none(self) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def _is_optional(self) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def _is_missing(self) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def _is_interpolation(self) -> bool:
        ...  # pragma: no cover

    def _key(self) -> Any:
        return self._metadata.key

    def _set_key(self, key: Any) -> None:
        self._metadata.key = key


class Container(Node):
    """
    Container tagging interface
    """

    _metadata: ContainerMetadata

    @abstractmethod
    def pretty(self, resolve: bool = False, sort_keys: bool = False) -> str:
        ...  # pragma: no cover

    @abstractmethod
    def update_node(self, key: str, value: Any = None) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def select(self, key: str) -> Any:
        ...  # pragma: no cover

    def get_node(self, key: Any) -> Node:
        ...  # pragma: no cover

    @abstractmethod
    def __delitem__(self, key: Union[str, int, slice]) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def __setitem__(self, key: Any, value: Any) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        ...  # pragma: no cover

    @abstractmethod
    def __getitem__(self, key_or_index: Any) -> Any:
        ...  # pragma: no cover

    def _get_root(self) -> "Container":
        root: Optional[Container] = self._get_parent()
        if root is None:
            return self
        assert root is not None and isinstance(root, Container)
        while root._get_parent() is not None:
            root = root._get_parent()
            assert root is not None and isinstance(root, Container)
        return root

    def _resolve_interpolation(
        self, key: Any, inter_type: str, inter_key: str, throw_on_missing: bool,
    ) -> "Node":
        from omegaconf import OmegaConf  # isort:skip
        from .nodes import ValueNode

        root_node = self._get_root()

        inter_type = ("str:" if inter_type is None else inter_type)[0:-1]
        if inter_type == "str":
            parent, last_key, value = root_node._select_impl(inter_key)  # type: ignore
            if parent is None or (value is None and last_key not in parent):
                raise KeyError(
                    "{} interpolation key '{}' not found".format(inter_type, inter_key)
                )
            if throw_on_missing and isinstance(value, Node) and value._is_missing():
                raise MissingMandatoryValue(parent._get_full_key(str(key)))
            assert isinstance(value, Node)
            return value
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                value = resolver(root_node, inter_key)
                assert isinstance(self, Container)
                node = self.get_node(key)
                return ValueNode(
                    value=value,
                    parent=self,
                    key=key,
                    is_optional=node._metadata.optional,
                )
            else:
                raise UnsupportedInterpolationType(
                    "Unsupported interpolation type {}".format(inter_type)
                )

    def _resolve_str_interpolation(
        self, key: Any, value: "Node", throw_on_missing: bool
    ) -> Any:
        from .nodes import StringNode

        value_kind, match_list = get_value_kind(value=value, return_match_list=True)
        if value_kind not in (ValueKind.INTERPOLATION, ValueKind.STR_INTERPOLATION):
            return value

        if value_kind == ValueKind.INTERPOLATION:
            # simple interpolation, inherit type
            match = match_list[0]
            return self._resolve_interpolation(
                key=key,
                inter_type=match.group(1),
                inter_key=match.group(2),
                throw_on_missing=throw_on_missing,
            )
        elif value_kind == ValueKind.STR_INTERPOLATION:
            value = _get_value(value)
            assert isinstance(value, str)
            orig = value
            new = ""
            last_index = 0
            for match in match_list:
                new_val = self._resolve_interpolation(
                    key=key,
                    inter_type=match.group(1),
                    inter_key=match.group(2),
                    throw_on_missing=throw_on_missing,
                )
                new += orig[last_index : match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return StringNode(value=new, key=key)
        else:
            assert False  # pragma: no cover
