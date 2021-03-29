from typing import Any

from omegaconf import Container, Node


def dereference_node(cfg: Container, key: Any) -> Node:
    node = cfg._get_node(key)
    assert isinstance(node, Node)
    node = node._dereference_node()
    assert isinstance(node, Node)
    return node
