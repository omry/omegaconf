import copy
from typing import Any

from pytest import fixture

from omegaconf import OmegaConf
from omegaconf.basecontainer import BaseContainer


@fixture(scope="function")
def restore_resolvers() -> Any:
    """
    A fixture to restore singletons state after this the function.
    This is useful for functions that are making a one-off change to singlestons that should not effect
    other tests
    """
    state = copy.deepcopy(BaseContainer._resolvers)
    yield
    BaseContainer._resolvers = state


@fixture(scope="function")
def common_resolvers(restore_resolvers: Any) -> Any:
    """
    A fixture to register the common `identity` resolver.
    It depends on `restore_resolvers` to make it easier and safer to use.
    """

    def cast(t: Any, v: Any) -> Any:
        return {"str": str, "int": int}[t](v)  # cast `v` to type `t`

    OmegaConf.register_new_resolver("cast", cast)
    OmegaConf.register_new_resolver("identity", lambda x: x)

    yield
