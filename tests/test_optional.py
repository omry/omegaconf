from typing import Any

from pytest import mark, param, raises

from omegaconf import OmegaConf
from omegaconf.errors import ValidationError
from tests import SubscriptedDict, SubscriptedList


@mark.parametrize(
    ("cls,key,assignment"),
    [
        param(SubscriptedList, "list", [None], id="list_elt"),
        param(SubscriptedDict, "dict_str", {"key": None}, id="dict_elt"),
    ],
)
def test_assign_none(cls: Any, key: str, assignment: Any) -> None:
    cfg = OmegaConf.structured(cls)
    with raises(ValidationError):
        cfg.__setattr__(key, assignment)
