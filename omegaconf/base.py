import copy
from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Tuple, Type, Union

from antlr4 import ParserRuleContext

from ._utils import ValueKind, _get_value, format_and_raise, get_value_kind
from .errors import (
    ConfigKeyError,
    InterpolationResolutionError,
    MissingMandatoryValue,
    OmegaConfBaseException,
    UnsupportedInterpolationType,
)
from .grammar.gen.OmegaConfGrammarParser import OmegaConfGrammarParser
from .grammar_parser import parse
from .grammar_visitor import GrammarVisitor

DictKeyType = Union[str, int, Enum, float, bool]

_MARKER_ = object()


@dataclass
class Metadata:

    ref_type: Union[Type[Any], Any]

    object_type: Union[Type[Any], Any]

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
        if self.ref_type is None:
            self.ref_type = Any
        assert self.key_type is Any or isinstance(self.key_type, type)
        if self.element_type is not None:
            assert self.element_type is Any or isinstance(self.element_type, type)

        if self.flags is None:
            self.flags = {}


class Node(ABC):
    _metadata: Metadata

    _parent: Optional["Container"]
    _flags_cache: Optional[Dict[str, Optional[bool]]]

    def __init__(self, parent: Optional["Container"], metadata: Metadata):
        self.__dict__["_metadata"] = metadata
        self.__dict__["_parent"] = parent
        self.__dict__["_flags_cache"] = None

    def __getstate__(self) -> Dict[str, Any]:
        # Overridden to ensure that the flags cache is cleared on serialization.
        state_dict = copy.copy(self.__dict__)
        del state_dict["_flags_cache"]
        return state_dict

    def __setstate__(self, state_dict: Dict[str, Any]) -> None:
        self.__dict__.update(state_dict)
        self.__dict__["_flags_cache"] = None

    def _set_parent(self, parent: Optional["Container"]) -> None:
        assert parent is None or isinstance(parent, Container)
        self.__dict__["_parent"] = parent
        self._invalidate_flags_cache()

    def _invalidate_flags_cache(self) -> None:
        self.__dict__["_flags_cache"] = None

    def _get_parent(self) -> Optional["Container"]:
        parent = self.__dict__["_parent"]
        assert parent is None or isinstance(parent, Container)
        return parent

    def _set_flag(
        self,
        flags: Union[List[str], str],
        values: Union[List[Optional[bool]], Optional[bool]],
    ) -> "Node":
        if isinstance(flags, str):
            flags = [flags]

        if values is None or isinstance(values, bool):
            values = [values]

        if len(values) == 1:
            values = len(flags) * values

        if len(flags) != len(values):
            raise ValueError("Inconsistent lengths of input flag names and values")

        for idx, flag in enumerate(flags):
            value = values[idx]
            if value is None:
                assert self._metadata.flags is not None
                if flag in self._metadata.flags:
                    del self._metadata.flags[flag]
            else:
                assert self._metadata.flags is not None
                self._metadata.flags[flag] = value
        self._invalidate_flags_cache()
        return self

    def _get_node_flag(self, flag: str) -> Optional[bool]:
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        assert self._metadata.flags is not None
        return self._metadata.flags[flag] if flag in self._metadata.flags else None

    def _get_flag(self, flag: str) -> Optional[bool]:
        cache = self.__dict__["_flags_cache"]
        if cache is None:
            cache = self.__dict__["_flags_cache"] = {}

        ret = cache.get(flag, _MARKER_)
        if ret is _MARKER_:
            ret = self._get_flag_no_cache(flag)
            cache[flag] = ret
        assert ret is None or isinstance(ret, bool)
        return ret

    def _get_flag_no_cache(self, flag: str) -> Optional[bool]:
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
    def _get_full_key(self, key: Optional[Union[DictKeyType, int]]) -> str:
        ...

    def _dereference_node(
        self,
        throw_on_missing: bool = False,
        throw_on_resolution_failure: bool = True,
    ) -> Optional["Node"]:
        if self._is_interpolation():
            parent = self._get_parent()
            if parent is None:
                raise OmegaConfBaseException(
                    "Cannot resolve interpolation for a node without a parent"
                )
            assert parent is not None
            key = self._key()
            return parent._resolve_interpolation_from_parse_tree(
                parent=parent,
                key=key,
                value=self,
                parse_tree=parse(_get_value(self)),
                throw_on_missing=throw_on_missing,
                throw_on_resolution_failure=throw_on_resolution_failure,
            )
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
    def _set_value(self, value: Any, flags: Optional[Dict[str, bool]] = None) -> None:
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

    def _get_node(
        self,
        key: Any,
        validate_access: bool = True,
        throw_on_missing_value: bool = False,
        throw_on_missing_key: bool = False,
    ) -> Union[Optional[Node], List[Optional[Node]]]:
        ...

    @abstractmethod
    def __delitem__(self, key: Any) -> None:
        ...

    @abstractmethod
    def __setitem__(self, key: Any, value: Any) -> None:
        ...

    @abstractmethod
    def __iter__(self) -> Iterator[Any]:
        ...

    @abstractmethod
    def __getitem__(self, key_or_index: Any) -> Any:
        ...

    def __copy__(self) -> Any:
        # real shallow copy is impossible because of the reference to the parent.
        return copy.deepcopy(self)

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
                parent_key = ".".join(split[0 : i + 1])
                child_key = split[i + 1]
                raise ConfigKeyError(
                    f"Error trying to access {key}: node `{parent_key}` "
                    f"is not a container and thus cannot contain `{child_key}`"
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
        value = root._maybe_resolve_interpolation(
            parent=root,
            key=last_key,
            value=value,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )
        return root, last_key, value

    def _resolve_interpolation_from_parse_tree(
        self,
        parent: Optional["Container"],
        value: "Node",
        key: Any,
        parse_tree: OmegaConfGrammarParser.ConfigValueContext,
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Optional["Node"]:
        from .nodes import StringNode

        resolved = self.resolve_parse_tree(
            parse_tree=parse_tree,
            key=key,
            parent=parent,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )

        if resolved is None:
            return None
        elif isinstance(resolved, str):
            # Result is a string: create a new StringNode for it.
            return StringNode(
                value=resolved,
                key=key,
                parent=parent,
                is_optional=value._metadata.optional,
            )
        else:
            assert isinstance(resolved, Node)
            return resolved

    def _resolve_node_interpolation(
        self,
        inter_key: str,
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Optional["Node"]:
        """A node interpolation is of the form `${foo.bar}`"""
        root_node, inter_key = self._resolve_key_and_root(inter_key)
        parent, last_key, value = root_node._select_impl(
            inter_key,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )

        if parent is None or value is None:
            if throw_on_resolution_failure:
                raise InterpolationResolutionError(
                    f"Interpolation key '{inter_key}' not found"
                )
            else:
                return None
        assert isinstance(value, Node)
        return value

    def _evaluate_custom_resolver(
        self,
        key: Any,
        inter_type: str,
        inter_args: Tuple[Any, ...],
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
        inter_args_str: Tuple[str, ...],
    ) -> Optional["Node"]:
        from omegaconf import OmegaConf

        from .nodes import ValueNode

        resolver = OmegaConf.get_resolver(inter_type)
        if resolver is not None:
            root_node = self._get_root()
            try:
                value = resolver(root_node, inter_args, inter_args_str)
                return ValueNode(
                    value=value,
                    parent=self,
                    metadata=Metadata(
                        ref_type=Any, object_type=Any, key=key, optional=True
                    ),
                )
            except Exception as e:
                if throw_on_resolution_failure:
                    self._format_and_raise(key=None, value=None, cause=e)
                    assert False
                else:
                    return None
        else:
            if throw_on_resolution_failure:
                raise UnsupportedInterpolationType(
                    f"Unsupported interpolation type {inter_type}"
                )
            else:
                return None

    def _maybe_resolve_interpolation(
        self,
        parent: Optional["Container"],
        key: Any,
        value: "Node",
        throw_on_missing: bool,
        throw_on_resolution_failure: bool,
    ) -> Any:
        value_kind = get_value_kind(value)
        if value_kind != ValueKind.INTERPOLATION:
            return value

        parse_tree = parse(_get_value(value))
        return self._resolve_interpolation_from_parse_tree(
            parent=parent,
            value=value,
            key=key,
            parse_tree=parse_tree,
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )

    def resolve_parse_tree(
        self,
        parse_tree: ParserRuleContext,
        key: Optional[Any] = None,
        parent: Optional["Container"] = None,
        throw_on_missing: bool = True,
        throw_on_resolution_failure: bool = True,
    ) -> Any:
        """
        Resolve a given parse tree into its value.

        We make no assumption here on the type of the tree's root, so that the
        return value may be of any type.
        """
        from .nodes import StringNode

        # Common arguments to all callbacks.
        callback_args: Dict[str, Any] = dict(
            throw_on_missing=throw_on_missing,
            throw_on_resolution_failure=throw_on_resolution_failure,
        )

        def node_interpolation_callback(inter_key: str) -> Optional["Node"]:
            return self._resolve_node_interpolation(
                inter_key=inter_key, **callback_args
            )

        def resolver_interpolation_callback(
            name: str, args: Tuple[Any, ...], args_str: Tuple[str, ...]
        ) -> Optional["Node"]:
            return self._evaluate_custom_resolver(
                key=key,
                inter_type=name,
                inter_args=args,
                inter_args_str=args_str,
                **callback_args,
            )

        def quoted_string_callback(quoted_str: str) -> str:
            quoted_val = self._maybe_resolve_interpolation(
                key=key,
                parent=parent,
                value=StringNode(
                    value=quoted_str,
                    key=key,
                    parent=parent,
                    is_optional=False,
                ),
                **callback_args,
            )
            return str(quoted_val)

        visitor = GrammarVisitor(
            node_interpolation_callback=node_interpolation_callback,
            resolver_interpolation_callback=resolver_interpolation_callback,
            quoted_string_callback=quoted_string_callback,
        )
        return visitor.visit(parse_tree)

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

    def _invalidate_flags_cache(self) -> None:
        from .dictconfig import DictConfig
        from .listconfig import ListConfig

        # invalidate subtree cache only if the cache is initialized in this node.

        if self.__dict__["_flags_cache"] is not None:
            self.__dict__["_flags_cache"] = None
            if isinstance(self, DictConfig):
                content = self.__dict__["_content"]
                if isinstance(content, dict):
                    for value in self.__dict__["_content"].values():
                        value._invalidate_flags_cache()
            elif isinstance(self, ListConfig):
                content = self.__dict__["_content"]
                if isinstance(content, list):
                    for item in self.__dict__["_content"]:
                        item._invalidate_flags_cache()

    def _has_ref_type(self) -> bool:
        return self._metadata.ref_type is not Any


class SCMode(Enum):
    DICT = 1  # convert to plain dict
    DICT_CONFIG = 2  # Keep as OmegaConf DictConfig
