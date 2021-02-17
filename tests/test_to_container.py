import re
from enum import Enum
from importlib import import_module
from typing import Any

import pytest

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf.errors import InterpolationResolutionError
from tests import Color, User


@pytest.mark.parametrize(
    "input_",
    [
        pytest.param([1, 2, 3], id="list"),
        pytest.param([1, 2, {"a": 3}], id="dict_in_list"),
        pytest.param([1, 2, [10, 20]], id="list_in_list"),
        pytest.param({"b": {"b": 10}}, id="dict_in_dict"),
        pytest.param({"b": [False, 1, "2", 3.0, Color.RED]}, id="list_in_dict"),
        pytest.param({"b": DictConfig(content=None)}, id="none_dictconfig"),
        pytest.param({"b": ListConfig(content=None)}, id="none_listconfig"),
        pytest.param({"b": DictConfig(content="???")}, id="missing_dictconfig"),
        pytest.param({"b": ListConfig(content="???")}, id="missing_listconfig"),
    ],
)
def test_to_container_returns_primitives(input_: Any) -> None:
    def assert_container_with_primitives(item: Any) -> None:
        if isinstance(item, list):
            for v in item:
                assert_container_with_primitives(v)
        elif isinstance(item, dict):
            for _k, v in item.items():
                assert_container_with_primitives(v)
        else:
            assert isinstance(item, (int, float, str, bool, type(None), Enum))

    c = OmegaConf.create(input_)
    res = OmegaConf.to_container(c, resolve=True)
    assert_container_with_primitives(res)


@pytest.mark.parametrize(
    "cfg,ex_false,ex_true",
    [
        pytest.param(
            {"user": User(age=7, name="Bond")},
            {"user": {"name": "Bond", "age": 7}},
            {"user": User(age=7, name="Bond")},
        ),
        pytest.param(
            [1, User(age=7, name="Bond")],
            [1, {"name": "Bond", "age": 7}],
            [1, User(age=7, name="Bond")],
        ),
        pytest.param(
            {"users": [User(age=1, name="a"), User(age=2, name="b")]},
            {"users": [{"age": 1, "name": "a"}, {"age": 2, "name": "b"}]},
            {"users": [User(age=1, name="a"), User(age=2, name="b")]},
        ),
    ],
)
def test_exclude_structured_configs(cfg: Any, ex_false: Any, ex_true: Any) -> None:
    cfg = OmegaConf.create(cfg)
    ret1 = OmegaConf.to_container(cfg, exclude_structured_configs=False)
    assert ret1 == ex_false

    ret1 = OmegaConf.to_container(cfg, instantiate=True)
    assert ret1 == ex_true

    ret1 = OmegaConf.to_container(cfg, exclude_structured_configs=True)
    assert ret1 == ex_true


