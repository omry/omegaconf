import re
from enum import Enum
from importlib import import_module
from typing import Any, Dict, List

from pytest import fixture, mark, param, raises, warns

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf, SCMode
from omegaconf.errors import InterpolationResolutionError
from tests import Color, User


@mark.parametrize(
    "input_",
    [
        param([1, 2, 3], id="list"),
        param([1, 2, {"a": 3}], id="dict_in_list"),
        param([1, 2, [10, 20]], id="list_in_list"),
        param({"b": {"b": 10}}, id="dict_in_dict"),
        param({"b": [False, 1, "2", 3.0, Color.RED]}, id="list_in_dict"),
        param({"b": DictConfig(content=None)}, id="none_dictconfig"),
        param({"b": ListConfig(content=None)}, id="none_listconfig"),
        param({"b": DictConfig(content="???")}, id="missing_dictconfig"),
        param({"b": ListConfig(content="???")}, id="missing_listconfig"),
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


@mark.parametrize(
    "src,ex_dict,ex_dict_config,ex_instantiate,key",
    [
        param(
            {"user": User(age=7, name="Bond")},
            {"user": {"name": "Bond", "age": 7}},
            {"user": User(age=7, name="Bond")},
            {"user": User(age=7, name="Bond")},
            "user",
            id="structured-inside-dict",
        ),
        param(
            [1, User(age=7, name="Bond")],
            [1, {"name": "Bond", "age": 7}],
            [1, User(age=7, name="Bond")],
            [1, User(age=7, name="Bond")],
            1,
            id="structured-inside-list",
        ),
    ],
)
class TestSCMode:
    @fixture
    def cfg(self, src: Any) -> Any:
        return OmegaConf.create(src)

    def test_exclude_structured_configs_default(
        self, cfg: Any, ex_dict: Any, ex_dict_config: Any, ex_instantiate: Any, key: Any
    ) -> None:
        ret = OmegaConf.to_container(cfg)
        assert ret == ex_dict
        assert isinstance(ret[key], dict)

    def test_scmode_dict(
        self, cfg: Any, ex_dict: Any, ex_dict_config: Any, ex_instantiate: Any, key: Any
    ) -> None:
        ret = OmegaConf.to_container(cfg, structured_config_mode=SCMode.DICT)
        assert ret == ex_dict
        assert isinstance(ret[key], dict)

        with warns(UserWarning):
            ret = OmegaConf.to_container(cfg, exclude_structured_configs=False)
        assert ret == ex_dict

    def test_scmode_dict_config(
        self, cfg: Any, ex_dict: Any, ex_dict_config: Any, ex_instantiate: Any, key: Any
    ) -> None:
        ret = OmegaConf.to_container(cfg, structured_config_mode=SCMode.DICT_CONFIG)
        assert ret == ex_dict_config
        assert isinstance(ret[key], DictConfig)

        with warns(UserWarning):
            ret = OmegaConf.to_container(cfg, exclude_structured_configs=True)
        assert ret == ex_dict_config

    def test_scmode_instantiate(
        self, cfg: Any, ex_dict: Any, ex_dict_config: Any, ex_instantiate: Any, key: Any
    ) -> None:
        ret = OmegaConf.to_container(cfg, structured_config_mode=SCMode.INSTANTIATE)
        assert ret == ex_instantiate
        assert isinstance(ret[key], User)


@mark.parametrize(
    "src, expected, expected_with_resolve",
    [
        param([], None, None, id="empty_list"),
        param([1, 2, 3], None, None, id="list"),
        param([None], None, None, id="list_with_none"),
        param([1, "${0}", 3], None, [1, 1, 3], id="list_with_inter"),
        param({}, None, None, id="empty_dict"),
        param({"foo": "bar"}, None, None, id="dict"),
        param(
            {"foo": "${bar}", "bar": "zonk"},
            None,
            {"foo": "zonk", "bar": "zonk"},
            id="dict_with_inter",
        ),
        param({"foo": None}, None, None, id="dict_with_none"),
        param({"foo": "???"}, None, None, id="dict_missing_value"),
        param({"foo": None}, None, None, id="dict_none_value"),
        # containers
        param(
            {"foo": DictConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_dictconfig",
        ),
        param(
            {"foo": DictConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_dictconfig",
        ),
        param(
            {"foo": DictConfig(content="${bar}"), "bar": 10},
            {"foo": "${bar}", "bar": 10},
            {"foo": 10, "bar": 10},
            id="dict_inter_dictconfig",
        ),
        param(
            {"foo": ListConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_listconfig",
        ),
        param(
            {"foo": ListConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_listconfig",
        ),
        param(
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
    container = OmegaConf.to_container(cfg, structured_config_mode=SCMode.INSTANTIATE)
    assert container == expected
    container = OmegaConf.to_container(cfg, resolve=True)
    assert container == expected_with_resolve


def test_to_container_invalid_input() -> None:
    with raises(
        ValueError,
        match=re.escape("Input cfg is not an OmegaConf config object (dict)"),
    ):
        OmegaConf.to_container({})


def test_string_interpolation_with_readonly_parent() -> None:
    cfg = OmegaConf.create({"a": 10, "b": {"c": "hello_${a}"}})
    OmegaConf.set_readonly(cfg, True)
    assert OmegaConf.to_container(cfg, resolve=True) == {
        "a": 10,
        "b": {"c": "hello_10"},
    }


@mark.parametrize(
    "src,expected",
    [
        param(DictConfig(content="${bar}"), "${bar}", id="DictConfig"),
        param(
            OmegaConf.create({"foo": DictConfig(content="${bar}")}),
            {"foo": "${bar}"},
            id="nested_DictConfig",
        ),
    ],
)
def test_to_container_missing_inter_no_resolve(src: Any, expected: Any) -> None:
    res = OmegaConf.to_container(src, resolve=False)
    assert res == expected


@mark.parametrize(
    "class_type",
    [
        "tests.structured_conf.data.dataclasses",
        "tests.structured_conf.data.attr_classes",
    ],
)
class TestInstantiateStructuredConfigs:
    @fixture
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
        with raises(InterpolationResolutionError):
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


class TestEnumToStr:
    """Test the `enum_to_str` argument to the `OmegaConf.to_container function`"""

    @mark.parametrize(
        "src,enum_to_str,expected",
        [
            param({Color.RED: "enum key"}, True, "RED", id="convert"),
            param({Color.RED: "enum key"}, False, Color.RED, id="dont-convert"),
        ],
    )
    def test_enum_to_str_for_keys(
        self, src: Any, enum_to_str: bool, expected: Any
    ) -> None:
        cfg = OmegaConf.create(src)
        container: Dict[Any, Any] = OmegaConf.to_container(cfg, enum_to_str=enum_to_str)  # type: ignore
        assert container == {expected: "enum key"}

    @mark.parametrize(
        "src,enum_to_str,expected",
        [
            param({"enum val": Color.RED}, True, "RED", id="convert"),
            param({"enum val": Color.RED}, False, Color.RED, id="dont-convert"),
        ],
    )
    def test_enum_to_str_for_values(
        self, src: Any, enum_to_str: bool, expected: Any
    ) -> None:
        cfg = OmegaConf.create(src)
        container: Dict[Any, Any] = OmegaConf.to_container(cfg, enum_to_str=enum_to_str)  # type: ignore
        assert container == {"enum val": expected}

    @mark.parametrize(
        "src,enum_to_str,expected",
        [
            param([Color.RED], True, "RED", id="convert"),
            param([Color.RED], False, Color.RED, id="dont-convert"),
        ],
    )
    def test_enum_to_str_for_list(
        self, src: Any, enum_to_str: bool, expected: Any
    ) -> None:
        cfg = OmegaConf.create(src)
        container: List[Any] = OmegaConf.to_container(cfg, enum_to_str=enum_to_str)  # type: ignore
        assert container == [expected]
