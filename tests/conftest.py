import copy
from typing import Any

import pytest

from omegaconf.basecontainer import BaseContainer


@pytest.fixture(scope="function")  # type: ignore
def restore_resolvers() -> Any:
    """
    A fixture to restore singletons state after this the function.
    This is useful for functions that are making a one-off change to singlestons that should not effect
    other tests
    """
    state = copy.deepcopy(BaseContainer._resolvers)
    yield
    BaseContainer._resolvers = state
