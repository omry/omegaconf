import sys
from importlib import import_module
from typing import Any, Dict, List, Optional

from pytest import fixture, mark, param, raises

from omegaconf import (
    MISSING,
    AnyNode,
    DictConfig,
    KeyValidationError,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    ReadonlyConfigError,
    ValidationError,
    _utils,
)
from omegaconf.errors import ConfigKeyError
from tests import Color, User


@fixture(
    params=[
        "tests.structured_conf.data.dataclasses",
        "tests.structured_conf.data.attr_classes",
    ],
    ids=["dataclasses", "attr_classes"],
)
def module(request: Any) -> Any:
    return import_module(request.param)


class EnumConfigAssignments:
    legal = [
        (Color.RED, Color.RED),
        (Color.GREEN, Color.GREEN),
        (Color.BLUE, Color.BLUE),
        ("RED", Color.RED),
        ("GREEN", Color.GREEN),
        ("BLUE", Color.BLUE),
        ("Color.RED", Color.RED),
        ("Color.GREEN", Color.GREEN),
        ("Color.BLUE", Color.BLUE),
        (1, Color.RED),
        (2, Color.GREEN),
        (3, Color.BLUE),
    ]
    illegal = ["foo", True, False, 4, 1.0]


class IntegersConfigAssignments:
    legal = [("10", 10), ("-10", -10), 100, 0, 1, 1]
    illegal = ["foo", 1.0, float("inf"), float("nan"), Color.BLUE]


class StringConfigAssignments:
    legal = ["10", "-10", "foo", "", (Color.BLUE, "Color.BLUE")]
    illegal: Any = []


class FloatConfigAssignments:
    legal = [
        ("inf", float("inf")),
        ("-inf", float("-inf")),
        (10, 10.0),
        (10.1, 10.1),
        ("10.2", 10.2),
        ("10e-3", 10e-3),
    ]
    illegal = ["foo", True, False, Color.BLUE]


class BoolConfigAssignments:
    legal = [
        (True, True),
        ("Y", True),
        ("true", True),
        ("Yes", True),
        ("On", True),
        ("1", True),
        (100, True),
        (False, False),
        ("N", False),
        ("false", False),
        ("No", False),
        ("Off", False),
        ("0", False),
        (0, False),
    ]
    illegal = [100.0, Color.BLUE]


class AnyTypeConfigAssignments:
    legal = [True, False, 10, 10.0, "foobar", Color.BLUE]

    illegal: Any = []


