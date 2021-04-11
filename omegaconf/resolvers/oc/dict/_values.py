from typing import Any, List

from omegaconf import AnyNode, Container, ListConfig
from omegaconf.basecontainer import BaseContainer
from omegaconf.resolvers.oc.dict._common import _get_and_validate_dict_input


def dict_values(key: str, _root_: BaseContainer, _parent_: Container) -> ListConfig:
    assert isinstance(_parent_, BaseContainer)
    in_dict = _get_and_validate_dict_input(
        key, parent=_parent_, resolver_name="oc.dict.values"
    )

    content = in_dict._content
    assert isinstance(content, dict)

    ret = ListConfig([])
    for k in content:
        ref_node = AnyNode(f"${{{key}.{k}}}")
        ret.append(ref_node)

    # Finalize result by setting proper type and parent.
    element_type: Any = in_dict._metadata.element_type
    ret._metadata.element_type = element_type
    ret._metadata.ref_type = List[element_type]
    ret._set_parent(_parent_)

    return ret
