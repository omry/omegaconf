import copy
import itertools
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Iterator,
    List,
    MutableSequence,
    Optional,
    Tuple,
    Union,
)

from ._utils import ValueKind, get_value_kind, is_primitive_list, isint
from .base import Container, Node
from .basecontainer import BaseContainer
from .errors import KeyValidationError, ReadonlyConfigError, UnsupportedValueType
from .nodes import AnyNode, ValueNode


class ListConfig(BaseContainer, MutableSequence[Any]):
    def __init__(
        self,
        content: Union[List[Any], Tuple[Any, ...]],
        parent: Optional[Container] = None,
        element_type: Any = Any,
    ) -> None:
        super().__init__(parent=parent, element_type=element_type)
        if get_value_kind(content) == ValueKind.MANDATORY_MISSING:
            self.__dict__["_missing"] = True
            self.__dict__["content"] = None
        else:
            assert is_primitive_list(content) or isinstance(content, ListConfig)
            self.__dict__["_missing"] = False
            self.__dict__["content"] = []
            for item in content:
                self.append(item)

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "ListConfig":
        res = ListConfig(content=[])
        for key in ["content", "flags", "_element_type", "_missing"]:
            res.__dict__[key] = copy.deepcopy(self.__dict__[key], memo=memo)
        res._re_parent()
        return res

    def __getattr__(self, key: str) -> Any:
        if isinstance(key, str) and isint(key):
            return self.__getitem__(int(key))
        else:
            raise AttributeError()

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        return [str(x) for x in range(0, len(self))]

    def __len__(self) -> int:
        if self._is_missing():
            return 0
        return len(self.content)

    def __getitem__(self, index: Union[int, slice]) -> Any:
        assert isinstance(index, (int, slice))
        if isinstance(index, slice):
            result = []
            for slice_idx in itertools.islice(
                range(0, len(self)), index.start, index.stop, index.step
            ):
                val = self._resolve_with_default(
                    key=slice_idx, value=self.content[slice_idx], default_value=None
                )
                result.append(val)
            return result
        else:
            return self._resolve_with_default(
                key=index, value=self.content[index], default_value=None
            )

    def _set_at_index(self, index: Union[int, slice], value: Any) -> None:
        if not isinstance(index, int):
            raise KeyValidationError(f"Key type {type(index).__name__} is not an int")

        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(str(index)))

        if isinstance(value, BaseContainer):
            value = copy.deepcopy(value)
            value._set_parent(self)

        try:

            self._set_item_impl(index, value)

        except UnsupportedValueType:
            raise UnsupportedValueType(
                "key {}: {} is not a supported type".format(
                    self.get_full_key(str(index)), type(value).__name__
                )
            )

    def __setitem__(self, index: Union[int, slice], value: Any) -> None:
        self._set_at_index(index, value)

    def append(self, item: Any) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(f"{len(self)}"))

        try:
            from omegaconf.omegaconf import _maybe_wrap

            self.__dict__["content"].append(
                _maybe_wrap(
                    annotated_type=self.__dict__["_element_type"],
                    value=item,
                    is_optional=True,
                    parent=self,
                )
            )
        except UnsupportedValueType:
            full_key = self.get_full_key(f"{len(self)}")
            raise UnsupportedValueType(
                f"key {full_key}: {type(item).__name__} is not a supported type"
            )

    def insert(self, index: int, item: Any) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(str(index)))
        try:
            self.content.insert(index, AnyNode(None))
            self._set_at_index(index, item)
        except Exception:
            del self.__dict__["content"][index]
            raise

    def extend(self, lst: Iterable[Any]) -> None:
        assert isinstance(lst, (tuple, list, ListConfig))
        for x in lst:
            self.append(x)

    def remove(self, x: Any) -> None:
        del self[self.index(x)]

    def clear(self) -> None:
        del self[:]

    def index(
        self, x: Any, start: Optional[int] = None, end: Optional[int] = None
    ) -> int:
        if start is None:
            start = 0
        if end is None:
            end = len(self)
        assert start >= 0
        assert end <= len(self)
        found_idx = -1
        for idx in range(start, end):
            item = self[idx]
            if x == item:
                found_idx = idx
                break
        if found_idx != -1:
            return found_idx
        else:
            raise ValueError("Item not found in ListConfig")

    def count(self, x: Any) -> int:
        c = 0
        for item in self:
            if item == x:
                c = c + 1
        return c

    def copy(self) -> "ListConfig":
        return copy.copy(self)

    def get_node(self, index: int) -> Node:
        assert type(index) == int
        return self.__dict__["content"][index]  # type: ignore

    def get(self, index: int, default_value: Any = None) -> Any:
        assert type(index) == int
        return self._resolve_with_default(
            key=index, value=self.content[index], default_value=default_value
        )

    def pop(self, index: int = -1) -> Any:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(
                self.get_full_key(str(index if index != -1 else ""))
            )
        return self._resolve_with_default(
            key=index, value=self.content.pop(index), default_value=None
        )

    def sort(
        self, key: Optional[Callable[[Any], Any]] = None, reverse: bool = False
    ) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError()

        if key is None:

            def key1(x: Any) -> Any:
                return x.value()

        else:

            def key1(x: Any) -> Any:
                return key(x.value())  # type: ignore

        self.content.sort(key=key1, reverse=reverse)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, list):
            return BaseContainer._list_eq(self, ListConfig(other))
        if isinstance(other, ListConfig):
            return BaseContainer._list_eq(self, other)
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def __iter__(self) -> Iterator[Any]:
        class MyItems(Iterator[Any]):
            def __init__(self, lst: List[Any]) -> None:
                self.lst = lst
                self.iterator = iter(lst)

            def __next__(self) -> Any:
                return self.next()

            def next(self) -> Any:
                v = next(self.iterator)
                if isinstance(v, ValueNode):
                    v = v.value()
                return v

        return MyItems(self.content if not self._is_missing() else [])

    def __add__(self, other: Union[List[Any], "ListConfig"]) -> "ListConfig":
        # res is sharing this list's parent to allow interpolation to work as expected
        res = ListConfig(parent=self._get_parent(), content=[])
        res.extend(self)
        res.extend(other)
        return res

    def __iadd__(self, other: Iterable[Any]) -> "ListConfig":
        self.extend(other)
        return self

    def __contains__(self, item: Any) -> bool:
        for x in iter(self):
            if x == item:
                return True
        return False
