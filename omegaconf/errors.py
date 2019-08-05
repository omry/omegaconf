class MissingMandatoryValue(Exception):
    """Thrown when a variable flagged with '???' value is accessed to
    indicate that the value was not set"""


class ValidationError(Exception):
    """
    Thrown when a value fails validation
    """


class ReadonlyConfigError(Exception):
    """
    Thrown when someone tries to modify a frozen config
    """
