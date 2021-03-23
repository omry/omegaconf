from typing import Any

from omegaconf import MISSING, DictConfig, ListConfig, ValueNode
from omegaconf.errors import InterpolationToMissingValueError


def _resolve(cfg: Any) -> Any:
    if isinstance(cfg, DictConfig):
        for k in cfg.keys():
            _resolve(cfg._get_node(k))

    if isinstance(cfg, ListConfig):
        for i in range(len(cfg)):
            _resolve(cfg._get_node(i))

    elif isinstance(cfg, ValueNode):
        try:
            resolved = cfg._dereference_node()
            assert resolved is not None
            cfg._set_value(resolved._value())
        except InterpolationToMissingValueError:
            cfg._set_value(MISSING)

    return cfg
