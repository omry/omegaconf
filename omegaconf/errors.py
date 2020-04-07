from typing import Any, Optional


class OmegaConfBaseException(Exception):
    # would ideally be typed Optional[Node]
    node: Any
    key: Any
    value: Any
    msg: Optional[str]
    cause: Optional[Exception]

    def __init__(self, *_args: Any, **_kwargs: Any) -> None:
        self.node = None
        self.key = None
        self.value = None
        self.msg = None
        self.cause = None


class MissingMandatoryValue(OmegaConfBaseException):
    """Thrown when a variable flagged with '???' value is accessed to
    indicate that the value was not set"""


class UnsupportedValueType(OmegaConfBaseException, ValueError):
    """
    Thrown when an input value is not of supported type
    """


class KeyValidationError(OmegaConfBaseException, ValueError):
    """
    Thrown when an a key of invalid type is used
    """


class ValidationError(OmegaConfBaseException, ValueError):
    """
    Thrown when a value fails validation
    """


class ReadonlyConfigError(OmegaConfBaseException):
    """
    Thrown when someone tries to modify a frozen config
    """


class UnsupportedInterpolationType(OmegaConfBaseException, ValueError):
    """
    Thrown when an attempt to use an unregistered interpolation is made
    """


# TODO KeyError subclass?
