import os
import warnings
from typing import Any, Optional

from omegaconf._utils import decode_primitive
from omegaconf.errors import ValidationError
from omegaconf.resolvers import oc


# DEPRECATED: remove in 2.2
def env(key: str, default: Optional[str] = None) -> Any:
    warnings.warn(
        "The `env` resolver is deprecated, see https://github.com/omry/omegaconf/issues/573"
    )

    try:
        return decode_primitive(os.environ[key])
    except KeyError:
        if default is not None:
            return decode_primitive(default)
        else:
            raise ValidationError(f"Environment variable '{key}' not found")


__all__ = [
    "env",
    "oc",
]
