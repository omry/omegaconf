import copy
import math
from enum import Enum
from typing import Any, Dict, Optional, Type, Union

from omegaconf._utils import _is_interpolation
from omegaconf.base import Container, Metadata, Node
from omegaconf.errors import (
    MissingMandatoryValue,
    UnsupportedValueType,
    ValidationError,
)


class ValueNode(Node):
    _val: Any

    def __init__(self, parent: Optional[Container], value: Any, metadata: Metadata):
        super().__init__(parent=parent, metadata=metadata)
        self._set_value(value)

    def _value(self) -> Any:
        return self._val

    def _set_value(self, value: Any) -> None:
        from ._utils import ValueKind, get_value_kind

        if isinstance(value, str) and get_value_kind(value) in (
            ValueKind.INTERPOLATION,
            ValueKind.STR_INTERPOLATION,
            ValueKind.MANDATORY_MISSING,
        ):
            self._val = value
        else:

            if not self._metadata.optional and value is None:
                raise ValidationError("Non optional field cannot be assigned None")
            self._val = self.validate_and_convert(value)

    def validate_and_convert(self, value: Any) -> Any:
        """
        Validates input and converts to canonical form
        :param value: input value
        :return:  converted value ("100" may be converted to 100 for example)
        """
        return value

    def __str__(self) -> str:
        return str(self._val)

    def __repr__(self) -> str:
        return repr(self._val) if hasattr(self, "_val") else "__INVALID__"

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AnyNode):
            return self._val == other._val  # type: ignore
        else:
            return self._val == other  # type: ignore

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        assert x is not NotImplemented
        return not x

    def __hash__(self) -> int:
        return hash(self._val)

    def _deepcopy_impl(self, res: Any, memo: Optional[Dict[int, Any]] = {}) -> None:
        res.__dict__ = copy.deepcopy(self.__dict__, memo=memo)

    def _is_none(self) -> bool:
        node = self._dereference_node()
        return node._value() is None

    def _is_optional(self) -> bool:
        node = self._dereference_node()
        return node._metadata.optional

    def _is_missing(self) -> bool:
        try:
            node = self._dereference_node(throw_on_missing=True)
            if isinstance(node, Container):
                ret = node._is_missing()
            else:
                ret = node._value() == "???"
        except MissingMandatoryValue:
            ret = True
        assert isinstance(ret, bool)
        return ret

    def _is_interpolation(self) -> bool:
        return _is_interpolation(self._value())


class AnyNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                ref_type=None, object_type=None, key=key, optional=is_optional
            ),
        )

    def validate_and_convert(self, value: Any) -> Any:
        from ._utils import is_primitive_type

        if not is_primitive_type(value):
            raise UnsupportedValueType(
                f"Unsupported value type, type={type(value)}, value={value}"
            )
        return value

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "AnyNode":
        res = AnyNode()
        self._deepcopy_impl(res, memo)
        return res


class StringNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                key=key, optional=is_optional, ref_type=str, object_type=str
            ),
        )

    def validate_and_convert(self, value: Any) -> Optional[str]:
        return str(value) if value is not None else None

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "StringNode":
        res = StringNode()
        self._deepcopy_impl(res, memo)
        return res


class IntegerNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                key=key, optional=is_optional, ref_type=int, object_type=int
            ),
        )

    def validate_and_convert(self, value: Any) -> Optional[int]:
        try:
            if value is None:
                val = None
            elif type(value) in (str, int):
                val = int(value)
            else:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                f"Value '{value}' could not be converted to Integer"
            ) from None
        return val

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "IntegerNode":
        res = IntegerNode()
        self._deepcopy_impl(res, memo)
        return res


class FloatNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                key=key, optional=is_optional, ref_type=float, object_type=float
            ),
        )

    def validate_and_convert(self, value: Any) -> Optional[float]:
        if value is None:
            return None
        try:
            if type(value) in (float, str, int):
                return float(value)
            else:
                raise ValueError()
        except ValueError:
            raise ValidationError(
                f"Value '{value}' could not be converted to float"
            ) from None

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, ValueNode):
            other_val = other._val
        else:
            other_val = other
        if self._val is None and other is None:
            return True
        if self._val is None and other is not None:
            return False
        if self._val is not None and other is None:
            return False
        nan1 = math.isnan(self._val) if isinstance(self._val, float) else False
        nan2 = math.isnan(other_val) if isinstance(other_val, float) else False
        return self._val == other_val or (nan1 and nan2)

    def __hash__(self) -> int:
        return hash(self._val)

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "FloatNode":
        res = FloatNode()
        self._deepcopy_impl(res, memo)
        return res


class BooleanNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                key=key, optional=is_optional, ref_type=bool, object_type=bool
            ),
        )

    def validate_and_convert(self, value: Any) -> Optional[bool]:
        if isinstance(value, bool):
            return value
        if isinstance(value, int):
            return value != 0
        elif value is None:
            return None
        elif isinstance(value, str):
            try:
                return self.validate_and_convert(int(value))
            except ValueError:
                if value.lower() in ("yes", "y", "on", "true"):
                    return True
                elif value.lower() in ("no", "n", "off", "false"):
                    return False
                else:
                    raise ValidationError(
                        "Value '{}' is not a valid bool".format(value)
                    ) from None
        else:
            raise ValidationError(
                f"Value '{value}' is not a valid bool (type {type(value).__name__})"
            )

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "BooleanNode":
        res = BooleanNode()
        self._deepcopy_impl(res, memo)
        return res


class EnumNode(ValueNode):  # lgtm [py/missing-equals] : Intentional.
    """
    NOTE: EnumNode is serialized to yaml as a string ("Color.BLUE"), not as a fully qualified yaml type.
    this means serialization to YAML of a typed config (with EnumNode) will not retain the type of the Enum
    when loaded.
    This is intentional, Please open an issue against OmegaConf if you wish to discuss this decision.
    """

    def __init__(
        self,
        enum_type: Type[Enum],
        value: Optional[Union[Enum, str]] = None,
        key: Any = None,
        parent: Optional[Container] = None,
        is_optional: bool = True,
    ):
        if not isinstance(enum_type, type) or not issubclass(enum_type, Enum):
            raise ValidationError(
                f"EnumNode can only operate on Enum subclasses ({enum_type})"
            )
        self.fields: Dict[str, str] = {}
        self.enum_type: Type[Enum] = enum_type
        for name, constant in enum_type.__members__.items():
            self.fields[name] = constant.value
        super().__init__(
            parent=parent,
            value=value,
            metadata=Metadata(
                key=key, optional=is_optional, ref_type=enum_type, object_type=enum_type
            ),
        )

    def validate_and_convert(self, value: Any) -> Optional[Enum]:
        return self.validate_and_convert_to_enum(enum_type=self.enum_type, value=value)

    @staticmethod
    def validate_and_convert_to_enum(
        enum_type: Type[Enum], value: Any
    ) -> Optional[Enum]:
        if value is None:
            return None

        if not isinstance(value, (str, int)) and not isinstance(value, enum_type):
            # if type(value) not in (str, int) and not isinstance(value, enum_type):
            raise ValidationError(
                f"Value {value} ({type(value).__name__}) is not a valid input for {enum_type}"
            )

        if isinstance(value, enum_type):
            return value

        try:
            if isinstance(value, (float, bool)):
                raise ValueError

            if isinstance(value, int):
                return enum_type(value)

            if isinstance(value, str):
                prefix = "{}.".format(enum_type.__name__)
                if value.startswith(prefix):
                    value = value[len(prefix) :]
                return enum_type[value]

            assert False  # pragma: no cover

        except (ValueError, KeyError):
            valid = "\n".join([f"\t{x}" for x in enum_type.__members__.keys()])
            raise ValidationError(
                f"Invalid value '{value}', expected one of:\n{valid}"
            ) from None

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "EnumNode":
        res = EnumNode(enum_type=self.enum_type)
        self._deepcopy_impl(res, memo)
        return res
