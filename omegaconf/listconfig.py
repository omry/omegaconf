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
from .base import Container, ContainerMetadata, Node
from .basecontainer import BaseContainer
from .errors import (
    KeyValidationError,
    ReadonlyConfigError,
    UnsupportedValueType,
    ValidationError,
)
from .nodes import AnyNode, ValueNode


class ListConfig(BaseContainer, MutableSequence[Any]):
    def __init__(
        self,
        content: Union[List[Any], Tuple[Any, ...], str, None],
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
        element_type: Any = Any,
    ) -> None:
        super().__init__(
            parent=parent,
            metadata=ContainerMetadata(
                key=key, optional=is_optional, element_type=element_type
            ),
        )
        self._set_value(value=content)

    def _validate_get(self, index: Any) -> None:
        if not isinstance(index, (int, slice)):
            raise KeyValidationError(f"Key type {type(index).__name__} is invalid")

    def _validate_set(self, index: Any, value: Any) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self._get_full_key(f"{index}"))

        if 0 <= index < self.__len__():
            target = self.get_node(index)
            if isinstance(target, Container):
                if value is None and not target._is_optional():
                    raise ValidationError(
                        "Non optional ListConfig node cannot be assigned None"
                    )

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "ListConfig":
        res = ListConfig(content=[])
        for k, v in self.__dict__.items():
            res.__dict__[k] = copy.deepcopy(v, memo=memo)
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
        return len(self._content)

    def __getitem__(self, index: Union[int, slice]) -> Any:
        assert isinstance(index, (int, slice))
        self._validate_get(index)

        if isinstance(index, slice):
            result = []
            for slice_idx in itertools.islice(
                range(0, len(self)), index.start, index.stop, index.step
            ):
                val = self._resolve_with_default(
                    key=slice_idx, value=self._content[slice_idx], default_value=None
                )
                result.append(val)
            return result
        else:
            return self._resolve_with_default(
                key=index, value=self._content[index], default_value=None
            )

    def _set_at_index(self, index: Union[int, slice], value: Any) -> None:
        try:
            self._set_item_impl(index, value)
        except UnsupportedValueType:
            full_key = self._get_full_key(str(index))

            raise UnsupportedValueType(
                f"{type(value).__name__} is not a supported type (key: {full_key})"
            )

    def __setitem__(self, index: Union[int, slice], value: Any) -> None:
        self._set_at_index(index, value)

    def append(self, item: Any) -> None:
        index = len(self)
        self._validate_set(index=index, value=item)

        try:
            from omegaconf.omegaconf import OmegaConf, _maybe_wrap

            self.__dict__["_content"].append(
                _maybe_wrap(
                    annotated_type=self._metadata.element_type,
                    key=index,
                    value=item,
                    is_optional=OmegaConf.is_optional(item),
                    parent=self,
                )
            )
        except UnsupportedValueType:
            full_key = self._get_full_key(f"{len(self)}")
            raise UnsupportedValueType(
                f"{type(item).__name__} is not a supported type (key: {full_key})"
            )

    def insert(self, index: int, item: Any) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self._get_full_key(str(index)))
        try:
            self._content.insert(index, AnyNode(None))
            self._set_at_index(index, item)
        except Exception:
            del self.__dict__["_content"][index]
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
        return self.__dict__["_content"][index]  # type: ignore

    def get(self, index: int, default_value: Any = None) -> Any:
        assert type(index) == int
        return self._resolve_with_default(
            key=index, value=self._content[index], default_value=default_value
        )

    def pop(self, index: int = -1) -> Any:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(
                self._get_full_key(str(index if index != -1 else ""))
            )
        return self._resolve_with_default(
            key=index, value=self._content.pop(index), default_value=None
        )

    def sort(
        self, key: Optional[Callable[[Any], Any]] = None, reverse: bool = False
    ) -> None:
        if self._get_flag("readonly"):
            raise ReadonlyConfigError()

        if key is None:

            def key1(x: Any) -> Any:
                return x._value()

        else:

            def key1(x: Any) -> Any:
                return key(x._value())  # type: ignore

        self._content.sort(key=key1, reverse=reverse)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (list, tuple)) or other is None:
            return ListConfig._list_eq(self, ListConfig(other))
        if other is None or isinstance(other, ListConfig):
            return ListConfig._list_eq(self, other)
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
                    v = v._value()
                return v

        return MyItems(self._content)

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

    def _set_value(self, value: Any) -> None:
        from omegaconf import OmegaConf

        if OmegaConf.is_none(value):
            if not self._is_optional():
                raise ValidationError(
                    "Non optional ListConfig cannot be constructed from None"
                )
            self.__dict__["_content"] = None
        elif get_value_kind(value) == ValueKind.MANDATORY_MISSING:
            self.__dict__["_content"] = "???"
        elif get_value_kind(value) in (
            ValueKind.INTERPOLATION,
            ValueKind.STR_INTERPOLATION,
        ):
            self.__dict__["_content"] = value
        else:
            assert is_primitive_list(value) or isinstance(value, ListConfig)
            self.__dict__["_content"] = []
            for item in value:
                self.append(item)

    @staticmethod
    def _list_eq(l1: Optional["ListConfig"], l2: Optional["ListConfig"]) -> bool:

        l1_none = l1.__dict__["_content"] is None
        l2_none = l2.__dict__["_content"] is None
        if l1_none and l2_none:
            return True
        if l1_none != l2_none:
            return False

        assert isinstance(l1, ListConfig)
        assert isinstance(l2, ListConfig)
        if len(l1) != len(l2):
            return False
        for i in range(len(l1)):
            if not BaseContainer._item_eq(l1, i, l2, i):
                return False

        return True
