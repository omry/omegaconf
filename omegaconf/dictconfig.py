import copy
from enum import Enum
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from ._utils import (
    _re_parent,
    get_structured_config_data,
    is_structured_config,
    is_structured_config_frozen,
)
from .base import Container, Node
from .basecontainer import BaseContainer
from .errors import (
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
    UnsupportedKeyType,
    UnsupportedValueType,
    ValidationError,
)
from .nodes import ValueNode


class DictConfig(BaseContainer):
    def __init__(
        self,
        content: Union[Dict[str, Any], Any],
        parent: Optional[Container] = None,
        element_type: type = Any,  # type: ignore
    ) -> None:
        super().__init__(element_type=element_type, parent=parent)

        self.__dict__["content"] = {}
        self.__dict__["_type"] = None
        if is_structured_config(content):
            d = get_structured_config_data(content)
            for k, v in d.items():
                self.__setitem__(k, v)

            if is_structured_config_frozen(content):
                self._set_flag("readonly", True)

            if isinstance(content, type):
                self.__dict__["_type"] = content
            else:
                self.__dict__["_type"] = type(content)

        else:
            for k, v in content.items():
                self.__setitem__(k, v)

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "DictConfig":
        res = DictConfig({})
        res.__dict__["content"] = copy.deepcopy(self.__dict__["content"], memo=memo)
        res.__dict__["flags"] = copy.deepcopy(self.__dict__["flags"], memo=memo)
        res.__dict__["_element_type"] = copy.deepcopy(
            self.__dict__["_element_type"], memo=memo
        )

        res.__dict__["_type"] = copy.deepcopy(self.__dict__["_type"], memo=memo)
        _re_parent(res)
        return res

    def __copy__(self) -> "DictConfig":
        res = DictConfig(content={}, element_type=self.__dict__["_element_type"])
        res.__dict__["content"] = copy.copy(self.__dict__["content"])
        res.__dict__["_type"] = self.__dict__["_type"]
        res.__dict__["flags"] = copy.copy(self.__dict__["flags"])
        _re_parent(res)
        return res

    def copy(self) -> "DictConfig":
        return copy.copy(self)

    def __setitem__(self, key: Union[str, Enum], value: Any) -> None:
        if isinstance(key, Enum):
            key = key.name

        if not isinstance(key, str):
            raise UnsupportedKeyType(f"Key type is not str ({type(key).__name__})")

        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))

        self._validate_access(key)
        self._validate_type(key, value)

        if isinstance(value, BaseContainer):
            value = copy.deepcopy(value)
            value._set_parent(self)

        try:
            self._set_item_impl(key, value)
        except UnsupportedValueType:
            raise UnsupportedValueType(
                f"key {self.get_full_key(key)}: {type(value).__name__} is not a supported type"
            )

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        return self.__dict__["content"].keys()  # type: ignore

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Allow assigning attributes to DictConfig
        :param key:
        :param value:
        :return:
        """
        self.__setitem__(key, value)

    def __getattr__(self, key: str) -> Any:
        """
        Allow accessing dictionary values as attributes
        :param key:
        :return:
        """
        # PyCharm is sometimes inspecting __members__. returning None or throwing is
        # confusing it and it prints an error when inspecting this object.
        if key == "__members__":
            return {}

        # Sometimes we get queried for name.
        if key == "__name__":
            return None

        return self.get(key=key, default_value=None)

    def __getitem__(self, key: Union[str, Enum]) -> Any:
        """
        Allow map style access
        :param key:
        :return:
        """
        return self.get(key=key, default_value=None)

    def get(self, key: Union[str, Enum], default_value: Any = None) -> Any:
        if isinstance(key, Enum):
            key = key.name

        if not isinstance(key, str):
            raise UnsupportedKeyType(f"Key type is not str ({type(key).__name__})")

        return self._resolve_with_default(
            key=key,
            value=self.get_node(key, default_value),
            default_value=default_value,
        )

    def get_node(
        self,
        key: Union[str, Enum],
        default_value: Any = None,
        validate_access: bool = True,
    ) -> Node:
        if isinstance(key, Enum):
            key = key.name

        value: Node = self.__dict__["content"].get(key)
        if validate_access:
            try:
                self._validate_access(key)
            except (KeyError, AttributeError):
                if default_value is not None:
                    value = default_value
                else:
                    raise
        else:
            if default_value is not None:
                value = default_value
        return value

    __marker = object()

    def pop(self, key: Union[str, Enum], default: Any = __marker) -> Any:
        if isinstance(key, Enum):
            key = key.name
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))
        val = self.content.pop(key, default)
        if val is self.__marker:
            raise KeyError(key)
        return val

    def keys(self) -> Any:
        return self.content.keys()

    def __contains__(self, key: Union[str, Enum]) -> bool:
        """
        A key is contained in a DictConfig if there is an associated value and
        it is not a mandatory missing value ('???').
        :param key:
        :return:
        """

        str_key: str
        if isinstance(key, Enum):
            str_key = key.name
        else:
            str_key = key

        try:
            node: Optional[Node] = self.get_node(str_key)
        except (KeyError, AttributeError):
            node = None

        if node is None:
            return False
        else:
            try:
                self._resolve_with_default(str_key, node, None)
                return True
            except UnsupportedInterpolationType:
                # Value that has unsupported interpolation counts as existing.
                return True
            except (MissingMandatoryValue, KeyError):
                return False

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def items(
        self, resolve: bool = True, keys: Optional[List[str]] = None
    ) -> Iterator[Any]:
        class MyItems(Iterator[Any]):
            def __init__(self, m: DictConfig) -> None:
                self.map = m
                self.iterator = iter(m)

            def __iter__(self) -> Iterator[Any]:
                return self

            def __next__(self) -> Tuple[str, Any]:
                k, v = self._next_pair()
                if keys is not None:
                    while k not in keys:
                        k, v = self._next_pair()
                return k, v

            def _next_pair(self) -> Tuple[str, Any]:
                k = next(self.iterator)
                if resolve:
                    v = self.map.get(k)
                else:
                    v = self.map.content[k]
                    if isinstance(v, ValueNode):
                        v = v.value()
                kv = (k, v)
                return kv

        return MyItems(self)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, dict):
            return BaseContainer._dict_conf_eq(self, DictConfig(other))
        if isinstance(other, DictConfig):
            return BaseContainer._dict_conf_eq(self, other)
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def _validate_access(self, key: str) -> None:
        is_typed = self.__dict__["_type"] is not None
        is_closed = self._get_flag("struct") is True
        node_open = self._get_node_flag("struct") is False
        if key not in self.content:
            if is_typed and node_open:
                return
            if is_typed or is_closed:
                msg = "Accessing unknown key in a struct : {}".format(
                    self.get_full_key(key)
                )
                if is_closed:
                    raise AttributeError(msg)
                else:
                    raise KeyError(msg)

    def _validate_type(self, key: str, value: Any) -> None:
        if self.__dict__["_type"] is not None:
            child = self.get_node(key)
            if child is None:
                return
            type_ = child.__dict__["_type"] if isinstance(child, DictConfig) else None
            is_typed = type_ is not None
            mismatch_type = is_typed and type(value) != type_

            if mismatch_type:
                raise ValidationError(
                    f"Invalid type assigned : {type_.__name__} != {type(value).__name__}"
                )
