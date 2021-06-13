from typing import Any, Optional

from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf._utils import _ensure_container
from omegaconf.errors import ValidationError
from tests import (
    ConcretePlugin,
    Group,
    OptionalUsers,
    SubscriptedDict,
    SubscriptedList,
    User,
    Users,
)


@mark.parametrize(
    "cls,key,assignment,error",
    [
        param(SubscriptedList, "list", [None], True, id="list_elt"),
        param(SubscriptedList, "list", [0, 1, None], True, id="list_elt_partial"),
        param(SubscriptedDict, "dict_str", {"key": None}, True, id="dict_elt"),
        param(
            SubscriptedDict,
            "dict_str",
            {"key_valid": 123, "key_invalid": None},
            True,
            id="dict_elt_partial",
        ),
        param(SubscriptedList, "list", None, True, id="list"),
        param(SubscriptedDict, "dict_str", None, True, id="dict"),
        param(SubscriptedList, "opt_list", [None], True, id="opt_list_elt"),
        param(SubscriptedDict, "opt_dict_str", {"key": None}, True, id="opt_dict_elt"),
        param(SubscriptedList, "opt_list", None, False, id="opt_list"),
        param(SubscriptedDict, "opt_dict_str", None, False, id="opt_dict"),
        param(SubscriptedList, "list_opt", [None], False, id="list_opt_elt"),
        param(SubscriptedDict, "dict_opt", {"key": None}, False, id="dict_opt_elt"),
        param(SubscriptedList, "list_opt", None, True, id="list_opt"),
        param(SubscriptedDict, "dict_opt", None, True, id="dict_opt"),
        param(
            ListConfig([None], element_type=Optional[User]),
            0,
            User("Bond", 7),
            False,
            id="Optional[User]<-User_succeeds",
        ),
        param(
            ListConfig([User], element_type=User),
            0,
            None,
            True,
            id="Optional[User]<-str_fails",
        ),
    ],
)
def test_assign(cls: Any, key: str, assignment: Any, error: bool) -> None:
    cfg = OmegaConf.structured(cls)
    if error:
        with raises(ValidationError):
            cfg[key] = assignment
    else:
        cfg[key] = assignment
        assert cfg[key] == assignment


@mark.parametrize(
    "src,op,keys,ref_type,is_optional",
    [
        param(Group, None, ["admin"], User, True, id="opt_user"),
        param(
            ConcretePlugin,
            None,
            ["params"],
            ConcretePlugin.FoobarParams,
            False,
            id="nested_structured_conf",
        ),
        param(
            OmegaConf.structured(Users({"user007": User("Bond", 7)})).name2user,
            None,
            ["user007"],
            User,
            False,
            id="structured_dict_of_user",
        ),
        param(
            DictConfig({"a": 123}, element_type=int),
            None,
            ["a"],
            int,
            False,
            id="dict_int",
        ),
        param(
            DictConfig({"a": 123}, element_type=Optional[int]),
            None,
            ["a"],
            int,
            True,
            id="dict_opt_int",
        ),
        param(DictConfig({"a": 123}), None, ["a"], Any, True, id="dict_any"),
        param(
            ListConfig([], element_type=int),
            lambda cfg: cfg.insert(0, 123),
            [0],
            int,
            False,
            id="list_int_insert",
        ),
        param(
            OmegaConf.merge(Users, {"name2user": {"joe": User("joe")}}),
            None,
            ["name2user", "joe"],
            User,
            False,
            id="dict:merge_into_new_user_node",
        ),
        param(
            OmegaConf.merge(OptionalUsers, {"name2user": {"joe": User("joe")}}),
            None,
            ["name2user", "joe"],
            User,
            True,
            id="dict:merge_into_new_optional_user_node",
        ),
        param(
            OmegaConf.merge(ListConfig([], element_type=User), [User(name="joe")]),
            None,
            [0],
            User,
            False,
            id="list:merge_into_new_user_node",
        ),
        param(
            OmegaConf.merge(
                ListConfig([], element_type=Optional[User]), [User(name="joe")]
            ),
            None,
            [0],
            User,
            True,
            id="list:merge_into_new_optional_user_node",
        ),
    ],
)
def test_ref_type(
    src: Any, op: Any, keys: Any, ref_type: Any, is_optional: bool
) -> None:
    cfg = _ensure_container(src)
    if callable(op):
        op(cfg)
    for k in keys:
        cfg = cfg._get_node(k)
    assert cfg._is_optional() == is_optional
    assert cfg._metadata.ref_type == ref_type


ListConfig([], element_type=int)
