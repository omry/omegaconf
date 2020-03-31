from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Tuple, Type, Union

from ._utils import ValueKind, _get_value, format_and_raise, get_value_kind
from .errors import MissingMandatoryValue, UnsupportedInterpolationType


@dataclass
class Metadata:

    ref_type: Optional[Type[Any]]

    object_type: Optional[Type[Any]]

    optional: bool

    key: Any

    # Flags have 3 modes:
    #   unset : inherit from parent (None if no parent specifies)
    #   set to true: flag is true
    #   set to false: flag is false
    flags: Dict[str, bool] = field(default_factory=dict)
    resolver_cache: Dict[str, Any] = field(default_factory=lambda: defaultdict(dict))


@dataclass
class ContainerMetadata(Metadata):
    key_type: Any = None
    element_type: Any = None


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

    # TODO: move to utils
    def _translate_exception(
        self, e: Exception, key: Any, value: Any, type_override: Any = None
    ) -> None:
        etype = type(e) if type_override is None else type_override
        format_and_raise(
            exception_type=etype, node=self, key=key, value=value, msg=str(e), cause=e,
        )
        assert False  # pragma: no cover

    @abstractmethod
    def _get_full_key(self, key: Union[str, Enum, int, None]) -> str:
        ...

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
                value = self._value()
                if value == "???":
                    raise MissingMandatoryValue("Missing mandatory value")
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
    def select(self, key: str, throw_on_missing: bool = False) -> Any:
        ...  # pragma: no cover

    def get_node(self, key: Any) -> Optional[Node]:
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

    def _select_impl(
        self, key: str, throw_on_missing: bool
    ) -> Tuple[Optional["Container"], Optional[str], Optional[Node]]:
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
            ret, _ = _select_one(c=root, key=k, throw_on_missing=throw_on_missing)
            assert ret is None or isinstance(ret, Container)
            root = ret

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = _select_one(c=root, key=last_key, throw_on_missing=throw_on_missing)
        if value is None:
            return root, last_key, value
        value = root._resolve_str_interpolation(
            key=last_key, value=value, throw_on_missing=False
        )
        return root, last_key, value

    def _resolve_interpolation(
        self, key: Any, inter_type: str, inter_key: str, throw_on_missing: bool,
    ) -> "Node":
        from omegaconf import OmegaConf

        from .nodes import ValueNode

        root_node = self._get_root()

        inter_type = ("str:" if inter_type is None else inter_type)[0:-1]
        if inter_type == "str":
            parent, last_key, value = root_node._select_impl(
                inter_key, throw_on_missing=throw_on_missing
            )

            if parent is None or (value is None and last_key not in parent):  # type: ignore
                raise KeyError(
                    f"{inter_type} interpolation key '{inter_key}' not found"
                )
            assert isinstance(value, Node)
            return value
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                value = resolver(root_node, inter_key)
                return ValueNode(
                    value=value,
                    parent=self,
                    metadata=Metadata(
                        ref_type=None, object_type=None, key=key, optional=True
                    ),
                )
            else:
                raise UnsupportedInterpolationType(
                    f"Unsupported interpolation type {inter_type}"
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