class TestConfigs:
    def test_nested_config_is_none(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NestedWithNone)
        assert cfg == {"plugin": None}
        assert OmegaConf.get_type(cfg, "plugin") is None
        assert _utils.get_ref_type(cfg, "plugin") == Optional[module.Plugin]

    def test_nested_config(self, module: Any) -> None:
        def validate(cfg: DictConfig) -> None:
            assert cfg == {
                "default_value": {
                    "with_default": 10,
                    "null_default": None,
                    "mandatory_missing": "???",
                    "interpolation": "${value_at_root}",
                },
                "user_provided_default": {
                    "with_default": 42,
                    "null_default": None,
                    "mandatory_missing": "???",
                    "interpolation": "${value_at_root}",
                },
                "value_at_root": 1000,
            }

            with raises(ValidationError):
                cfg.user_provided_default = 10

            with raises(ValidationError):
                cfg.default_value = 10

            # assign subclass
            cfg.default_value = module.NestedSubclass()
            assert cfg.default_value == {
                "additional": 20,
                "with_default": 10,
                "null_default": None,
                "mandatory_missing": "???",
                "interpolation": "${value_at_root}",
            }

            # assign original ref type back
            cfg.default_value = module.Nested()
            assert cfg.default_value == module.Nested()

        conf1 = OmegaConf.structured(module.NestedConfig(default_value=module.Nested()))
        validate(conf1)

    def test_nested_config2(self, module: Any) -> None:
        def validate(cfg: DictConfig) -> None:
            assert cfg == {
                "default_value": "???",
                "user_provided_default": {
                    "with_default": 42,
                    "null_default": None,
                    "mandatory_missing": "???",
                    "interpolation": "${value_at_root}",
                },
                "value_at_root": 1000,
            }

            with raises(ValidationError):
                cfg.user_provided_default = 10

            with raises(ValidationError):
                cfg.default_value = 10

            # assign subclass
            cfg.default_value = module.NestedSubclass()
            assert cfg.default_value == {
                "additional": 20,
                "with_default": 10,
                "null_default": None,
                "mandatory_missing": "???",
                "interpolation": "${value_at_root}",
            }

            # assign original ref type back
            cfg.default_value = module.Nested()
            assert cfg.default_value == module.Nested()

        conf1 = OmegaConf.structured(module.NestedConfig)
        validate(conf1)

    def test_value_without_a_default(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NoDefaultValue)
        assert OmegaConf.is_missing(cfg, "no_default")

        OmegaConf.structured(module.NoDefaultValue(no_default=10)) == {"no_default": 10}

    def test_union_errors(self, module: Any) -> None:
        with raises(ValueError):
            OmegaConf.structured(module.UnionError)

    def test_config_with_list(self, module: Any) -> None:
        def validate(cfg: DictConfig) -> None:
            assert cfg == {"list1": [1, 2, 3], "list2": [1, 2, 3], "missing": MISSING}
            with raises(ValidationError):
                cfg.list1[1] = "foo"

            assert OmegaConf.is_missing(cfg, "missing")

        conf1 = OmegaConf.structured(module.ConfigWithList)
        validate(conf1)

        conf1 = OmegaConf.structured(module.ConfigWithList())
        validate(conf1)

    def test_assignment_to_nested_structured_config(self, module: Any) -> None:
        conf = OmegaConf.structured(module.NestedConfig)
        with raises(ValidationError):
            conf.default_value = 10

        conf.default_value = module.Nested()

    def test_assignment_to_structured_inside_dict_config(self, module: Any) -> None:
        conf = OmegaConf.create(
            {"val": DictConfig(module.Nested, ref_type=module.Nested)}
        )
        with raises(ValidationError):
            conf.val = 10

    def test_config_with_dict(self, module: Any) -> None:
        def validate(cfg: DictConfig) -> None:
            assert cfg == {"dict1": {"foo": "bar"}, "missing": MISSING}
            assert OmegaConf.is_missing(cfg, "missing")

        conf1 = OmegaConf.structured(module.ConfigWithDict)
        validate(conf1)
        conf1 = OmegaConf.structured(module.ConfigWithDict())
        validate(conf1)

    def test_structured_config_struct_behavior(self, module: Any) -> None:
        def validate(cfg: DictConfig) -> None:
            assert not OmegaConf.is_struct(cfg)
            with raises(AttributeError):
                # noinspection PyStatementEffect
                cfg.foo

            cfg.dict1.foo = 10
            assert cfg.dict1.foo == 10

            # setting struct False on a specific typed node opens it up even though it's
            # still typed
            OmegaConf.set_struct(cfg, False)
            cfg.foo = 20
            assert cfg.foo == 20

        conf = OmegaConf.structured(module.ConfigWithDict)
        validate(conf)
        conf = OmegaConf.structured(module.ConfigWithDict())
        validate(conf)

    @mark.parametrize(
        "tested_type,assignment_data, init_dict",
        [
            # Use class to build config
            ("BoolConfig", BoolConfigAssignments, {}),
            ("IntegersConfig", IntegersConfigAssignments, {}),
            ("FloatConfig", FloatConfigAssignments, {}),
            ("StringConfig", StringConfigAssignments, {}),
            ("EnumConfig", EnumConfigAssignments, {}),
            # Use instance to build config
            ("BoolConfig", BoolConfigAssignments, {"with_default": False}),
            ("IntegersConfig", IntegersConfigAssignments, {"with_default": 42}),
            ("FloatConfig", FloatConfigAssignments, {"with_default": 42.0}),
            ("StringConfig", StringConfigAssignments, {"with_default": "fooooooo"}),
            ("EnumConfig", EnumConfigAssignments, {"with_default": Color.BLUE}),
            ("AnyTypeConfig", AnyTypeConfigAssignments, {}),
        ],
    )
    def test_field_with_default_value(
        self,
        module: Any,
        tested_type: str,
        init_dict: Dict[str, Any],
        assignment_data: Any,
    ) -> None:
        input_class = getattr(module, tested_type)

        def validate(input_: Any, expected: Any) -> None:
            conf = OmegaConf.structured(input_)
            # Test access
            assert conf.with_default == expected.with_default
            assert conf.null_default is None
            # Test that accessing a variable without a default value
            # results in a MissingMandatoryValue exception
            with raises(MissingMandatoryValue):
                # noinspection PyStatementEffect
                conf.mandatory_missing

            # Test interpolation preserves type and value
            assert type(conf.with_default) == type(conf.interpolation)  # noqa E721
            assert conf.with_default == conf.interpolation

            # Test that assignment of illegal values
            for illegal_value in assignment_data.illegal:
                with raises(ValidationError):
                    conf.with_default = illegal_value

                with raises(ValidationError):
                    conf.null_default = illegal_value

                with raises(ValidationError):
                    conf.mandatory_missing = illegal_value

            # Test assignment of legal values
            for legal_value in assignment_data.legal:
                expected_data = legal_value
                if isinstance(legal_value, tuple):
                    expected_data = legal_value[1]
                    legal_value = legal_value[0]
                conf.with_default = legal_value
                conf.null_default = legal_value
                conf.mandatory_missing = legal_value

                msg = "Error: {} : {}".format(input_class.__name__, legal_value)
                assert conf.with_default == expected_data, msg
                assert conf.null_default == expected_data, msg
                assert conf.mandatory_missing == expected_data, msg

        validate(input_class, input_class())
        validate(input_class(**init_dict), input_class(**init_dict))

    @mark.parametrize(
        "input_init, expected_init",
        [
            # attr class as class
            (None, {}),
            # attr class object with custom values
            ({"int_default": 30}, {"int_default": 30}),
            # dataclass as class
            (None, {}),
            # dataclass as object with custom values
            ({"int_default": 30}, {"int_default": 30}),
        ],
    )
    def test_untyped(self, module: Any, input_init: Any, expected_init: Any) -> None:
        input_ = module.AnyTypeConfig
        expected = input_(**expected_init)
        if input_init is not None:
            input_ = input_(**input_init)

        conf = OmegaConf.structured(input_)
        assert conf.null_default == expected.null_default
        assert conf.int_default == expected.int_default
        assert conf.float_default == expected.float_default
        assert conf.str_default == expected.str_default
        assert conf.bool_default == expected.bool_default
        # yes, this is weird.
        assert "mandatory_missing" in conf.keys() and "mandatory_missing" not in conf

        with raises(MissingMandatoryValue):
            # noinspection PyStatementEffect
            conf.mandatory_missing

        assert type(conf._get_node("null_default")) == AnyNode
        assert type(conf._get_node("int_default")) == AnyNode
        assert type(conf._get_node("float_default")) == AnyNode
        assert type(conf._get_node("str_default")) == AnyNode
        assert type(conf._get_node("bool_default")) == AnyNode
        assert type(conf._get_node("mandatory_missing")) == AnyNode

        assert conf.int_default == expected.int_default
        with raises(ValidationError):
            conf.typed_int_default = "foo"

        values = [10, True, False, None, 1.0, -1.0, "10", float("inf")]
        for val in values:
            conf.null_default = val
            conf.int_default = val
            conf.float_default = val
            conf.str_default = val
            conf.bool_default = val

            assert conf.null_default == val
            assert conf.int_default == val
            assert conf.float_default == val
            assert conf.str_default == val
            assert conf.bool_default == val

    def test_interpolation(self, module: Any) -> Any:
        input_ = module.Interpolation()
        conf = OmegaConf.structured(input_)
        assert conf.x == input_.x
        assert conf.z1 == conf.x
        assert conf.z2 == f"{conf.x}_{conf.y}"
        assert type(conf.x) == int
        assert type(conf.y) == int
        assert type(conf.z1) == int
        assert type(conf.z2) == str

    @mark.parametrize(
        "tested_type",
        [
            "BoolOptional",
            "IntegerOptional",
            "FloatOptional",
            "StringOptional",
            "ListOptional",
            "TupleOptional",
            "EnumOptional",
            "StructuredOptional",
            "DictOptional",
        ],
    )
    def test_optional(self, module: Any, tested_type: str) -> None:
        input_ = getattr(module, tested_type)
        obj = input_()
        conf = OmegaConf.structured(input_)

        # verify non-optional fields are rejecting None
        with raises(ValidationError):
            conf.not_optional = None

        assert conf.as_none is None
        assert conf.with_default == obj.with_default
        # assign None to an optional field
        conf.with_default = None
        assert conf.with_default is None

    def test_list_field(self, module: Any) -> None:
        input_ = module.WithListField
        conf = OmegaConf.structured(input_)
        with raises(ValidationError):
            conf.list[0] = "fail"

        with raises(ValidationError):
            conf.list.append("fail")

        with raises(ValidationError):
            cfg2 = OmegaConf.create({"list": ["fail"]})
            OmegaConf.merge(conf, cfg2)

    def test_dict_field(self, module: Any) -> None:
        input_ = module.WithDictField
        conf = OmegaConf.structured(input_)
        with raises(ValidationError):
            conf.dict["foo"] = "fail"

        with raises(ValidationError):
            OmegaConf.merge(conf, OmegaConf.create({"dict": {"foo": "fail"}}))

    @mark.skipif(sys.version_info < (3, 8), reason="requires Python 3.8 or newer")
    def test_typed_dict_field(self, module: Any) -> None:
        input_ = module.WithTypedDictField
        conf = OmegaConf.structured(input_(dict={"foo": 10}))
        assert conf.dict["foo"] == 10

        # typed dicts does not currently runtime type safety.
        conf = OmegaConf.merge(conf, {"dict": {"foo": "not_failed"}})
        assert conf.dict["foo"] == "not_failed"

    def test_merged_type1(self, module: Any) -> None:
        # Test that the merged type is that of the last merged config
        input_ = module.WithDictField
        conf = OmegaConf.structured(input_)
        res = OmegaConf.merge(OmegaConf.create(), conf)
        assert OmegaConf.get_type(res) == input_

    def test_merged_type2(self, module: Any) -> None:
        # Test that the merged type is that of the last merged config
        input_ = module.WithDictField
        conf = OmegaConf.structured(input_)
        res = OmegaConf.merge(conf, {"dict": {"foo": 99}})
        assert OmegaConf.get_type(res) == input_

    def test_merged_with_subclass(self, module: Any) -> None:
        # Test that the merged type is that of the last merged config
        c1 = OmegaConf.structured(module.Plugin)
        c2 = OmegaConf.structured(module.ConcretePlugin)
        res = OmegaConf.merge(c1, c2)
        assert OmegaConf.get_type(res) == module.ConcretePlugin

    def test_merge_missing_structured_on_self(self, module: Any) -> None:
        c1 = OmegaConf.structured(module.MissingStructuredConfigField)
        assert OmegaConf.is_missing(c1, "plugin")
        c2 = OmegaConf.merge(c1, module.MissingStructuredConfigField)
        assert OmegaConf.is_missing(c2, "plugin")

    def test_merge_missing_structured_config_is_missing(self, module: Any) -> None:
        c1 = OmegaConf.structured(module.MissingStructuredConfigField)
        assert OmegaConf.is_missing(c1, "plugin")

    def test_merge_missing_structured(self, module: Any) -> None:
        # Test that the merged type is that of the last merged config
        c1 = OmegaConf.create({"plugin": "???"})
        c2 = OmegaConf.merge(c1, module.MissingStructuredConfigField)
        assert OmegaConf.is_missing(c2, "plugin")

    def test_merge_none_is_none(self, module: Any) -> None:
        # Test that the merged type is that of the last merged config
        c1 = OmegaConf.structured(module.StructuredOptional)
        assert c1.with_default == module.Nested()
        c2 = OmegaConf.merge(c1, {"with_default": None})
        assert OmegaConf.is_none(c2, "with_default")

    def test_merge_with_subclass_into_missing(self, module: Any) -> None:
        base = OmegaConf.structured(module.PluginHolder)
        assert _utils.get_ref_type(base, "missing") == module.Plugin
        assert OmegaConf.get_type(base, "missing") is None
        res = OmegaConf.merge(base, {"missing": module.Plugin})
        assert OmegaConf.get_type(res) == module.PluginHolder
        assert _utils.get_ref_type(base, "missing") == module.Plugin
        assert OmegaConf.get_type(res, "missing") == module.Plugin

    def test_merged_with_nons_subclass(self, module: Any) -> None:
        c1 = OmegaConf.structured(module.Plugin)
        c2 = OmegaConf.structured(module.FaultyPlugin)
        with raises(ValidationError):
            OmegaConf.merge(c1, c2)

    def test_merge_into_Dict(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictExamples)
        res = OmegaConf.merge(cfg, {"strings": {"x": "abc"}})
        assert res.strings == {"a": "foo", "b": "bar", "x": "abc"}

    def test_merge_user_list_with_wrong_key(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UserList)
        with raises(ConfigKeyError):
            OmegaConf.merge(cfg, {"list": [{"foo": "var"}]})

    def test_merge_list_with_correct_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UserList)
        user = module.User(name="John", age=21)
        res = OmegaConf.merge(cfg, {"list": [user]})
        assert res.list == [user]

    def test_merge_dict_with_wrong_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UserDict)
        with raises(ValidationError):
            OmegaConf.merge(cfg, {"dict": {"foo": "var"}})

    def test_merge_dict_with_correct_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UserDict)
        user = module.User(name="John", age=21)
        res = OmegaConf.merge(cfg, {"dict": {"foo": user}})
        assert res.dict == {"foo": user}

    def test_dict_field_key_type_error(self, module: Any) -> None:
        input_ = module.ErrorDictObjectKey
        with raises(KeyValidationError):
            OmegaConf.structured(input_)

    def test_dict_field_value_type_error(self, module: Any) -> None:
        input_ = module.ErrorDictUnsupportedValue
        with raises(ValidationError):
            OmegaConf.structured(input_)

    def test_list_field_value_type_error(self, module: Any) -> None:
        input_ = module.ErrorListUnsupportedValue
        with raises(ValidationError):
            OmegaConf.structured(input_)

    @mark.parametrize("example", ["ListExamples", "TupleExamples"])
    def test_list_examples(self, module: Any, example: str) -> None:
        input_ = getattr(module, example)
        conf = OmegaConf.structured(input_)

        def test_any(name: str) -> None:
            conf[name].append(True)
            conf[name].extend([Color.RED, 3.1415])
            conf[name][2] = False
            assert conf[name] == [1, "foo", False, Color.RED, 3.1415]

        # any and untyped
        test_any("any")

        # test ints
        with raises(ValidationError):
            conf.ints[0] = "foo"
        conf.ints.append(10)
        assert conf.ints == [1, 2, 10]

        # test strings
        conf.strings.append(Color.BLUE)
        assert conf.strings == ["foo", "bar", "Color.BLUE"]

        # test booleans
        with raises(ValidationError):
            conf.booleans[0] = "foo"
        conf.booleans.append(True)
        conf.booleans.append("off")
        conf.booleans.append(1)
        assert conf.booleans == [True, False, True, False, True]

        # test colors
        with raises(ValidationError):
            conf.colors[0] = "foo"
        conf.colors.append(Color.BLUE)
        conf.colors.append("RED")
        conf.colors.append("Color.GREEN")
        conf.colors.append(3)
        assert conf.colors == [
            Color.RED,
            Color.GREEN,
            Color.BLUE,
            Color.RED,
            Color.GREEN,
            Color.BLUE,
        ]

    def test_dict_examples_any(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictExamples)

        dct = conf.any
        dct.c = True
        dct.d = Color.RED
        dct.e = 3.1415
        assert dct == {"a": 1, "b": "foo", "c": True, "d": Color.RED, "e": 3.1415}

    def test_dict_examples_int(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictExamples)
        dct = conf.ints

        # test ints
        with raises(ValidationError):
            dct.a = "foo"
        dct.c = 10
        assert dct == {"a": 10, "b": 20, "c": 10}

    def test_dict_examples_strings(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictExamples)

        # test strings
        conf.strings.c = Color.BLUE
        assert conf.strings == {"a": "foo", "b": "bar", "c": "Color.BLUE"}

    def test_dict_examples_bool(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictExamples)
        dct = conf.booleans

        # test bool
        with raises(ValidationError):
            dct.a = "foo"
        dct.c = True
        dct.d = "off"
        dct.e = 1
        assert dct == {
            "a": True,
            "b": False,
            "c": True,
            "d": False,
            "e": True,
        }

    class TestDictExamples:
        @fixture
        def conf(self, module: Any) -> DictConfig:
            conf: DictConfig = OmegaConf.structured(module.DictExamples)
            return conf

        def test_dict_examples_colors(self, conf: DictConfig) -> None:
            dct = conf.colors

            # test colors
            with raises(ValidationError):
                dct.foo = "foo"
            dct.c = Color.BLUE
            dct.d = "RED"
            dct.e = "Color.GREEN"
            dct.f = 3
            assert dct == {
                "red": Color.RED,
                "green": Color.GREEN,
                "blue": Color.BLUE,
                "c": Color.BLUE,
                "d": Color.RED,
                "e": Color.GREEN,
                "f": Color.BLUE,
            }

        def test_dict_examples_str_keys(self, conf: DictConfig) -> None:
            dct = conf.any

            with raises(KeyValidationError):
                dct[123] = "bad key type"
            dct["c"] = "three"
            assert dct == {
                "a": 1,
                "b": "foo",
                "c": "three",
            }

        def test_dict_examples_int_keys(self, conf: DictConfig) -> None:
            dct = conf.int_keys

            # test int keys
            with raises(KeyValidationError):
                dct.foo_key = "foo_value"
            dct[3] = "three"
            assert dct == {
                1: "one",
                2: "two",
                3: "three",
            }

        def test_dict_examples_float_keys(self, conf: DictConfig) -> None:
            dct = conf.float_keys

            # test float keys
            with raises(KeyValidationError):
                dct.foo_key = "foo_value"
            dct[3.3] = "three"
            assert dct == {
                1.1: "one",
                2.2: "two",
                3.3: "three",
            }

        def test_dict_examples_bool_keys(self, conf: DictConfig) -> None:
            dct = conf.bool_keys

            # test bool_keys
            with raises(KeyValidationError):
                dct.foo_key = "foo_value"
            dct[True] = "new value"
            assert dct == {
                True: "new value",
                False: "F",
            }

        def test_dict_examples_enum_key(self, conf: DictConfig) -> None:
            dct = conf.enum_key

            # When an Enum is a dictionary key the name of the Enum is actually used
            # as the key
            assert dct.RED == "red"
            assert dct["GREEN"] == "green"
            assert dct[Color.GREEN] == "green"

            dct["BLUE"] = "Blue too"
            assert dct[Color.BLUE] == "Blue too"
            with raises(KeyValidationError):
                dct["error"] = "error"

    def test_dict_of_objects(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictOfObjects)
        dct = conf.users
        assert dct.joe.age == 18
        assert dct.joe.name == "Joe"

        dct.bond = module.User(name="James Bond", age=7)
        assert dct.bond.name == "James Bond"
        assert dct.bond.age == 7

        with raises(ValidationError):
            dct.fail = "fail"

    def test_list_of_objects(self, module: Any) -> None:
        conf = OmegaConf.structured(module.ListOfObjects)
        assert conf.users[0].age == 18
        assert conf.users[0].name == "Joe"

        conf.users.append(module.User(name="James Bond", age=7))
        assert conf.users[1].name == "James Bond"
        assert conf.users[1].age == 7

        with raises(ValidationError):
            conf.users.append("fail")

    def test_promote_api(self, module: Any) -> None:
        conf = OmegaConf.create(module.AnyTypeConfig)
        conf._promote(None)
        assert conf == OmegaConf.create(module.AnyTypeConfig)
        with raises(ValueError):
            conf._promote(42)
        assert conf == OmegaConf.create(module.AnyTypeConfig)

    def test_promote_to_class(self, module: Any) -> None:

        conf = OmegaConf.create(module.AnyTypeConfig)
        assert OmegaConf.get_type(conf) == module.AnyTypeConfig

        conf._promote(module.BoolConfig)

        assert OmegaConf.get_type(conf) == module.BoolConfig
        assert conf.with_default is True
        assert conf.null_default is None
        assert OmegaConf.is_missing(conf, "mandatory_missing")

    def test_promote_to_object(self, module: Any) -> None:

        conf = OmegaConf.create(module.AnyTypeConfig)
        assert OmegaConf.get_type(conf) == module.AnyTypeConfig

        conf._promote(module.BoolConfig(with_default=False))
        assert OmegaConf.get_type(conf) == module.BoolConfig
        assert conf.with_default is False

    def test_set_key_with_with_dataclass(self, module: Any) -> None:
        cfg = OmegaConf.create({"foo": [1, 2]})
        cfg.foo = module.ListClass()

    def test_set_list_correct_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.ListClass)
        value = [1, 2, 3]
        cfg.list = value
        cfg.tuple = value
        assert cfg.list == value
        assert cfg.tuple == value

    @mark.parametrize("value", [1, True, "str", 3.1415, ["foo", True, 1.2], User()])
    def test_assign_wrong_type_to_list(self, module: Any, value: Any) -> None:
        cfg = OmegaConf.structured(module.ListClass)
        with raises(ValidationError):
            cfg.list = value
        with raises(ValidationError):
            cfg.tuple = value
        assert cfg == OmegaConf.structured(module.ListClass)

    @mark.parametrize(
        "value",
        [
            1,
            True,
            "str",
            3.1415,
            ["foo", True, 1.2],
            {"foo": True},
            User(age=1, name="foo"),
            {"user": User(age=1, name="foo")},
            ListConfig(content=[1, 2], ref_type=List[int], element_type=int),
        ],
    )
    def test_assign_wrong_type_to_dict(self, module: Any, value: Any) -> None:
        cfg = OmegaConf.structured(module.ConfigWithDict2)
        with raises(ValidationError):
            cfg.dict1 = value
        assert cfg == OmegaConf.structured(module.ConfigWithDict2)

    def test_recursive_dict(self, module: Any) -> None:
        rd = module.RecursiveDict
        o = rd(d={"a": rd(), "b": rd()})
        cfg = OmegaConf.structured(o)
        assert cfg == {
            "d": {
                "a": {"d": "???"},
                "b": {"d": "???"},
            }
        }

    def test_recursive_list(self, module: Any) -> None:
        rl = module.RecursiveList
        o = rl(d=[rl(), rl()])
        cfg = OmegaConf.structured(o)
        assert cfg == {"d": [{"d": "???"}, {"d": "???"}]}

    def test_create_untyped_dict(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UntypedDict)
        assert _utils.get_ref_type(cfg, "dict") == Dict[Any, Any]
        assert _utils.get_ref_type(cfg, "opt_dict") == Optional[Dict[Any, Any]]
        assert cfg.dict == {"foo": "var"}
        assert cfg.opt_dict is None

    def test_create_untyped_list(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UntypedList)
        assert _utils.get_ref_type(cfg, "list") == List[Any]
        assert _utils.get_ref_type(cfg, "opt_list") == Optional[List[Any]]
        assert cfg.list == [1, 2]
        assert cfg.opt_list is None


