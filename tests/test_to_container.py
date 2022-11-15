import re
from enum import Enum
from importlib import import_module
from typing import Any, Callable, Dict, List, Optional

from pytest import fixture, mark, param, raises

from omegaconf import (
    DictConfig,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    SCMode,
    open_dict,
)
from omegaconf._utils import _ensure_container
from omegaconf.errors import (
    ConfigTypeError,
    InterpolationKeyError,
    InterpolationResolutionError,
    InterpolationToMissingValueError,
)
from tests import (
    B,
    Color,
    NestedInterpolationToMissing,
    StructuredInterpolationKeyError,
    User,
    Users,
    warns_dict_subclass_deprecated,
)


@mark.parametrize(
    "input_",
    [
        param([1, 2, 3], id="list"),
        param([1, 2, {"a": 3}], id="dict_in_list"),
        param([1, 2, [10, 20]], id="list_in_list"),
        param({"b": {"b": 10}}, id="dict_in_dict"),
        param({"b": [False, 1, "2", 3.0, Color.RED, b"binary"]}, id="list_in_dict"),
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
            assert isinstance(item, (int, float, str, bytes, bool, type(None), Enum))

    c = OmegaConf.create(input_)
    res = OmegaConf.to_container(c, resolve=True)
    assert isinstance(res, (dict, list))
    assert_container_with_primitives(res)


@mark.parametrize(
    "method",
    [
        OmegaConf.to_container,
        OmegaConf.to_object,
    ],
)
def test_to_container_supports_allow_objects(method: Callable[[Any], Any]) -> None:
    obj = object()
    input_ = {"obj": obj}
    cfg = OmegaConf.create(input_, flags={"allow_objects": True})

    container = method(cfg)

    assert container == input_
    assert container["obj"] is obj


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
    assert isinstance(ret, (dict, list))
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
            OmegaConf.create(
                {"foo": DictConfig(content="${bar}"), "bar": {"a": 0}}
            )._get_node("foo"),
            "${bar}",
            {"a": 0},
            id="toplevel_dict_inter",
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
        param(
            OmegaConf.create(
                {"foo": ListConfig(content="${bar}"), "bar": ["a"]}
            )._get_node("foo"),
            "${bar}",
            ["a"],
            id="toplevel_list_inter",
        ),
    ],
)
def test_to_container(src: Any, expected: Any, expected_with_resolve: Any) -> None:
    if expected is None:
        expected = src
    if expected_with_resolve is None:
        expected_with_resolve = expected
    cfg = _ensure_container(src)
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

    def test_unions_with_defaults_to_container(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UnionsOfPrimitveTypes.WithDefaults)
        obj: Any = OmegaConf.to_container(cfg)
        assert obj["uis"] == "abc"
        assert obj["ubc1"] is True
        assert obj["ubc2"] == Color.RED
        assert obj["ouis"] is None

    def test_unions_with_defaults_to_object(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UnionsOfPrimitveTypes.WithDefaults)
        obj: Any = OmegaConf.to_object(cfg)
        assert obj.uis == "abc"
        assert obj.ubc1 is True
        assert obj.ubc2 == Color.RED
        assert obj.ouis is None

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

    def test_init_false_with_default(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        assert cfg.with_default == "default"
        data = self.round_trip_to_object(cfg)
        assert data.with_default == "default"

    def test_init_false_with_default_overridden(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        cfg.with_default = "default_overridden"
        data = self.round_trip_to_object(cfg)
        assert data.with_default == "default_overridden"

    def test_init_false_without_default(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        assert OmegaConf.is_missing(cfg, "without_default")
        data = self.round_trip_to_object(cfg)
        assert not hasattr(data, "without_default")

    def test_init_false_without_default_overridden(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        cfg.with_default = "default_overridden"
        data = self.round_trip_to_object(cfg)
        assert data.with_default == "default_overridden"

    def test_init_false_post_initialized(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        assert OmegaConf.is_missing(cfg, "post_initialized")
        data = self.round_trip_to_object(cfg)
        assert data.post_initialized == "set_by_post_init"

    def test_init_false_post_initialized_overridden(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.HasInitFalseFields)
        cfg.post_initialized = "overridden"
        data = self.round_trip_to_object(cfg)
        assert data.post_initialized == "overridden"

    def test_ignore_metadata_with_required_args(self, module: Any) -> None:
        """
        Given a dataclass/attr class that has a field with no default value and with
        metadata["omegaconf_ignore"] == True, test that OmegaConf.to_object(cfg) fails.
        """
        cfg = OmegaConf.structured(module.HasIgnoreMetadataRequired(1, 2))
        assert cfg.keys() == {"no_ignore"}
        with raises(
            ConfigTypeError,
            match=r"Could not create instance of `HasIgnoreMetadataRequired`: "
            + r".*__init__\(\) missing 1 required positional argument: 'ignore'",
        ):
            OmegaConf.to_object(cfg)

    def test_ignore_metadata_with_default_args(self, module: Any) -> None:
        """
        Given a dataclass/attr class that has a field with a default value and with
        metadata["omegaconf_ignore"] == True, test that OmegaConf.to_object(cfg) succeeds.
        """
        cfg = OmegaConf.structured(module.HasIgnoreMetadataWithDefault(3, 4))
        assert cfg == {"no_ignore": 4}
        data = OmegaConf.to_object(cfg)
        assert data == module.HasIgnoreMetadataWithDefault(1, 4)


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


@mark.parametrize(
    "cfg",
    [
        # to_container: throw_on_missing
        param(DictConfig("???"), id="dict:missing"),
        param(DictConfig({"a": "???"}), id="dict:missing_value"),
        param(DictConfig({"a": {"b": "???"}}), id="dict:nested"),
        param(ListConfig("???"), id="list:missing"),
        param(ListConfig(["???"]), id="list:missing_elt"),
        param(ListConfig(["abc", ["???"]]), id="list:nested"),
        param(OmegaConf.structured(B), id="structured:missing_field"),
        param(
            OmegaConf.structured(Users({"Bond": "???"})),  # type: ignore
            id="structured:missing_in_dict_field",
        ),
    ],
)
class TestThrowOnMissing:
    """Tests the `throw_on_missing` arugment to OmegaConf.to_container"""

    @mark.parametrize(
        "op",
        [
            param(
                lambda cfg: OmegaConf.to_container(cfg, throw_on_missing=True),
                id="to_container",
            ),
            param(OmegaConf.to_object, id="to_object"),
        ],
    )
    def test_throw_on_missing_raises(self, op: Any, cfg: Any) -> None:
        with raises(MissingMandatoryValue):
            op(cfg)

    def test_no_throw_on_missing(self, cfg: Any) -> None:
        assert OmegaConf.to_container(cfg, throw_on_missing=False) == cfg


@mark.parametrize(
    "cfg,expected,exception_type",
    [
        param(
            OmegaConf.create({"foo": "${bar}"}),
            {"foo": "${bar}"},
            InterpolationKeyError,
            id="interp_key_error",
        ),
        param(
            OmegaConf.create({"subcfg": {"x": "${missing}"}, "missing": "???"}).subcfg,
            {"x": "${missing}"},
            InterpolationToMissingValueError,
            id="interp_to_missing_in_dict",
        ),
        param(
            OmegaConf.create({"subcfg": ["${missing}"], "missing": "???"}).subcfg,
            ["${missing}"],
            InterpolationToMissingValueError,
            id="interp_to_missing_in_list",
        ),
        param(
            OmegaConf.structured(NestedInterpolationToMissing).subcfg,
            {"baz": "${..name}"},
            InterpolationToMissingValueError,
            id="interp_to_missing_in_structured",
        ),
        param(
            OmegaConf.structured(StructuredInterpolationKeyError),
            {"name": "${bar}"},
            InterpolationKeyError,
            id="interp_key_error_in_structured",
        ),
        param(
            DictConfig(content="${bar}"),
            "${bar}",
            InterpolationResolutionError,
            id="dictconfig_interp_key_error",
        ),
        param(
            ListConfig(content="${bar}"),
            "${bar}",
            InterpolationResolutionError,
            id="dictconfig_interp_key_error",
        ),
        param(
            OmegaConf.create({"foo": DictConfig(content="${bar}")}),
            {"foo": "${bar}"},
            InterpolationKeyError,
            id="dictconfig_interp_key_error_in_dict",
        ),
    ],
)
class TestResolveBadInterpolation:
    @mark.parametrize(
        "op",
        [
            param(
                lambda cfg: OmegaConf.to_container(
                    cfg, resolve=True, throw_on_missing=True
                ),
                id="throw_on_missing",
            ),
            param(
                lambda cfg: OmegaConf.to_container(
                    cfg, resolve=True, throw_on_missing=False
                ),
                id="no_throw_on_missing",
            ),
            param(OmegaConf.to_object, id="to_object"),
        ],
    )
    def test_resolve_bad_interpolation_raises(
        self, op: Any, cfg: Any, expected: Any, exception_type: Any
    ) -> None:
        with raises(exception_type):
            op(cfg)

    @mark.parametrize("throw_on_missing", [True, False])
    def test_resolve_bad_interpolation_no_resolve(
        self, cfg: Any, expected: Any, exception_type: Any, throw_on_missing: bool
    ) -> None:
        ret = OmegaConf.to_container(
            cfg, resolve=False, throw_on_missing=throw_on_missing
        )
        assert ret == expected
