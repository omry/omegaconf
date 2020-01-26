class MissingMandatoryValue(Exception):
    """Thrown when a variable flagged with '???' value is accessed to
    indicate that the value was not set"""


class UnsupportedValueType(ValueError):
    """
    Thrown when an input value is not of supported type
    """


class KeyValidationError(ValueError):
    """
    Thrown when an a key of invalid type is used
    """


class ValidationError(ValueError):
    """
    Thrown when a value fails validation
    """


class ReadonlyConfigError(Exception):
    """
    Thrown when someone tries to modify a frozen config
    """


class UnsupportedInterpolationType(ValueError):
    """
    Thrown when an attempt to use an unregistered interpolation is made
    """
