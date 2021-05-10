import re
from enum import Enum
from importlib import import_module
from typing import Any, Dict, List, Optional

from pytest import fixture, mark, param, raises

from omegaconf import (
    DictConfig,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    SCMode,
    open_dict,
)
from omegaconf.errors import InterpolationResolutionError
from tests import Color, User, warns_dict_subclass_deprecated


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
    "structured_config_mode,src,expected,key,expected_value_type",
    [
        param(
            SCMode.DICT,
            {"user": User(age=7, name="Bond")},
            {"user": {"name": "Bond", "age": 7}},
            "user",
            dict,
            id="DICT-dict",
        ),
        param(
            SCMode.DICT,
            [1, User(age=7, name="Bond")],
            [1, {"name": "Bond", "age": 7}],
            1,
            dict,
            id="DICT-list",
        ),
        param(
            SCMode.DICT_CONFIG,
            {"user": User(age=7, name="Bond")},
            {"user": User(age=7, name="Bond")},
            "user",
            DictConfig,
            id="DICT_CONFIG-dict",
        ),
        param(
            SCMode.DICT_CONFIG,
            [1, User(age=7, name="Bond")],
            [1, User(age=7, name="Bond")],
            1,
            DictConfig,
            id="DICT_CONFIG-list",
        ),
        param(
            SCMode.INSTANTIATE,
            {"user": User(age=7, name="Bond")},
            {"user": User(age=7, name="Bond")},
            "user",
            User,
            id="INSTANTIATE-dict",
        ),
        param(
            SCMode.INSTANTIATE,
            [1, User(age=7, name="Bond")],
            [1, User(age=7, name="Bond")],
            1,
            User,
            id="INSTANTIATE-list",
        ),
        param(
            None,
            {"user": User(age=7, name="Bond")},
            {"user": {"name": "Bond", "age": 7}},
            "user",
            dict,
            id="default-dict",
        ),
        param(
            None,
            [1, User(age=7, name="Bond")],
            [1, {"name": "Bond", "age": 7}],
            1,
            dict,
            id="default-list",
        ),
    ],
)
def test_scmode(
    src: Any,
    structured_config_mode: Optional[SCMode],
    expected: Any,
    expected_value_type: Any,
    key: Any,
) -> None:
    cfg = OmegaConf.create(src)
    if structured_config_mode is None:
        ret = OmegaConf.to_container(cfg)
    else:
        ret = OmegaConf.to_container(cfg, structured_config_mode=structured_config_mode)
    assert ret == expected
    assert isinstance(ret[key], expected_value_type)


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


