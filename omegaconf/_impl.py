from typing import Any

from omegaconf import MISSING, Container, DictConfig, ListConfig, Node, ValueNode
from omegaconf.errors import InterpolationToMissingValueError


def _resolve_container_value(cfg: Container, key: Any) -> None:
    node = cfg._get_node(key)
    assert isinstance(node, Node)
    if node._is_interpolation():
        try:
            resolved = node._dereference_node()
        except InterpolationToMissingValueError:
            node._set_value(MISSING)
        else:
            assert resolved is not None
            if isinstance(resolved, Container):
                _resolve(resolved)
            if isinstance(resolved, Container) and isinstance(node, ValueNode):
                cfg[key] = resolved
            else:
                node._set_value(resolved._value())
    else:
        _resolve(node)


def _resolve(cfg: Node) -> Node:
    assert isinstance(cfg, Node)
    if cfg._is_interpolation():
        try:
            resolved = cfg._dereference_node()
        except InterpolationToMissingValueError:
            cfg._set_value(MISSING)
        else:
            assert resolved is not None
            cfg._set_value(resolved._value())

    if isinstance(cfg, DictConfig):
        for k in cfg.keys():
            _resolve_container_value(cfg, k)

    elif isinstance(cfg, ListConfig):
        for i in range(len(cfg)):
            _resolve_container_value(cfg, i)

    return cfg