def validate_frozen_impl(conf: DictConfig) -> None:
    with raises(ReadonlyConfigError):
        conf.x = 20

    with raises(ReadonlyConfigError):
        conf.list[0] = 10

    with raises(ReadonlyConfigError):
        conf.user.age = 20

    # merge into is rejected because it mutates a readonly object
    with raises(ReadonlyConfigError):
        conf.merge_with({"user": {"name": "iceman"}})

    # Normal merge is allowed.
    ret = OmegaConf.merge(conf, {"user": {"name": "iceman"}})
    assert ret == {"user": {"name": "iceman", "age": 10}, "x": 10, "list": [1, 2, 3]}
    with raises(ReadonlyConfigError):
        ret.user.age = 20


def test_attr_frozen() -> None:
    from tests.structured_conf.data.attr_classes import FrozenClass

    validate_frozen_impl(OmegaConf.structured(FrozenClass))
    validate_frozen_impl(OmegaConf.structured(FrozenClass()))


def test_dataclass_frozen() -> None:
    from tests.structured_conf.data.dataclasses import FrozenClass

    validate_frozen_impl(OmegaConf.structured(FrozenClass))
    validate_frozen_impl(OmegaConf.structured(FrozenClass()))


class TestDictSubclass:
    def test_str2str(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2Str())
        cfg.hello = "world"
        assert cfg.hello == "world"

        with raises(KeyValidationError):
            cfg[Color.RED]

    def test_str2str_as_sub_node(self, module: Any) -> None:
        cfg = OmegaConf.create({"foo": module.DictSubclass.Str2Str})
        assert OmegaConf.get_type(cfg.foo) == module.DictSubclass.Str2Str
        assert _utils.get_ref_type(cfg.foo) == Any

        cfg.foo.hello = "world"
        assert cfg.foo.hello == "world"

        with raises(KeyValidationError):
            cfg.foo[Color.RED] = "fail"

        with raises(KeyValidationError):
            cfg.foo[123] = "fail"

    def test_int2str(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Int2Str())

        cfg[10] = "ten"  # okay
        assert cfg[10] == "ten"

        with raises(KeyValidationError):
            cfg[10.0] = "float"  # fail

        with raises(KeyValidationError):
            cfg["10"] = "string"  # fail

        with raises(KeyValidationError):
            cfg.hello = "fail"

        with raises(KeyValidationError):
            cfg[Color.RED] = "fail"

    def test_int2str_as_sub_node(self, module: Any) -> None:
        cfg = OmegaConf.create({"foo": module.DictSubclass.Int2Str})
        assert OmegaConf.get_type(cfg.foo) == module.DictSubclass.Int2Str
        assert _utils.get_ref_type(cfg.foo) == Any

        cfg.foo[10] = "ten"
        assert cfg.foo[10] == "ten"

        with raises(KeyValidationError):
            cfg.foo[10.0] = "float"  # fail

        with raises(KeyValidationError):
            cfg.foo["10"] = "string"  # fail

        with raises(KeyValidationError):
            cfg.foo.hello = "fail"

        with raises(KeyValidationError):
            cfg.foo[Color.RED] = "fail"

    def test_color2str(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Color2Str())
        cfg[Color.RED] = "red"

        with raises(KeyValidationError):
            cfg.greeen = "nope"

        with raises(KeyValidationError):
            cfg[123] = "nope"

    def test_color2color(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Color2Color())

        # add key
        cfg[Color.RED] = "GREEN"
        assert cfg[Color.RED] == Color.GREEN

        # replace key
        cfg[Color.RED] = "RED"
        assert cfg[Color.RED] == Color.RED

        cfg[Color.BLUE] = Color.BLUE
        assert cfg[Color.BLUE] == Color.BLUE

        cfg.RED = Color.RED
        assert cfg.RED == Color.RED

        with raises(ValidationError):
            # bad value
            cfg[Color.GREEN] = 10

        with raises(ValidationError):
            # bad value
            cfg[Color.GREEN] = "this string is not a color"

        with raises(KeyValidationError):
            # bad key
            cfg.greeen = "nope"

    def test_str2user(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2User())

        cfg.bond = module.User(name="James Bond", age=7)
        assert cfg.bond.name == "James Bond"
        assert cfg.bond.age == 7

        with raises(ValidationError):
            # bad value
            cfg.hello = "world"

        with raises(KeyValidationError):
            # bad key
            cfg[Color.BLUE] = "nope"

    def test_str2str_with_field(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictSubclass.Str2StrWithField())
        assert cfg.foo == "bar"
        cfg.hello = "world"
        assert cfg.hello == "world"

        with raises(KeyValidationError):
            cfg[Color.RED] = "fail"

    class TestErrors:
        def test_usr2str(self, module: Any) -> None:
            with raises(KeyValidationError):
                OmegaConf.structured(module.DictSubclass.Error.User2Str())

        def test_str2int_with_field_of_different_type(self, module: Any) -> None:
            cfg = OmegaConf.structured(module.DictSubclass.Str2IntWithStrField())
            with raises(ValidationError):
                cfg.foo = "str"

    def test_construct_from_another_retain_node_types(self, module: Any) -> None:
        cfg1 = OmegaConf.create(module.User(name="James Bond", age=7))
        with raises(ValidationError):
            cfg1.age = "not a number"

        cfg2 = OmegaConf.create(cfg1)
        with raises(ValidationError):
            cfg2.age = "not a number"

    def test_nested_with_any_var_type(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NestedWithAny)
        assert cfg == {
            "var": {
                "with_default": 10,
                "null_default": None,
                "mandatory_missing": "???",
                "interpolation": "${value_at_root}",
            }
        }

    def test_noop_merge_into_frozen(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.ContainsFrozen)
        ret = OmegaConf.merge(cfg, {"x": 20, "frozen": {}})
        assert ret == {
            "x": 20,
            "frozen": {"user": {"name": "Bart", "age": 10}, "x": 10, "list": [1, 2, 3]},
        }

    def test_merge_into_none_list(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.ListOptional)
        assert OmegaConf.merge(cfg, {"as_none": [4, 5, 6]}) == {
            "with_default": [1, 2, 3],
            "as_none": [4, 5, 6],
            "not_optional": [1, 2, 3],
        }

        assert OmegaConf.merge(cfg, cfg) == cfg

    def test_merge_into_none_dict(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictOptional)
        assert OmegaConf.merge(cfg, {"as_none": {"x": 100}}) == {
            "with_default": {"a": 10},
            "as_none": {"x": 100},
            "not_optional": {"a": 10},
        }

        assert OmegaConf.merge(cfg, cfg) == cfg

    @mark.parametrize(
        "update_value,expected",
        [
            param([], {"list": []}, id="empty"),
            param(
                [{"name": "Bond"}],
                {"list": [{"name": "Bond", "age": "???"}]},
                id="partial",
            ),
            param(
                [{"name": "Bond", "age": 7}],
                {"list": [{"name": "Bond", "age": 7}]},
                id="complete",
            ),
            param(
                [{"age": "double o seven"}],
                raises(ValidationError),
                id="complete",
            ),
        ],
    )
    def test_update_userlist(
        self, module: Any, update_value: Any, expected: Any
    ) -> None:
        cfg = OmegaConf.structured(module.UserList)
        if isinstance(expected, dict):
            OmegaConf.update(cfg, "list", update_value, merge=True)
            assert cfg == expected
        else:
            with raises(ValidationError):
                OmegaConf.update(cfg, "list", update_value, merge=True)

    def test_merge_missing_list_promotes_target_type(self, module: Any) -> None:
        c1 = OmegaConf.create({"missing": []})
        c2 = OmegaConf.structured(module.ConfigWithList)
        c3 = OmegaConf.merge(c1, c2)
        with raises(ValidationError):
            c3.missing.append("xx")
