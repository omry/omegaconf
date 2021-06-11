from typing import Any

from pytest import mark, param, raises

from omegaconf import OmegaConf
from omegaconf.errors import ValidationError
from tests import SubscriptedDict, SubscriptedList


@mark.parametrize(
    ("cls,key,assignment,error"),
    [
        param(SubscriptedList, "list", [None], True, id="list_elt"),
        param(SubscriptedDict, "dict_str", {"key": None}, True, id="dict_elt"),
        param(SubscriptedList, "list", None, True, id="list"),
        param(SubscriptedDict, "dict_str", None, True, id="dict"),
        param(SubscriptedList, "opt_list", [None], True, id="opt_list_elt"),
        param(SubscriptedDict, "opt_dict_str", {"key": None}, True, id="opt_dict_elt"),
        param(SubscriptedList, "opt_list", None, False, id="opt_list"),
        param(SubscriptedDict, "opt_dict_str", None, False, id="opt_dict"),
    ],
)
def test_assign_none(cls: Any, key: str, assignment: Any, error: bool) -> None:
    cfg = OmegaConf.structured(cls)
    if error:
        with raises(ValidationError):
            cfg.__setattr__(key, assignment)
    else:
        cfg.__setattr__(key, assignment)
        assert cfg.__getattr__(key) == assignment
