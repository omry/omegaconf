from omegaconf import Container, ListConfig
from omegaconf.basecontainer import BaseContainer
from omegaconf.resolvers.oc.dict._common import _get_and_validate_dict_input


def dict_keys(
    key: str,
    _parent_: Container,
) -> ListConfig:
    from omegaconf import OmegaConf

    assert isinstance(_parent_, BaseContainer)

    in_dict = _get_and_validate_dict_input(
        key, parent=_parent_, resolver_name="oc.dict.keys"
    )

    ret = OmegaConf.create(list(in_dict.keys()), parent=_parent_)
    assert isinstance(ret, ListConfig)
    return ret
