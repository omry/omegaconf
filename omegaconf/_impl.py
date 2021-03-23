from omegaconf import MISSING, DictConfig, ListConfig, Node
from omegaconf.errors import InterpolationToMissingValueError


def _resolve(cfg: Node) -> Node:
    assert isinstance(cfg, Node)
    try:
        if cfg._is_interpolation():
            resolved = cfg._dereference_node()
            assert resolved is not None
            cfg._set_value(resolved._value())
    except InterpolationToMissingValueError:
        cfg._set_value(MISSING)

    if isinstance(cfg, DictConfig):
        for k in cfg.keys():
            node = cfg._get_node(k)
            assert isinstance(node, Node)
            _resolve(node)

    elif isinstance(cfg, ListConfig):
        for i in range(len(cfg)):
            node = cfg._get_node(i)
            assert isinstance(node, Node)
            _resolve(node)

    return cfg
