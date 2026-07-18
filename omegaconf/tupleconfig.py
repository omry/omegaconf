import copy
import operator
from collections.abc import Sequence
from typing import Any, Dict, Iterable, Iterator, List, Optional, Tuple, Union

from ._utils import (
    ValueKind,
    _get_value,
    _is_missing_literal,
    _is_none,
    _resolve_optional,
    format_and_raise,
    get_tuple_item_types,
    get_value_kind,
    is_valid_value_annotation,
    is_variadic_tuple_annotation,
    make_tuple_annotation,
    normalize_tuple_annotation,
)
from .base import Box, ContainerMetadata, Node
from .basecontainer import BaseContainer
from .errors import (
    ConfigAttributeError,
    ConfigTypeError,
    ConfigValueError,
    KeyValidationError,
    MissingMandatoryValue,
    ValidationError,
)


class TupleConfig(BaseContainer, Sequence[Any]):
    _content: Union[List[Node], None, str]
    __hash__ = None  # type: ignore[assignment]

    def __init__(
        self,
        content: Union[List[Any], Tuple[Any, ...], "TupleConfig", str, None],
        key: Any = None,
        parent: Optional[Box] = None,
        ref_type: Any = Tuple[Any, ...],
        is_optional: bool = True,
        flags: Optional[Dict[str, bool]] = None,
    ) -> None:
        try:
            ref_type = normalize_tuple_annotation(ref_type)
            for item_type in get_tuple_item_types(ref_type):
                if item_type is not Ellipsis and not is_valid_value_annotation(
                    item_type
                ):
                    raise ValidationError(f"Unsupported value type: '{item_type}'")
            if isinstance(content, TupleConfig) and flags is None:
                flags = content._metadata.flags

            super().__init__(
                parent=parent,
                metadata=ContainerMetadata(
                    ref_type=ref_type,
                    object_type=tuple,
                    key=key,
                    optional=is_optional,
                    element_type=Any,
                    key_type=int,
                    flags=flags,
                ),
            )

            if isinstance(content, TupleConfig):
                metadata = copy.deepcopy(content._metadata)
                metadata.key = key
                metadata.ref_type = ref_type
                metadata.optional = is_optional
                metadata.flags = copy.deepcopy(flags)
                self.__dict__["_metadata"] = metadata
            self._set_value(content, flags=flags)
        except Exception as ex:
            format_and_raise(node=None, key=key, value=None, cause=ex, msg=str(ex))

    def _validate_get(self, key: Any, value: Any = None) -> None:
        if not isinstance(key, (int, slice)):
            raise KeyValidationError(
                "TupleConfig indices must be integers or slices, not $KEY_TYPE"
            )

    def _validate_set(self, key: Any, value: Any) -> None:
        raise ConfigTypeError("TupleConfig is immutable")

    def _raise_immutable(self, key: Any = None, value: Any = None) -> None:
        self._format_and_raise(
            key=key,
            value=value,
            cause=ConfigTypeError("TupleConfig is immutable"),
        )

    def __deepcopy__(self, memo: Dict[int, Any]) -> "TupleConfig":
        res = TupleConfig(None)
        res.__dict__["_metadata"] = copy.deepcopy(self.__dict__["_metadata"], memo)
        res.__dict__["_flags_cache"] = copy.deepcopy(
            self.__dict__["_flags_cache"], memo
        )

        src_content = self.__dict__["_content"]
        if isinstance(src_content, list):
            content_copy: List[Node] = []
            for value in src_content:
                old_parent = value.__dict__["_parent"]
                try:
                    value.__dict__["_parent"] = None
                    value_copy = copy.deepcopy(value, memo)
                    value_copy.__dict__["_parent"] = res
                    content_copy.append(value_copy)
                finally:
                    value.__dict__["_parent"] = old_parent
        else:
            content_copy = src_content  # type: ignore[assignment]

        res.__dict__["_content"] = content_copy
        res.__dict__["_parent"] = self.__dict__["_parent"]
        return res

    def copy(self) -> "TupleConfig":
        return copy.copy(self)

    def __repr__(self) -> str:
        if self._is_none() or self._is_missing() or self._is_interpolation():
            return super().__repr__()
        return repr(tuple(_get_value(node) for node in self._unresolved_nodes()))

    def __dir__(self) -> Iterable[str]:
        if self._is_missing() or self._is_none():
            return []
        return [str(index) for index in range(len(self))]

    def __setattr__(self, key: str, value: Any) -> None:
        self._format_and_raise(
            key=key,
            value=value,
            cause=ConfigAttributeError("TupleConfig does not support attribute access"),
        )

    def __getattr__(self, key: str) -> Any:
        if key in ("__members__", "__name__"):
            raise AttributeError()
        self._format_and_raise(
            key=key,
            value=None,
            cause=ConfigAttributeError("TupleConfig does not support attribute access"),
        )

    def _item_type(self, index: int) -> Any:
        item_types = get_tuple_item_types(self._metadata.ref_type)
        if is_variadic_tuple_annotation(self._metadata.ref_type):
            return item_types[0]
        return item_types[index]

    def _slice_type(self, index: slice) -> Any:
        if is_variadic_tuple_annotation(self._metadata.ref_type):
            return self._metadata.ref_type
        item_types = get_tuple_item_types(self._metadata.ref_type)
        indexes = range(*index.indices(len(self)))
        return make_tuple_annotation(tuple(item_types[item] for item in indexes))

    def _expanded_item_types(self) -> Tuple[Any, ...]:
        item_types = get_tuple_item_types(self._metadata.ref_type)
        if is_variadic_tuple_annotation(self._metadata.ref_type):
            return (item_types[0],) * len(self)
        return item_types

    def _unresolved_nodes(self) -> List[Node]:
        content = self.__dict__["_content"]
        assert isinstance(content, list)
        return content

    def _new_with_fixed_type(
        self, content: List[Any], item_types: Tuple[Any, ...]
    ) -> "TupleConfig":
        return TupleConfig(
            content=content,
            parent=self._get_parent(),
            ref_type=make_tuple_annotation(item_types),
            flags=copy.deepcopy(self._metadata.flags),
        )

    def __getitem__(self, key_or_index: Union[int, slice]) -> Any:
        index = key_or_index
        try:
            if self._is_missing():
                raise MissingMandatoryValue("TupleConfig is missing")
            self._validate_get(index)
            if self._is_none():
                raise TypeError(
                    "TupleConfig object representing None is not subscriptable"
                )

            content = self.__dict__["_content"]
            assert isinstance(content, list)
            if isinstance(index, slice):
                nodes = [content[item] for item in range(*index.indices(len(self)))]
                return TupleConfig(
                    content=nodes,
                    parent=self._get_parent(),
                    ref_type=self._slice_type(index),
                    flags=copy.deepcopy(self._metadata.flags),
                )
            return self._resolve_with_default(key=index, value=content[index])
        except Exception as ex:
            self._format_and_raise(key=index, value=None, cause=ex)

    def __setitem__(self, key: Any, value: Any) -> None:
        self._raise_immutable(key=key, value=value)

    def _set_item_for_resolution(self, key: int, value: Any) -> None:
        """Replace an element while materializing an interpolation in-place."""
        from omegaconf.omegaconf import _maybe_wrap

        content = self.__dict__["_content"]
        assert isinstance(content, list)
        optional, item_type = _resolve_optional(self._item_type(key))
        content[key] = _maybe_wrap(
            ref_type=item_type,
            key=key,
            value=value,
            is_optional=optional,
            parent=self,
        )

    def __delitem__(self, key: Any) -> None:
        self._raise_immutable(key=key)

    def append(self, item: Any) -> None:
        self._raise_immutable(value=item)

    def clear(self) -> None:
        self._raise_immutable()

    def extend(self, values: Iterable[Any]) -> None:
        self._raise_immutable(value=values)

    def insert(self, index: int, item: Any) -> None:
        self._raise_immutable(key=index, value=item)

    def pop(self, index: int = -1) -> Any:
        self._raise_immutable(key=index)

    def remove(self, item: Any) -> None:
        self._raise_immutable(value=item)

    def reverse(self) -> None:
        self._raise_immutable()

    def sort(self, *args: Any, **kwargs: Any) -> None:
        self._raise_immutable()

    def __iadd__(self, other: Any) -> "TupleConfig":
        self._raise_immutable(value=other)
        assert False

    def __imul__(self, other: Any) -> "TupleConfig":
        self._raise_immutable(value=other)
        assert False

    def _get_node(
        self,
        key: Union[int, slice],
        validate_access: bool = True,
        validate_key: bool = True,
        throw_on_missing_value: bool = False,
        throw_on_missing_key: bool = False,
    ) -> Union[Optional[Node], List[Optional[Node]]]:
        try:
            if self._is_none():
                raise TypeError(
                    "Cannot get_node from a TupleConfig object representing None"
                )
            if self._is_missing():
                raise MissingMandatoryValue(
                    "Cannot get_node from a missing TupleConfig"
                )
            if validate_access:
                self._validate_get(key)

            content = self.__dict__["_content"]
            assert isinstance(content, list)
            value = content[key]
            if isinstance(key, slice):
                assert isinstance(value, list)
                if throw_on_missing_value:
                    for item in value:
                        if item._is_missing():
                            raise MissingMandatoryValue("Missing mandatory value")
            else:
                assert isinstance(value, Node)
                if throw_on_missing_value and value._is_missing():
                    raise MissingMandatoryValue("Missing mandatory value: $KEY")
            return value
        except (IndexError, TypeError, MissingMandatoryValue, KeyValidationError) as ex:
            if isinstance(ex, MissingMandatoryValue) and throw_on_missing_value:
                raise
            if validate_access:
                self._format_and_raise(key=key, value=None, cause=ex)
            return None

    def get(self, index: int, default_value: Any = None) -> Any:
        try:
            node = self._get_node(index)
            assert isinstance(node, Node)
            return self._resolve_with_default(index, node, default_value)
        except Exception as ex:
            self._format_and_raise(key=index, value=None, cause=ex)

    def index(
        self, item: Any, start: Optional[int] = None, stop: Optional[int] = None
    ) -> int:
        start = 0 if start is None else start
        stop = len(self) if stop is None else stop
        for index in range(*slice(start, stop).indices(len(self))):
            if self[index] == item:
                return index
        self._format_and_raise(
            key=None,
            value=None,
            cause=ConfigValueError("Item not found in TupleConfig"),
        )
        assert False

    def count(self, item: Any) -> int:
        return sum(1 for value in self if value == item)

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, TupleConfig):
            if self._is_missing() or other._is_missing():
                return self._is_missing() and other._is_missing()
            if self._is_none() or other._is_none():
                return self._is_none() and other._is_none()
        if self._is_missing():
            return _is_missing_literal(other)
        if other is None:
            return self._is_none()
        if isinstance(other, TupleConfig):
            if len(self) != len(other):
                return False
            return all(
                BaseContainer._item_eq(self, index, other, index)
                for index in range(len(self))
            )
        if isinstance(other, tuple):
            if self._is_none() or self._is_interpolation():
                return False
            return len(self) == len(other) and all(
                self[index] == other[index] for index in range(len(self))
            )
        return False

    def __ne__(self, other: Any) -> bool:
        return not self.__eq__(other)

    class TupleIterator(Iterator[Any]):
        def __init__(self, value: "TupleConfig", resolve: bool) -> None:
            self.resolve = resolve
            self.iterator = iter(value.__dict__["_content"])
            self.index = 0

        def __next__(self) -> Any:
            node = next(self.iterator)
            if self.resolve:
                node = node._dereference_node()
                if node._is_missing():
                    raise MissingMandatoryValue(f"Missing value at index {self.index}")
            self.index += 1
            return _get_value(node)

    def _iter_ex(self, resolve: bool) -> Iterator[Any]:
        try:
            if self._is_none():
                raise TypeError("Cannot iterate a TupleConfig object representing None")
            if self._is_missing():
                raise MissingMandatoryValue("Cannot iterate a missing TupleConfig")
            return TupleConfig.TupleIterator(self, resolve)
        except (TypeError, MissingMandatoryValue) as ex:
            self._format_and_raise(key=None, value=None, cause=ex)
            assert False

    def __iter__(self) -> Iterator[Any]:
        return self._iter_ex(resolve=True)

    def __contains__(self, item: Any) -> bool:
        return any(value == item for value in self)

    def __add__(self, other: Any) -> "TupleConfig":
        if isinstance(other, TupleConfig):
            other_content: List[Any] = other._unresolved_nodes()
            other_types = other._expanded_item_types()
        elif isinstance(other, tuple):
            other_content = list(other)
            other_types = (Any,) * len(other)
        else:
            raise TypeError(
                f'can only concatenate tuple (not "{type(other).__name__}") to tuple'
            )
        return self._new_with_fixed_type(
            self._unresolved_nodes() + other_content,
            self._expanded_item_types() + other_types,
        )

    def __radd__(self, other: Any) -> "TupleConfig":
        if isinstance(other, TupleConfig):
            return other + self
        if not isinstance(other, tuple):
            raise TypeError(
                f'can only concatenate tuple (not "{type(other).__name__}") to tuple'
            )
        return self._new_with_fixed_type(
            list(other) + self._unresolved_nodes(),
            (Any,) * len(other) + self._expanded_item_types(),
        )

    def __mul__(self, count: Any) -> "TupleConfig":
        try:
            count = operator.index(count)
        except TypeError:
            raise TypeError(
                f"can't multiply sequence by non-int of type '{type(count).__name__}'"
            ) from None

        if count <= 0:
            return self._new_with_fixed_type([], ())

        content = self._unresolved_nodes() * count
        if is_variadic_tuple_annotation(self._metadata.ref_type):
            return TupleConfig(
                content=content,
                parent=self._get_parent(),
                ref_type=self._metadata.ref_type,
                flags=copy.deepcopy(self._metadata.flags),
            )
        return self._new_with_fixed_type(content, self._expanded_item_types() * count)

    def __rmul__(self, count: Any) -> "TupleConfig":
        return self * count

    def _set_value(self, value: Any, flags: Optional[Dict[str, bool]] = None) -> None:
        previous_content = self.__dict__["_content"]
        previous_metadata = self.__dict__["_metadata"]
        try:
            self._set_value_impl(value, flags)
        except Exception:
            self.__dict__["_content"] = previous_content
            self.__dict__["_metadata"] = previous_metadata
            raise

    def _set_value_impl(
        self, value: Any, flags: Optional[Dict[str, bool]] = None
    ) -> None:
        from omegaconf import MISSING
        from omegaconf.listconfig import ListConfig
        from omegaconf.omegaconf import _maybe_wrap

        value = _get_value(value)
        kind = get_value_kind(value, strict_interpolation_validation=True)
        if _is_none(value):
            if not self._is_optional():
                raise ValidationError(
                    "Non optional TupleConfig cannot be constructed from None"
                )
            self.__dict__["_content"] = None
            self._metadata.object_type = None
            return
        if kind is ValueKind.MANDATORY_MISSING:
            self.__dict__["_content"] = MISSING
            self._metadata.object_type = None
            return
        if kind is ValueKind.INTERPOLATION:
            self.__dict__["_content"] = value
            self._metadata.object_type = None
            return
        if not isinstance(value, (list, tuple, ListConfig, TupleConfig)):
            raise ValidationError(
                f"Invalid value assigned: {type(value).__name__} is not a TupleConfig, list or tuple."
            )

        values = (
            list(value._iter_ex(resolve=False))
            if isinstance(value, (ListConfig, TupleConfig))
            else list(value)
        )
        item_types = get_tuple_item_types(self._metadata.ref_type)
        if not is_variadic_tuple_annotation(self._metadata.ref_type) and len(
            values
        ) != len(item_types):
            raise ValidationError(
                f"TupleConfig length {len(values)} does not match type hint length {len(item_types)}"
            )

        content: List[Node] = []
        self.__dict__["_content"] = content
        for index, item in enumerate(values):
            if get_value_kind(item) is ValueKind.MANDATORY_MISSING:
                raise ValidationError("TupleConfig elements cannot be missing")
            if isinstance(item, Node):
                item = copy.deepcopy(item)
            optional, item_type = _resolve_optional(self._item_type(index))
            node = _maybe_wrap(
                ref_type=item_type,
                key=index,
                value=item,
                is_optional=optional,
                parent=self,
            )
            content.append(node)
        self._metadata.object_type = tuple
