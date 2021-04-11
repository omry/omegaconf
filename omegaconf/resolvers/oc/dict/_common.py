from typing import Any

from omegaconf import DictConfig
from omegaconf._utils import Marker
from omegaconf.basecontainer import BaseContainer
from omegaconf.errors import ConfigKeyError

_DEFAULT_SELECT_MARKER_: Any = Marker("_DEFAULT_SELECT_MARKER_")


def _get_and_validate_dict_input(
    key: str,
    parent: BaseContainer,
    resolver_name: str,
) -> DictConfig:
    from omegaconf import OmegaConf

    if not isinstance(key, str):
        raise TypeError(
            f"`{resolver_name}` requires a string as input, but obtained `{key}` "
            f"of type: {type(key).__name__}"
        )

    in_dict = OmegaConf.select(
        parent,
        key,
        throw_on_missing=True,
        absolute_key=True,
        default=_DEFAULT_SELECT_MARKER_,
    )

    if in_dict is _DEFAULT_SELECT_MARKER_:
        raise ConfigKeyError(f"Key not found: '{key}'")

    if not isinstance(in_dict, DictConfig):
        raise TypeError(
            f"`{resolver_name}` cannot be applied to objects of type: "
            f"{type(in_dict).__name__}"
        )

    return in_dict
