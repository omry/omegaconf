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
    Type,
    Union,
)

from ._utils import ValueKind, get_value_kind, is_primitive_list
from .base import Container, ContainerMetadata, Node
from .basecontainer import BaseContainer
from .errors import (
    KeyValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    ValidationError,
)
from .nodes import AnyNode, ValueNode


class ListConfig(BaseContainer, MutableSequence[Any]):

    _content: Union[List[Optional[Node]], None, str]

    def __init__(
        self,
        content: Union[List[Any], Tuple[Any, ...], str, None],
        key: Any = None,
        parent: Optional[Container] = None,
        ref_type: Optional[Type[Any]] = None,
        is_optional: bool = True,
        element_type: Optional[Type[Any]] = None,
    ) -> None:
        super().__init__(
            parent=parent,
            metadata=ContainerMetadata(
                ref_type=ref_type,
                object_type=list,
                key=key,
                optional=is_optional,
                element_type=element_type,
                key_type=int,
            ),
        )
        self._content = None
        self._set_value(value=content)

    def _validate_get(self, key: Any, value: Any = None) -> None:
        if not isinstance(key, (int, slice)):
            raise KeyValidationError("Invalid key type '$KEY_TYPE'")

    def _validate_set(self, key: Any, value: Any) -> None:

        self._validate_get(key, value)

        if self._get_flag("readonly"):
            raise ReadonlyConfigError("ListConfig is read-only")

        if 0 <= key < self.__len__():
            target = self.get_node(key)
            if target is not None:
                if value is None and not target._is_optional():
                    raise ValidationError(
                        "$FULL_KEY is not optional and cannot be assigned None"
                    )

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "ListConfig":
        res = ListConfig(content=[])
        for k, v in self.__dict__.items():
            res.__dict__[k] = copy.deepcopy(v, memo=memo)
        res._re_parent()
        return res

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        return [str(x) for x in range(0, len(self))]

    def __len__(self) -> int:
        if self._is_none():
            return 0
        if self._is_missing():
            return 0
        assert isinstance(self._content, list)
        return len(self._content)

    def __getitem__(self, index: Union[int, slice]) -> Any:
        try:
            if self._is_missing():
                raise MissingMandatoryValue("ListConfig is missing")
            self._validate_get(index, None)
            if self._is_none():
                raise TypeError(
                    "ListConfig object representing None is not subscriptable"
                )

            assert isinstance(self._content, list)
            if isinstance(index, slice):
                result = []
                for slice_idx in itertools.islice(
                    range(0, len(self)), index.start, index.stop, index.step
                ):
                    val = self._resolve_with_default(
                        key=slice_idx, value=self._content[slice_idx]
                    )
                    result.append(val)
                return result
            else:
                return self._resolve_with_default(key=index, value=self._content[index])
        except Exception as e:
            self._translate_exception(e=e, key=index, value=None)

    def _set_at_index(self, index: Union[int, slice], value: Any) -> None:
        self._set_item_impl(index, value)

    def __setitem__(self, index: Union[int, slice], value: Any) -> None:
        try:
            self._set_at_index(index, value)
        except Exception as e:
            self._translate_exception(e=e, key=index, value=value)

    def append(self, item: Any) -> None:
        try:
            from omegaconf.omegaconf import OmegaConf, _maybe_wrap

            index = len(self)
            self._validate_set(key=index, value=item)

            node = _maybe_wrap(
                ref_type=self._metadata.element_type,
                key=index,
                value=item,
                is_optional=OmegaConf.is_optional(item),
                parent=self,
            )
            self.__dict__["_content"].append(node)
        except Exception as e:
            self._translate_exception(e=e, key=index, value=item)
            assert False  # pragma: no cover

    def insert(self, index: int, item: Any) -> None:
        try:
            if self._get_flag("readonly"):
                raise ReadonlyConfigError("Cannot insert into a read-only ListConfig")
            if self._is_none():
                raise TypeError(
                    "Cannot insert into ListConfig object representing None"
                )
            if self._is_missing():
                raise MissingMandatoryValue("Cannot insert into missing ListConfig")
            try:
                # TODO: not respecting element type
                # TODO: this and other list ops like delete are not updating key in list element nodes
                # from omegaconf.omegaconf import OmegaConf, _maybe_wrap
                #
                # index = len(self)
                # self._validate_set(key=index, value=item)
                #
                # node = _maybe_wrap(
                #     ref_type=self._metadata.element_type,
                #     key=index,
                #     value=item,
                #     is_optional=OmegaConf.is_optional(item),
                #     parent=self,
                # )
                assert isinstance(self._content, list)
                self._content.insert(index, AnyNode(None))
                self._set_at_index(index, item)
            except Exception:
                del self.__dict__["_content"][index]
                raise
        except Exception as e:
            self._translate_exception(e=e, key=index, value=item)
            assert False  # pragma: no cover

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
            self._translate_exception(
                e=ValueError("Item not found in ListConfig"), key=None, value=None
            )
            assert False  # pragma: no cover

    def count(self, x: Any) -> int:
        c = 0
        for item in self:
            if item == x:
                c = c + 1
        return c

    def copy(self) -> "ListConfig":
        return copy.copy(self)

    def get_node(self, key: Any) -> Optional[Node]:
        return self.get_node_ex(key)

    def get_node_ex(self, key: Any, validate_access: bool = True) -> Optional[Node]:
        if self._is_none():
            raise TypeError(
                "Cannot get_node from a ListConfig object representing None"
            )
        if self._is_missing():
            raise MissingMandatoryValue("Cannot get_node from a missing ListConfig")

        try:
            assert isinstance(self._content, list)
            return self._content[key]  # type: ignore
        except (IndexError, TypeError) as e:
            if validate_access:
                self._translate_exception(e=e, key=key, value=None)
                assert False  # pragma: no cover
            else:
                return None

    def get(self, index: int, default_value: Any = None) -> Any:
        try:
            if self._is_none():
                raise TypeError("Cannot get from a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot get from a missing ListConfig")
            self._validate_get(index, None)
            assert isinstance(self._content, list)
            return self._resolve_with_default(
                key=index, value=self._content[index], default_value=default_value
            )
        except Exception as e:
            self._translate_exception(e=e, key=index, value=None)
            assert False  # pragma: no cover

    def pop(self, index: int = -1) -> Any:
        try:
            if self._get_flag("readonly"):
                raise ReadonlyConfigError("Cannot pop from read-only ListConfig")
            if self._is_none():
                raise TypeError("Cannot pop from a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot pop from a missing ListConfig")

            assert isinstance(self._content, list)

            return self._resolve_with_default(
                key=index, value=self._content.pop(index), default_value=None
            )
        except (ReadonlyConfigError, IndexError) as e:
            self._translate_exception(e=e, key=index, value=None)
            assert False  # pragma: no cover

    def sort(
        self, key: Optional[Callable[[Any], Any]] = None, reverse: bool = False
    ) -> None:
        try:
            if self._get_flag("readonly"):
                raise ReadonlyConfigError("Cannot sort a read-only ListConfig")
            if self._is_none():
                raise TypeError("Cannot sort a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot sort a missing ListConfig")

            if key is None:

                def key1(x: Any) -> Any:
                    return x._value()

            else:

                def key1(x: Any) -> Any:
                    return key(x._value())  # type: ignore

            assert isinstance(self._content, list)
            self._content.sort(key=key1, reverse=reverse)

        except (ReadonlyConfigError, IndexError) as e:
            self._translate_exception(e=e, key=None, value=None)
            assert False  # pragma: no cover

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
        try:
            if self._is_none():
                raise TypeError("Cannot iterate on ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot iterate on a missing ListConfig")

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

            assert isinstance(self._content, list)
            return MyItems(self._content)
        except (ReadonlyConfigError, TypeError, MissingMandatoryValue) as e:
            self._translate_exception(e=e, key=None, value=None)
            assert False  # pragma: no cover

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
            if isinstance(value, ListConfig):
                self._metadata = copy.deepcopy(value._metadata)
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
