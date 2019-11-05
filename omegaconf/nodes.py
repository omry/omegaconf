from abc import abstractmethod

from .errors import ValidationError
import math


class BaseNode(object):
    def __init__(self):
        self.val = None

    def value(self):
        return self.val

    @abstractmethod
    def set_value(self, value):
        raise NotImplementedError()

    def __str__(self):
        return str(self.val)

    def __repr__(self):
        return repr(self.val)

    def __eq__(self, other):
        if isinstance(other, BaseNode):
            return self.val == other.val
        else:
            return self.val == other

    def __ne__(self, other):
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented


class UntypedNode(BaseNode):
    def __init__(self, value=None):
        self.val = None
        self.set_value(value)

    def set_value(self, value):
        self.val = value


class StringNode(BaseNode):
    def __init__(self, value=None):
        self.val = None
        self.set_value(value)

    def set_value(self, value):
        self.val = str(value)


class IntegerNode(BaseNode):
    def __init__(self, value=None):
        self.val = None
        self.set_value(value)

    def set_value(self, value):
        try:
            self.val = int(value) if value is not None else None
        except ValueError:
            raise ValidationError(
                "Value '{}' could not be converted to Integer".format(value)
            )


class FloatNode(BaseNode):
    def __init__(self, value=None):
        self.val = None
        self.set_value(value)

    def set_value(self, value):
        try:
            self.val = float(value) if value is not None else None
        except ValueError:
            raise ValidationError(
                "Value '{}' could not be converted to float".format(value)
            )

    def __eq__(self, other):
        if isinstance(other, BaseNode):
            other_val = other.val
        else:
            other_val = other

        return self.val == other_val or (math.isnan(self.val) and math.isnan(other_val))


class BooleanNode(BaseNode):
    def __init__(self, value=None):
        self.val = None
        self.set_value(value)

    def set_value(self, value):
        if isinstance(value, bool):
            self.val = value
        if isinstance(value, int):
            self.val = value != 0
        elif value is None:
            self.val = False
        elif isinstance(value, str):
            try:
                self.set_value(int(value))
                return
            except ValueError:
                if value.lower() in ("yes", "y", "on", "true"):
                    self.val = True
                elif value.lower() in ("no", "n", "off", "false"):
                    self.val = False
                else:
                    raise ValidationError(
                        "Value '{}' is not a valid bool".format(value)
                    )
        else:
            raise ValidationError(
                "Value '{}' has unsupported type {}".format(value, type(value).__name__)
            )