class TestInstantiateStructuredConfigs:
    @fixture(
        params=[
            "tests.structured_conf.data.dataclasses",
            "tests.structured_conf.data.attr_classes",
        ]
    )
    def module(self, request: Any) -> Any:
        return import_module(request.param)

    def round_trip_to_object(self, input_data: Any) -> Any:
        serialized = OmegaConf.create(input_data)
        round_tripped = OmegaConf.to_object(serialized)
        return round_tripped

    def test_basic(self, module: Any) -> None:
        user = self.round_trip_to_object(module.User("Bond", 7))
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_basic_with_missing(self, module: Any) -> None:
        with raises(MissingMandatoryValue):
            self.round_trip_to_object(module.User())

    def test_nested(self, module: Any) -> None:
        data = self.round_trip_to_object({"user": module.User("Bond", 7)})
        user = data["user"]
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_nested_with_missing(self, module: Any) -> None:
        with raises(MissingMandatoryValue):
            self.round_trip_to_object({"user": module.User()})

    def test_list(self, module: Any) -> None:
        lst = self.round_trip_to_object(module.UserList([module.User("Bond", 7)]))
        assert type(lst) is module.UserList
        assert len(lst.list) == 1
        user = lst.list[0]
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_list_with_missing(self, module: Any) -> None:
        with raises(MissingMandatoryValue):
            self.round_trip_to_object(module.UserList)

    def test_dict(self, module: Any) -> None:
        user_dict = self.round_trip_to_object(
            module.UserDict({"user007": module.User("Bond", 7)})
        )
        assert type(user_dict) is module.UserDict
        assert len(user_dict.dict) == 1
        user = user_dict.dict["user007"]
        assert type(user) is module.User
        assert user.name == "Bond"
        assert user.age == 7

    def test_dict_with_missing(self, module: Any) -> None:
        with raises(MissingMandatoryValue):
            self.round_trip_to_object(module.UserDict)

    def test_nested_object(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NestedConfig)
        # fill in missing values:
        cfg.default_value = module.NestedSubclass(mandatory_missing=123)
        cfg.user_provided_default.mandatory_missing = 456

        nested: Any = OmegaConf.to_object(cfg)
        assert type(nested) is module.NestedConfig
        assert type(nested.default_value) is module.NestedSubclass
        assert type(nested.user_provided_default) is module.Nested

        assert nested.default_value.mandatory_missing == 123
        assert nested.default_value.additional == 20
        assert nested.user_provided_default.mandatory_missing == 456

    def test_nested_object_with_missing(self, module: Any) -> None:
        with raises(MissingMandatoryValue):
            self.round_trip_to_object(module.NestedConfig)

    def test_to_object_resolve_is_True_by_default(self, module: Any) -> None:
        interp = self.round_trip_to_object(module.Interpolation)
        assert type(interp) is module.Interpolation

        assert interp.z1 == 100
        assert interp.z2 == "100_200"

    def test_to_container_INSTANTIATE_resolve_False(self, module: Any) -> None:
        """Test the lower level `to_container` API with SCMode.INSTANTIATE and resolve=False"""
        src = dict(
            obj=module.RelativeInterpolation(),
            interp_x="${obj.x}",
            interp_x_y="${obj.x}_${obj.x}",
        )
        nested = OmegaConf.create(src)
        container = OmegaConf.to_container(
            nested, resolve=False, structured_config_mode=SCMode.INSTANTIATE
        )
        assert isinstance(container, dict)
        assert container["interp_x"] == "${obj.x}"
        assert container["interp_x_y"] == "${obj.x}_${obj.x}"
        assert container["obj"].z1 == 100
        assert container["obj"].z2 == "100_200"

    def test_to_container_INSTANTIATE_enum_to_str_True(self, module: Any) -> None:
        """Test the lower level `to_container` API with SCMode.INSTANTIATE and resolve=False"""
        src = dict(
            color=Color.BLUE,
            obj=module.EnumOptional(),
        )
        nested = OmegaConf.create(src)
        container = OmegaConf.to_container(
            nested, enum_to_str=True, structured_config_mode=SCMode.INSTANTIATE
        )
        assert isinstance(container, dict)
        assert container["color"] == "BLUE"
        assert container["obj"].not_optional is Color.BLUE

    def test_to_object_InterpolationResolutionError(self, module: Any) -> None:
        with raises(InterpolationResolutionError):
            cfg = OmegaConf.structured(module.NestedWithAny)
            cfg.var.mandatory_missing = 123
            OmegaConf.to_object(cfg)

    def test_nested_object_with_Any_ref_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NestedWithAny())
        cfg.var.mandatory_missing = 123
        with open_dict(cfg):
            cfg.value_at_root = 456
        nested = self.round_trip_to_object(cfg)
        assert type(nested) is module.NestedWithAny

        assert type(nested.var) is module.Nested
        assert nested.var.with_default == 10
        assert nested.var.mandatory_missing == 123
        assert nested.var.interpolation == 456

    def test_str2user_instantiate(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2User):
            cfg = OmegaConf.structured(module.DictSubclass.Str2User())
        cfg.bond = module.User(name="James Bond", age=7)
        data = self.round_trip_to_object(cfg)

        assert type(data) is module.DictSubclass.Str2User
        assert type(data.bond) is module.User
        assert data.bond == module.User("James Bond", 7)

    def test_str2user_with_field_instantiate(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2UserWithField):
            cfg = OmegaConf.structured(module.DictSubclass.Str2UserWithField())
        cfg.mp = module.User(name="Moneypenny", age=11)
        data = self.round_trip_to_object(cfg)

        assert type(data) is module.DictSubclass.Str2UserWithField
        assert type(data.foo) is module.User
        assert data.foo == module.User("Bond", 7)
        assert type(data.mp) is module.User
        assert data.mp == module.User("Moneypenny", 11)

    def test_str2str_with_field_instantiate(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2StrWithField):
            cfg = OmegaConf.structured(module.DictSubclass.Str2StrWithField())
        cfg.hello = "world"
        data = self.round_trip_to_object(cfg)

        assert type(data) is module.DictSubclass.Str2StrWithField
        assert data.foo == "bar"
        assert data.hello == "world"

    def test_setattr_for_user_with_extra_field(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.User(name="James Bond", age=7))
        with open_dict(cfg):
            cfg.extra_field = 123

        user: Any = OmegaConf.to_object(cfg)
        assert type(user) is module.User
        assert user.extra_field == 123


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
