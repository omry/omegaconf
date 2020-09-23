from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, Optional, Tuple, Type, Union

from ._utils import ValueKind, format_and_raise, get_value_kind
from .errors import ConfigKeyError, MissingMandatoryValue, UnsupportedInterpolationType
from .grammar.gen.OmegaConfGrammarParser import OmegaConfGrammarParser
from .grammar_visitor import GrammarVisitor


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
    flags: Optional[Dict[str, bool]] = None
    resolver_cache: Dict[str, Any] = field(default_factory=lambda: defaultdict(dict))

    def __post_init__(self) -> None:
        if self.flags is None:
            self.flags = {}


@dataclass
class ContainerMetadata(Metadata):
    key_type: Any = None
    element_type: Any = None

    def __post_init__(self) -> None:
        assert self.key_type is Any or isinstance(self.key_type, type)
        if self.element_type is not None:
            assert self.element_type is Any or isinstance(self.element_type, type)

        if self.flags is None:
            self.flags = {}


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
            assert self._metadata.flags is not None
            if flag in self._metadata.flags:
                del self._metadata.flags[flag]
        else:
            assert self._metadata.flags is not None
            self._metadata.flags[flag] = value
        return self

    def _get_node_flag(self, flag: str) -> Optional[bool]:
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        assert self._metadata.flags is not None
        return self._metadata.flags[flag] if flag in self._metadata.flags else None

    def _get_flag(self, flag: str) -> Optional[bool]:
        """
        Returns True if this config node flag is set
        A flag is set if node.set_flag(True) was called
        or one if it's parents is flag is set
        :return:
        """
        flags = self._metadata.flags
        assert flags is not None
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
        if self._is_interpolation():
            parent = self._get_parent()
            assert parent is not None
            key = self._key()
            rval = parent.resolve_interpolation(
                parent=parent,
                key=key,
                value=self,
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            )
            assert rval is None or isinstance(rval, Node)
            return rval
        else:
            # not interpolation, compare directly
            if throw_on_missing:
                value = self._value()
                if value == "???":
                    raise MissingMandatoryValue("Missing mandatory value")
            return self

    def _get_root(self) -> "Container":
        root: Optional[Container] = self._get_parent()
        if root is None:
            assert isinstance(self, Container)
            return self
        assert root is not None and isinstance(root, Container)
        while root._get_parent() is not None:
            root = root._get_parent()
            assert root is not None and isinstance(root, Container)
        return root

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

    def _resolve_key_and_root(self, key: str) -> Tuple["Container", str]:
        orig = key
        if not key.startswith("."):
            return self._get_root(), key
        else:
            root: Optional[Container] = self
            assert key.startswith(".")
            while True:
                assert root is not None
                key = key[1:]
                if not key.startswith("."):
                    break
                root = root._get_parent()
                if root is None:
                    raise ConfigKeyError(f"Error resolving key '{orig}'")

            return root, key

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

            if ret is not None and not isinstance(ret, Container):
                raise ConfigKeyError(
                    f"Error trying to access {key}: node `{'.'.join(split[0:i + 1])}` "
                    f"is not a container and thus cannot contain `{split[i + 1]}``"
                )
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
            return root, last_key, None
        value = root.resolve_interpolation(
            parent=root,
            key=last_key,
            value=value,
            throw_on_missing=False,
            throw_on_resolution_failure=True,
        )
        return root, last_key, value

    def _resolve_complex_interpolation(
        self,
        parent: Optional["Container"],
        value: "Node",
        key: Any,
        parse_tree: OmegaConfGrammarParser.ConfigValueContext,
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Optional["Node"]:
        """
        A "complex" interpolation is any interpolation that cannot be handled by
        `_resolve_simple_interpolation()`, i.e. that either contains nested
        interpolations or is not a single "${..}" block.
        """

        from .nodes import StringNode

        value_str = value._value()
        assert isinstance(value_str, str)

        visitor = GrammarVisitor(
            container=self,
            resolve_args=dict(
                key=key,
                parent=parent,
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            ),
        )

        resolved = visitor.visit(parse_tree)
        if resolved is None:
            return None
        elif isinstance(resolved, str):
            # Result is a string: create a new node to store it.
            return StringNode(
                value=resolved,
                key=key,
                parent=parent,
                is_optional=value._metadata.optional,
            )
        else:
            assert isinstance(resolved, Node)
            return resolved

    def _resolve_simple_interpolation(
        self,
        key: Any,
        parent: Optional["Container"],
        inter_type: Optional[str],
        inter_key: Tuple[Any, ...],
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
        inputs_str: Optional[Tuple[str, ...]] = None,  # text representation of inputs
    ) -> Optional["Node"]:
        from omegaconf import OmegaConf

        from .nodes import ValueNode

        if inter_type is None:
            assert inputs_str is None
            assert len(inter_key) == 1 and isinstance(inter_key[0], str)
            inter_key_str = inter_key[0]
            root_node, inter_key_str = self._resolve_key_and_root(inter_key_str)
            parent, last_key, value = root_node._select_impl(
                inter_key_str,
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            )

            # if parent is None or (value is None and last_key not in parent):  # type: ignore
            if parent is None or value is None:
                if throw_on_resolution_failure:
                    raise ConfigKeyError(
                        f"Interpolation key '{inter_key_str}' not found"
                    )
                else:
                    return None
            assert isinstance(value, Node)
            return value
        else:
            assert inputs_str is not None
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                root_node = self._get_root()
                try:
                    value = resolver(root_node, parent, inter_key, inputs_str)
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

    def resolve_interpolation(
        self,
        parent: Optional["Container"],
        key: Any,
        value: "Node",
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Any:
        value_kind, parse_tree = get_value_kind(value=value, return_parse_tree=True)  # type: ignore

        if value_kind != ValueKind.INTERPOLATION:
            return value

        assert parse_tree is not None
        return self._resolve_complex_interpolation(
            parent=parent,
            value=value,
            key=key,
            parse_tree=parse_tree,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )

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