@pytest.mark.parametrize(
    "src, expected, expected_with_resolve",
    [
        pytest.param([], None, None, id="empty_list"),
        pytest.param([1, 2, 3], None, None, id="list"),
        pytest.param([None], None, None, id="list_with_none"),
        pytest.param([1, "${0}", 3], None, [1, 1, 3], id="list_with_inter"),
        pytest.param({}, None, None, id="empty_dict"),
        pytest.param({"foo": "bar"}, None, None, id="dict"),
        pytest.param(
            {"foo": "${bar}", "bar": "zonk"},
            None,
            {"foo": "zonk", "bar": "zonk"},
            id="dict_with_inter",
        ),
        pytest.param({"foo": None}, None, None, id="dict_with_none"),
        pytest.param({"foo": "???"}, None, None, id="dict_missing_value"),
        pytest.param({"foo": None}, None, None, id="dict_none_value"),
        # containers
        pytest.param(
            {"foo": DictConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_dictconfig",
        ),
        pytest.param(
            {"foo": DictConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_dictconfig",
        ),
        pytest.param(
            {"foo": DictConfig(content="${bar}"), "bar": 10},
            {"foo": "${bar}", "bar": 10},
            {"foo": 10, "bar": 10},
            id="dict_inter_dictconfig",
        ),
        pytest.param(
            {"foo": ListConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_listconfig",
        ),
        pytest.param(
            {"foo": ListConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_listconfig",
        ),
        pytest.param(
            {"foo": ListConfig(content="${bar}"), "bar": 10},
            {"foo": "${bar}", "bar": 10},
            {"foo": 10, "bar": 10},
            id="dict_inter_listconfig",
        ),
    ],
)
def test_to_container(src: Any, expected: Any, expected_with_resolve: Any) -> None:
    if expected is None:
        expected = src
    if expected_with_resolve is None:
        expected_with_resolve = expected
    cfg = OmegaConf.create(src)
    container = OmegaConf.to_container(cfg)
    assert container == expected
    container = OmegaConf.to_container(cfg, instantiate=True)
    assert container == expected
    container = OmegaConf.to_container(cfg, resolve=True)
    assert container == expected_with_resolve


def test_to_container_invalid_input() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape("Input cfg is not an OmegaConf config object (dict)"),
    ):
        OmegaConf.to_container({})


def test_to_container_options_mutually_exclusive() -> None:
    with pytest.raises(ValueError):
        cfg = OmegaConf.create()
        OmegaConf.to_container(cfg, exclude_structured_configs=True, instantiate=True)


def test_string_interpolation_with_readonly_parent() -> None:
    cfg = OmegaConf.create({"a": 10, "b": {"c": "hello_${a}"}})
    OmegaConf.set_readonly(cfg, True)
    assert OmegaConf.to_container(cfg, resolve=True) == {
        "a": 10,
        "b": {"c": "hello_10"},
    }


@pytest.mark.parametrize(
    "src,expected",
    [
        pytest.param(DictConfig(content="${bar}"), "${bar}", id="DictConfig"),
        pytest.param(
            OmegaConf.create({"foo": DictConfig(content="${bar}")}),
            {"foo": "${bar}"},
            id="nested_DictConfig",
        ),
    ],
)
def test_to_container_missing_inter_no_resolve(src: Any, expected: Any) -> None:
    res = OmegaConf.to_container(src, resolve=False)
    assert res == expected


@pytest.mark.parametrize(
    "class_type",
    [
        "tests.structured_conf.data.dataclasses",
        "tests.structured_conf.data.attr_classes",
    ],
)
class TestInstantiateStructuredConfigs:
    @pytest.fixture
    def module(self, class_type: str) -> Any:
        module: Any = import_module(class_type)
        return module

    def round_trip_to_object(self, input_data: Any, **kwargs: Any) -> Any:
        serialized = OmegaConf.create(input_data)
        round_tripped = OmegaConf.to_object(serialized, **kwargs)
        return round_tripped

    def test_basic(self, module: Any) -> None:
        user = self.round_trip_to_object(module.User("Bond", 7))
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_basic_with_missing(self, module: Any) -> None:
        user = self.round_trip_to_object(module.User())
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == MISSING
        assert user.age == MISSING

    def test_nested(self, module: Any) -> None:
        data = self.round_trip_to_object({"user": module.User("Bond", 7)})
        user = data["user"]
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_nested_with_missing(self, module: Any) -> None:
        data = self.round_trip_to_object({"user": module.User()})
        user = data["user"]
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == MISSING
        assert user.age == MISSING

    def test_list(self, module: Any) -> None:
        lst = self.round_trip_to_object(module.UserList([module.User("Bond", 7)]))
        assert isinstance(lst, module.UserList)
        assert type(lst) is module.UserList
        assert len(lst.list) == 1
        user = lst.list[0]
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_list_with_missing(self, module: Any) -> None:
        lst = self.round_trip_to_object(module.UserList)
        assert isinstance(lst, module.UserList)
        assert type(lst) is module.UserList
        assert lst.list == MISSING

    def test_dict(self, module: Any) -> None:
        user_dict = self.round_trip_to_object(
            module.UserDict({"user007": module.User("Bond", 7)})
        )
        assert isinstance(user_dict, module.UserDict)
        assert type(user_dict) is module.UserDict
        assert len(user_dict.dict) == 1
        user = user_dict.dict["user007"]
        assert isinstance(user, module.User)
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_dict_with_missing(self, module: Any) -> None:
        user_dict = self.round_trip_to_object(module.UserDict)
        assert isinstance(user_dict, module.UserDict)
        assert type(user_dict) is module.UserDict
        assert user_dict.dict == MISSING

    def test_nested_object(self, module: Any) -> None:
        nested = self.round_trip_to_object(module.NestedConfig)
        assert isinstance(nested, module.NestedConfig)
        assert type(nested) is module.NestedConfig

        assert nested.default_value == MISSING

        assert isinstance(nested.user_provided_default, module.Nested)
        assert type(nested.user_provided_default) is module.Nested
        assert nested.user_provided_default.with_default == 42

    def test_to_object_resolve_is_True_by_default(self, module: Any) -> None:
        interp = self.round_trip_to_object(module.Interpolation)
        assert isinstance(interp, module.Interpolation)
        assert type(interp) is module.Interpolation

        assert interp.z1 == 100
        assert interp.z2 == "100_200"

    def test_to_object_resolve_False(self, module: Any) -> None:
        interp = self.round_trip_to_object(module.Interpolation, resolve=False)
        assert isinstance(interp, module.Interpolation)
        assert type(interp) is module.Interpolation

        assert interp.z1 == "${x}"
        assert interp.z2 == "${x}_${y}"

    def test_to_object_InterpolationResolutionError(self, module: Any) -> None:
        with pytest.raises(InterpolationResolutionError):
            self.round_trip_to_object(module.NestedWithAny)

    def test_nested_object_with_Any_ref_type(self, module: Any) -> None:
        nested = self.round_trip_to_object(module.NestedWithAny, resolve=False)
        assert isinstance(nested, module.NestedWithAny)
        assert type(nested) is module.NestedWithAny

        assert isinstance(nested.var, module.Nested)
        assert type(nested.var) is module.Nested
        assert nested.var.with_default == 10

    def test_str2user_instantiate(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2User())
        cfg.bond = module.User(name="James Bond", age=7)
        data = self.round_trip_to_object(cfg)

        assert isinstance(data, module.DictSubclass.Str2User)
        assert type(data) is module.DictSubclass.Str2User
        assert type(data["bond"]) is module.User
        assert data["bond"] == module.User("James Bond", 7)

    def test_str2user_with_field_instantiate(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2UserWithField())
        cfg.mp = module.User(name="Moneypenny", age=11)
        data = self.round_trip_to_object(cfg)

        assert isinstance(data, module.DictSubclass.Str2UserWithField)
        assert type(data) is module.DictSubclass.Str2UserWithField
        assert type(data.foo) is module.User
        assert data.foo == module.User("Bond", 7)
        assert type(data["mp"]) is module.User
        assert data["mp"] == module.User("Moneypenny", 11)

    def test_str2str_with_field_instantiate(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2StrWithField())
        cfg.hello = "world"
        data = self.round_trip_to_object(cfg)

        assert isinstance(data, module.DictSubclass.Str2StrWithField)
        assert type(data) is module.DictSubclass.Str2StrWithField
        assert data.foo == "bar"
        assert data["hello"] == "world"
