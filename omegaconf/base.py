from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Tuple, Type, Union

from ._utils import ValueKind, _get_value, format_and_raise, get_value_kind
from .errors import ConfigKeyError, MissingMandatoryValue, UnsupportedInterpolationType


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

    def __post_init__(self) -> None:
        assert self.key_type is None or isinstance(self.key_type, type)
        assert self.element_type is None or isinstance(self.element_type, type)


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

    def _set_flag(self, flag: str, value: Optional[bool]) -> "Node":
        assert value is None or isinstance(value, bool)
        if value is None:
            if flag in self._metadata.flags:
                del self._metadata.flags[flag]
        else:
            self._metadata.flags[flag] = value
        return self

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

    def _format_and_raise(
        self, key: Any, value: Any, cause: Exception, type_override: Any = None
    ) -> None:
        format_and_raise(
            node=self,
            key=key,
            value=value,
            msg=str(cause),
            cause=cause,
            type_override=type_override,
        )
        assert False

    @abstractmethod
    def _get_full_key(self, key: Union[str, Enum, int, None]) -> str:
        ...

    def _dereference_node(
        self, throw_on_missing: bool = False, throw_on_resolution_failure: bool = True
    ) -> Optional["Node"]:
        from .nodes import StringNode

        if self._is_interpolation():
            value_kind, match_list = get_value_kind(
                value=self._value(), return_match_list=True
            )
            match = match_list[0]
            parent = self._get_parent()
            key = self._key()
            if value_kind == ValueKind.INTERPOLATION:
                assert parent is not None
                v = parent._resolve_simple_interpolation(
                    key=key,
                    inter_type=match.group(1),
                    inter_key=match.group(2),
                    throw_on_missing=throw_on_missing,
                    throw_on_resolution_failure=throw_on_resolution_failure,
                )
                return v
            elif value_kind == ValueKind.STR_INTERPOLATION:
                assert parent is not None
                ret = parent._resolve_interpolation(
                    key=key,
                    value=self,
                    throw_on_missing=throw_on_missing,
                    throw_on_resolution_failure=throw_on_resolution_failure,
                )
                if ret is None:
                    return ret
                return StringNode(
                    value=ret,
                    key=key,
                    parent=parent,
                    is_optional=self._metadata.optional,
                )
            assert False
        else:
            # not interpolation, compare directly
            if throw_on_missing:
                value = self._value()
                if value == "???":
                    raise MissingMandatoryValue("Missing mandatory value")
            return self

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __ne__(self, other: Any) -> bool:
        ...

    @abstractmethod
    def __hash__(self) -> int:
        ...

    @abstractmethod
    def _value(self) -> Any:
        ...

    @abstractmethod
    def _set_value(self, value: Any) -> None:
        ...

    @abstractmethod
    def _is_none(self) -> bool:
        ...

    @abstractmethod
    def _is_optional(self) -> bool:
        ...

    @abstractmethod
    def _is_missing(self) -> bool:
        ...

    @abstractmethod
    def _is_interpolation(self) -> bool:
        ...

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
        ...

    @abstractmethod
    def update_node(self, key: str, value: Any = None) -> None:
        ...

    @abstractmethod
    def select(self, key: str, throw_on_missing: bool = False) -> Any:
        ...

    def _get_node(self, key: Any, validate_access: bool = True) -> Optional[Node]:
        ...

    @abstractmethod
    def __delitem__(self, key: Any) -> None:
        ...

    @abstractmethod
    def __setitem__(self, key: Any, value: Any) -> None:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        ...

    @abstractmethod
    def __getitem__(self, key_or_index: Any) -> Any:
        ...

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
        self, key: str, throw_on_missing: bool, throw_on_resolution_failure: bool
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
            ret, _ = _select_one(
                c=root,
                key=k,
                throw_on_missing=throw_on_missing,
                throw_on_type_error=throw_on_resolution_failure,
            )
            if isinstance(ret, Node):
                ret = ret._dereference_node(
                    throw_on_missing=throw_on_missing,
                    throw_on_resolution_failure=throw_on_resolution_failure,
                )

            assert ret is None or isinstance(ret, Container)
            root = ret

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = _select_one(
            c=root,
            key=last_key,
            throw_on_missing=throw_on_missing,
            throw_on_type_error=throw_on_resolution_failure,
        )
        if value is None:
            return root, last_key, value
        value = root._resolve_interpolation(
            key=last_key,
            value=value,
            throw_on_missing=False,
            throw_on_resolution_failure=True,
        )
        return root, last_key, value

    def _resolve_simple_interpolation(
        self,
        key: Any,
        inter_type: str,
        inter_key: str,
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Optional["Node"]:
        from omegaconf import OmegaConf

        from .nodes import ValueNode

        root_node = self._get_root()

        inter_type = ("str:" if inter_type is None else inter_type)[0:-1]
        if inter_type == "str":
            parent, last_key, value = root_node._select_impl(
                inter_key,
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            )

            # if parent is None or (value is None and last_key not in parent):  # type: ignore
            if parent is None or value is None:
                if throw_on_resolution_failure:
                    raise ConfigKeyError(
                        f"{inter_type} interpolation key '{inter_key}' not found"
                    )
                else:
                    return None
            assert isinstance(value, Node)
            return value
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                try:
                    value = resolver(root_node, inter_key)
                    return ValueNode(
                        value=value,
                        parent=self,
                        metadata=Metadata(
                            ref_type=None, object_type=None, key=key, optional=True
                        ),
                    )
                except Exception as e:
                    self._format_and_raise(key=inter_key, value=None, cause=e)
                    assert False
            else:
                if throw_on_resolution_failure:
                    raise UnsupportedInterpolationType(
                        f"Unsupported interpolation type {inter_type}"
                    )
                else:
                    return None

    def _resolve_interpolation(
        self,
        key: Any,
        value: "Node",
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Any:
        from .nodes import StringNode

        value_kind, match_list = get_value_kind(value=value, return_match_list=True)
        if value_kind not in (ValueKind.INTERPOLATION, ValueKind.STR_INTERPOLATION):
            return value

        if value_kind == ValueKind.INTERPOLATION:
            # simple interpolation, inherit type
            match = match_list[0]
            return self._resolve_simple_interpolation(
                key=key,
                inter_type=match.group(1),
                inter_key=match.group(2),
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            )
        elif value_kind == ValueKind.STR_INTERPOLATION:
            value = _get_value(value)
            assert isinstance(value, str)
            orig = value
            new = ""
            last_index = 0
            for match in match_list:
                new_val = self._resolve_simple_interpolation(
                    key=key,
                    inter_type=match.group(1),
                    inter_key=match.group(2),
                    throw_on_missing=throw_on_missing,
                    throw_on_resolution_failure=throw_on_resolution_failure,
                )
                # if failed to resolve, return None for the whole thing.
                if new_val is None:
                    return None
                new += orig[last_index : match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return StringNode(value=new, key=key)
        else:
            assert False

    def _re_parent(self) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        # update parents of first level Config nodes to self

        if isinstance(self, Container):
            if isinstance(self, DictConfig):
                content = self.__dict__["_content"]
                if isinstance(content, dict):
                    for _key, value in self.__dict__["_content"].items():
                        if value is not None:
                            value._set_parent(self)
                        if isinstance(value, Container):
                            value._re_parent()
            elif isinstance(self, ListConfig):
                content = self.__dict__["_content"]
                if isinstance(content, list):
                    for item in self.__dict__["_content"]:
                        if item is not None:
                            item._set_parent(self)
                        if isinstance(item, Container):
                            item._re_parent()

    def _has_ref_type(self) -> bool:
        return self._metadata.ref_type is not Any
