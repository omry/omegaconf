import os
from typing import Any, Optional

from omegaconf._utils import _DEFAULT_MARKER_


def env(key: str, default: Any = _DEFAULT_MARKER_) -> Optional[str]:
    """
    :param key: Environment variable key
    :param default: Optional default value to use in case the key environment variable is not set.
                    If default is not a string, it is converted with str(default).
                    None default is returned as is.
    :return: The environment variable 'key'. If the environment variable is not set and a default is
            provided, the default is used. If used, the default is converted to a string with str(default).
            If the default is None, None is returned (without a string conversion).
    """
    try:
        return os.environ[key]
    except KeyError:
        if default is not _DEFAULT_MARKER_:
            return str(default) if default is not None else None
        else:
            raise KeyError(f"Environment variable '{key}' not found")
