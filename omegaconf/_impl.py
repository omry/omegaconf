from typing import Any

from omegaconf import MISSING, DictConfig, ListConfig, ValueNode
from omegaconf.errors import InterpolationToMissingValueError


def _resolve(cfg: Any) -> Any:
    if isinstance(cfg, DictConfig):
        for k in cfg.keys():
            node = cfg._get_node(k)
            cfg[k] = _resolve(node)

    if isinstance(cfg, ListConfig):
        for i in range(len(cfg)):
            node = cfg._get_node(i)
            cfg[i] = _resolve(node)

    elif isinstance(cfg, ValueNode):
        try:
            cfg = cfg._dereference_node()
        except InterpolationToMissingValueError:
            cfg = MISSING

    return cfg
