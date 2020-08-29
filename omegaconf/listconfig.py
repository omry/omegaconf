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

from ._utils import (
    ValueKind,
    _get_value,
    format_and_raise,
    get_value_kind,
    is_int,
    is_primitive_list,
    is_structured_config,
    type_str,
)
from .base import Container, ContainerMetadata, Node
from .basecontainer import BaseContainer
from .errors import (
    ConfigAttributeError,
    ConfigTypeError,
    ConfigValueError,
    KeyValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    ValidationError,
)


class ListConfig(BaseContainer, MutableSequence[Any]):

    _content: Union[List[Optional[Node]], None, str]

    def __init__(
        self,
        content: Union[List[Any], Tuple[Any, ...], str, None],
        key: Any = None,
        parent: Optional[Container] = None,
        element_type: Optional[Type[Any]] = None,
        is_optional: bool = True,
        ref_type: Union[Type[Any], Any] = Any,
    ) -> None:
        try:
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
            self.__dict__["_content"] = None
            self._set_value(value=content)
        except Exception as ex:
            format_and_raise(node=None, key=None, value=None, cause=ex, msg=str(ex))

    def _validate_get(self, key: Any, value: Any = None) -> None:
        if not isinstance(key, (int, slice)):
            raise KeyValidationError(
                "ListConfig indices must be integers or slices, not $KEY_TYPE"
            )

    def _validate_set(self, key: Any, value: Any) -> None:
        from omegaconf import OmegaConf

        self._validate_get(key, value)

        if self._get_flag("readonly"):
            raise ReadonlyConfigError("ListConfig is read-only")

        if 0 <= key < self.__len__():
            target = self._get_node(key)
            if target is not None:
                if value is None and not target._is_optional():
                    raise ValidationError(
                        "$FULL_KEY is not optional and cannot be assigned None"
                    )

        target_type = self._metadata.element_type
        value_type = OmegaConf.get_type(value)
        if is_structured_config(target_type):
            if (
                target_type is not None
                and value_type is not None
                and not issubclass(value_type, target_type)
            ):
                msg = (
                    f"Invalid type assigned : {type_str(value_type)} is not a "
                    f"subclass of {type_str(target_type)}. value: {value}"
                )
                raise ValidationError(msg)

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "ListConfig":
        res = ListConfig(content=[])
        for k, v in self.__dict__.items():
            res.__dict__[k] = copy.deepcopy(v, memo=memo)
        res._re_parent()
        return res

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        if self._is_missing() or self._is_none():
            return []
        return [str(x) for x in range(0, len(self))]

    def __len__(self) -> int:
        if self._is_none():
            return 0
        if self._is_missing():
            return 0
        assert isinstance(self.__dict__["_content"], list)
        return len(self.__dict__["_content"])

    def __setattr__(self, key: str, value: Any) -> None:
        self._format_and_raise(
            key=key,
            value=value,
            cause=ConfigAttributeError("ListConfig does not support attribute access"),
        )
        assert False

    def __getattr__(self, key: str) -> Any:
        if is_int(key):
            return self.__getitem__(int(key))
        else:
            self._format_and_raise(
                key=key,
                value=None,
                cause=ConfigAttributeError(
                    "ListConfig does not support attribute access"
                ),
            )

    def __getitem__(self, index: Union[int, slice]) -> Any:
        try:
            if self._is_missing():
                raise MissingMandatoryValue("ListConfig is missing")
            self._validate_get(index, None)
            if self._is_none():
                raise TypeError(
                    "ListConfig object representing None is not subscriptable"
                )

            assert isinstance(self.__dict__["_content"], list)
            if isinstance(index, slice):
                result = []
                start, stop, step = self._correct_index_params(index)
                for slice_idx in itertools.islice(
                    range(0, len(self)), start, stop, step
                ):
                    val = self._resolve_with_default(
                        key=slice_idx, value=self.__dict__["_content"][slice_idx]
                    )
                    result.append(val)
                if index.step and index.step < 0:
                    result.reverse()
                return result
            else:
                return self._resolve_with_default(
                    key=index, value=self.__dict__["_content"][index]
                )
        except Exception as e:
            self._format_and_raise(key=index, value=None, cause=e)

    def _correct_index_params(self, index: slice) -> Tuple[int, int, int]:
        start = index.start
        stop = index.stop
        step = index.step
        if index.start and index.start < 0:
            start = self.__len__() + index.start
        if index.stop and index.stop < 0:
            stop = self.__len__() + index.stop
        if index.step and index.step < 0:
            step = abs(step)
            if start and stop:
                if start > stop:
                    start, stop = stop + 1, start + 1
                else:
                    start = stop = 0
            elif not start and stop:
                start = list(range(self.__len__() - 1, stop, -step))[0]
                stop = None
            elif start and not stop:
                stop = start + 1
                start = (stop - 1) % step
            else:
                start = (self.__len__() - 1) % step
        return start, stop, step

    def _set_at_index(self, index: Union[int, slice], value: Any) -> None:
        self._set_item_impl(index, value)

    def __setitem__(self, index: Union[int, slice], value: Any) -> None:
        try:
            self._set_at_index(index, value)
        except Exception as e:
            self._format_and_raise(key=index, value=value, cause=e)

    def append(self, item: Any) -> None:
        try:
            from omegaconf.omegaconf import OmegaConf, _maybe_wrap

            index = len(self)
            self._validate_set(key=index, value=item)

            node = _maybe_wrap(
                ref_type=self.__dict__["_metadata"].element_type,
                key=index,
                value=item,
                is_optional=OmegaConf.is_optional(item),
                parent=self,
            )
            self.__dict__["_content"].append(node)
        except Exception as e:
            self._format_and_raise(key=index, value=item, cause=e)
            assert False

    def _update_keys(self) -> None:
        for i in range(len(self)):
            node = self._get_node(i)
            if node is not None:
                node._metadata.key = i

    def insert(self, index: int, item: Any) -> None:
        from omegaconf.omegaconf import OmegaConf, _maybe_wrap

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
                assert isinstance(self.__dict__["_content"], list)
                # insert place holder
                self.__dict__["_content"].insert(index, None)
                node = _maybe_wrap(
                    ref_type=self.__dict__["_metadata"].element_type,
                    key=index,
                    value=item,
                    is_optional=OmegaConf.is_optional(item),
                    parent=self,
                )
                self._validate_set(key=index, value=node)
                self._set_at_index(index, node)
                self._update_keys()
            except Exception:
                del self.__dict__["_content"][index]
                self._update_keys()
                raise
        except Exception as e:
            self._format_and_raise(key=index, value=item, cause=e)
            assert False

    def extend(self, lst: Iterable[Any]) -> None:
        assert isinstance(lst, (tuple, list, ListConfig))
        for x in lst:
            self.append(x)

    def remove(self, x: Any) -> None:
        del self[self.index(x)]

    def __delitem__(self, key: Union[int, slice]) -> None:
        if self._get_flag("readonly"):
            self._format_and_raise(
                key=key,
                value=None,
                cause=ReadonlyConfigError(
                    "Cannot delete item from read-only ListConfig"
                ),
            )
        del self.__dict__["_content"][key]
        self._update_keys()

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
            self._format_and_raise(
                key=None,
                value=None,
                cause=ConfigValueError("Item not found in ListConfig"),
            )
            assert False

    def count(self, x: Any) -> int:
        c = 0
        for item in self:
            if item == x:
                c = c + 1
        return c

    def copy(self) -> "ListConfig":
        return copy.copy(self)

    def _get_node(
        self, key: Union[int, slice], validate_access: bool = True
    ) -> Optional[Node]:
        try:
            if self._is_none():
                raise TypeError(
                    "Cannot get_node from a ListConfig object representing None"
                )
            if self._is_missing():
                raise MissingMandatoryValue("Cannot get_node from a missing ListConfig")
            assert isinstance(self.__dict__["_content"], list)
            if validate_access:
                self._validate_get(key)
            return self.__dict__["_content"][key]  # type: ignore
        except (IndexError, TypeError, MissingMandatoryValue, KeyValidationError) as e:
            if validate_access:
                self._format_and_raise(key=key, value=None, cause=e)
                assert False
            else:
                return None

    def get(self, index: int, default_value: Any = None) -> Any:
        try:
            if self._is_none():
                raise TypeError("Cannot get from a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot get from a missing ListConfig")
            self._validate_get(index, None)
            assert isinstance(self.__dict__["_content"], list)
            return self._resolve_with_default(
                key=index,
                value=self.__dict__["_content"][index],
                default_value=default_value,
            )
        except Exception as e:
            self._format_and_raise(key=index, value=None, cause=e)
            assert False

    def pop(self, index: int = -1) -> Any:
        try:
            if self._get_flag("readonly"):
                raise ReadonlyConfigError("Cannot pop from read-only ListConfig")
            if self._is_none():
                raise TypeError("Cannot pop from a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot pop from a missing ListConfig")

            assert isinstance(self.__dict__["_content"], list)
            ret = self._resolve_with_default(
                key=index, value=self._get_node(index), default_value=None
            )
            del self.__dict__["_content"][index]
            self._update_keys()
            return ret
        except KeyValidationError as e:
            self._format_and_raise(
                key=index, value=None, cause=e, type_override=ConfigTypeError
            )
            assert False
        except Exception as e:
            self._format_and_raise(key=index, value=None, cause=e)
            assert False

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

            assert isinstance(self.__dict__["_content"], list)
            self.__dict__["_content"].sort(key=key1, reverse=reverse)

        except Exception as e:
            self._format_and_raise(key=None, value=None, cause=e)
            assert False

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, (list, tuple)) or other is None:
            other = ListConfig(other)
            return ListConfig._list_eq(self, other)
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
        return self._iter_ex(resolve=True)

    def _iter_ex(self, resolve: bool) -> Iterator[Any]:
        try:
            if self._is_none():
                raise TypeError("Cannot iterate a ListConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot iterate a missing ListConfig")

            class MyItems(Iterator[Any]):
                def __init__(self, lst: ListConfig) -> None:
                    self.lst = lst
                    self.index = 0

                def __next__(self) -> Any:
                    if self.index == len(self.lst):
                        raise StopIteration()
                    if resolve:
                        v = self.lst[self.index]
                    else:
                        v = self.lst.__dict__["_content"][self.index]
                        if v is not None:
                            v = _get_value(v)
                    self.index = self.index + 1
                    return v

            assert isinstance(self.__dict__["_content"], list)
            return MyItems(self)
        except (ReadonlyConfigError, TypeError, MissingMandatoryValue) as e:
            self._format_and_raise(key=None, value=None, cause=e)
            assert False

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
            if not (is_primitive_list(value) or isinstance(value, ListConfig)):
                type_ = type(value)
                msg = (
                    f"Invalid value assigned : {type_.__name__} is not a "
                    f"subclass of ListConfig or list."
                )
                raise ValidationError(msg)
            self.__dict__["_content"] = []
            if isinstance(value, ListConfig):
                self.__dict__["_metadata"] = copy.deepcopy(value._metadata)
                self.__dict__["_metadata"].flags = {}
                for item in value._iter_ex(resolve=False):
                    self.append(item)
                self.__dict__["_metadata"].flags = copy.deepcopy(value._metadata.flags)
            elif is_primitive_list(value):
                for item in value:
                    self.append(item)

            if isinstance(value, ListConfig):
                self.__dict__["_metadata"].flags = value._metadata.flags

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
