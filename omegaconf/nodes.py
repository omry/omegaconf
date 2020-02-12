import copy
import math
from abc import abstractmethod
from enum import Enum
from typing import Any, Dict, Optional, Type

from .base import Node
from .basecontainer import BaseContainer
from .errors import UnsupportedValueType, ValidationError


class ValueNode(Node):
    val = Any
    is_optional: bool

    def __init__(self, parent: Optional[BaseContainer], is_optional: bool):
        super().__init__(parent=parent)
        assert isinstance(is_optional, bool)
        self.is_optional = is_optional
        self.val = None

    def value(self) -> Any:
        return self.val

    def set_value(self, value: Any) -> None:
        from ._utils import ValueKind, get_value_kind

        if isinstance(value, str) and get_value_kind(value) in (
            ValueKind.INTERPOLATION,
            ValueKind.MANDATORY_MISSING,
        ):
            self.val = value
        else:
            if not self.is_optional and value is None:
                raise ValidationError("Non optional field cannot be assigned None")
            self.val = self.validate_and_convert(value)

    @abstractmethod
    def validate_and_convert(self, value: Any) -> Any:
        """
        Validates input and converts to canonical form
        :param value: input value
        :return:  converted value ("100" may be converted to 100 for example)
        """

    def __str__(self) -> str:
        return str(self.val)

    def __repr__(self) -> str:
        return repr(self.val) if hasattr(self, "val") else "__INVALID__"

    def __eq__(self, other: Any) -> bool:
        return self.val == other  # type: ignore

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        assert x is not NotImplemented
        return not x

    def _deepcopy_impl(self, res: Any, memo: Optional[Dict[int, Any]] = {}) -> None:
        res.__dict__["val"] = copy.deepcopy(x=self.__dict__["val"], memo=memo)
        res.__dict__["flags"] = copy.deepcopy(x=self.__dict__["flags"], memo=memo)
        res.__dict__["is_optional"] = copy.deepcopy(
            x=self.__dict__["is_optional"], memo=memo
        )
        # parent is not deep copied.
        # typically this is called by a container (DictConfig, ListConfig) which will
        # reparent the whole tree
        res.__dict__["parent"] = None


class AnyNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        self.set_value(value)

    def validate_and_convert(self, value: Any) -> Any:
        from ._utils import _is_primitive_type

        if not _is_primitive_type(value):
            raise UnsupportedValueType(
                f"Unsupported value type, type={type(value)}, value={value}"
            )
        return value

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "AnyNode":
        res = AnyNode()
        self._deepcopy_impl(res, memo)
        return res

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, AnyNode):
            return self.val == other.val and self.is_optional == other.is_optional
        else:
            return self.val == other  # type: ignore


class StringNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        self.val = None
        self.set_value(value)

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
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        self.val = None
        self.set_value(value)

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
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        self.val = None
        self.set_value(value)

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
            other_val = other.val
        else:
            other_val = other
        if self.val is None and other is None:
            return True
        if self.val is None and other is not None:
            return False
        if self.val is not None and other is None:
            return False
        nan1 = math.isnan(self.val) if isinstance(self.val, float) else False
        nan2 = math.isnan(other_val) if isinstance(other_val, float) else False
        return self.val == other_val or (nan1 and nan2)

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "FloatNode":
        res = FloatNode()
        self._deepcopy_impl(res, memo)
        return res


class BooleanNode(ValueNode):
    def __init__(
        self,
        value: Any = None,
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        self.val = None
        self.set_value(value)

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


class EnumNode(ValueNode):
    """
    NOTE: EnumNode is serialized to yaml as a string ("Color.BLUE"), not as a fully qualified yaml type.
    this means serialization to YAML of a typed config (with EnumNode) will not retain the type of the Enum
    when loaded.
    This is intentional, Please open an issue against OmegaConf if you wish to discuss this decision.
    """

    def __init__(
        self,
        enum_type: Type[Enum],
        parent: Optional[BaseContainer] = None,
        is_optional: bool = True,
    ):
        super().__init__(parent=parent, is_optional=is_optional)
        if not isinstance(enum_type, type) or not issubclass(enum_type, Enum):
            raise ValidationError(
                f"EnumNode can only operate on Enum subclasses ({enum_type})"
            )
        self.fields: Dict[str, str] = {}
        self.val = None
        self.enum_type: Type[Enum] = enum_type
        for name, constant in enum_type.__members__.items():
            self.fields[name] = constant.value

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

    def __eq__(self, other: Any) -> bool:
        sr = super().__eq__(other)
        if sr is False:
            return False
        if isinstance(other, EnumNode):
            return self.enum_type == other.enum_type and self.fields == other.fields
        else:
            return self.val == other  # type: ignore
