import sys
from importlib import import_module

import pytest

from omegaconf import (
    OmegaConf,
    AnyNode,
    ValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedKeyType,
)
from .structured_conf.common import Color


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
    illegal = []


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

    illegal = []


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
@pytest.mark.parametrize("class_type", ["dataclass_test_data", "attr_test_data"])
class TestConfigs:
    def test_nested_config_errors_on_missing(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        with pytest.raises(ValueError):
            OmegaConf.create(module.ErrorOnMissingNestedConfig)

    def test_nested_config_errors_on_none(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        with pytest.raises(ValueError):
            OmegaConf.create(module.ErrorOnNoneNestedConfig)

    def test_nested_config(self, class_type):
        def validate(cfg):
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

        module = import_module("tests.structured_conf." + class_type)

        conf1 = OmegaConf.create(module.NestedConfig)
        validate(conf1)
        conf1 = OmegaConf.create(module.NestedConfig(default_value=module.Nested()))
        validate(conf1)

    def test_no_default_errors(self, class_type):
        module = import_module("tests.structured_conf." + class_type)

        with pytest.raises(ValueError):
            OmegaConf.create(module.NoDefaultErrors)

    def test_config_with_list(self, class_type):
        module = import_module("tests.structured_conf." + class_type)

        def validate(cfg):
            assert cfg == {
                "list1": [1, 2, 3],
                "list2": [1, 2, 3],
                "list3": [1, 2, 3],
                "list4": [1, 2, 3],
            }
            with pytest.raises(ValidationError):
                cfg.list4[1] = "foo"

        conf1 = OmegaConf.create(module.ConfigWithList)
        validate(conf1)

        conf1 = OmegaConf.create(module.ConfigWithList())
        validate(conf1)

    def test_assignment_to_nested_structured_config(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.NestedConfig)
        with pytest.raises(ValidationError):
            conf.default_value = 10

        conf.default_value = module.Nested()

    def test_config_with_dict(self, class_type):
        module = import_module("tests.structured_conf." + class_type)

        def validate(cfg):
            assert cfg == {"dict1": {"foo": "bar"}, "dict2": {"foo": "bar"}}

        conf1 = OmegaConf.create(module.ConfigWithDict)
        validate(conf1)
        conf1 = OmegaConf.create(module.ConfigWithDict())
        validate(conf1)
        conf1 = OmegaConf.create(module.ConfigWithDict())
        validate(conf1)

    def test_structured_config_struct_behavior(self, class_type):
        module = import_module("tests.structured_conf." + class_type)

        def validate(cfg):
            assert not OmegaConf.is_struct(cfg)
            with pytest.raises(KeyError):
                # noinspection PyStatementEffect
                cfg.foo

            cfg.dict1.foo = 10
            assert cfg.dict1.foo == 10

            # setting struct False on a specific typed node opens it up even though it's
            # still typed
            OmegaConf.set_struct(cfg, False)
            cfg.foo = 20
            assert cfg.foo == 20

        conf = OmegaConf.create(module.ConfigWithDict)
        validate(conf)
        conf = OmegaConf.create(module.ConfigWithDict())
        validate(conf)

    @pytest.mark.parametrize(
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
        self, class_type, tested_type, init_dict, assignment_data
    ):
        module = import_module("tests.structured_conf." + class_type)
        input_class = getattr(module, tested_type)

        def validate(input_, expected):
            conf = OmegaConf.create(input_)
            # Test access
            assert conf.with_default == expected.with_default
            assert conf.null_default is None
            # Test that accessing a variable without a default value
            # results in a MissingMandatoryValue exception
            with pytest.raises(MissingMandatoryValue):
                # noinspection PyStatementEffect
                conf.mandatory_missing

            # Test interpolation preserves type and value
            assert type(conf.with_default) == type(conf.interpolation)  # noqa E721
            assert conf.with_default == conf.interpolation

            # Test that assignment of illegal values
            for illegal_value in assignment_data.illegal:
                with pytest.raises(ValidationError):
                    conf.with_default = illegal_value

                with pytest.raises(ValidationError):
                    conf.null_default = illegal_value

                with pytest.raises(ValidationError):
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

    @pytest.mark.parametrize(
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
    def test_untyped(self, class_type, input_init, expected_init):
        input_ = import_module("tests.structured_conf." + class_type).AnyTypeConfig
        expected = input_(**expected_init)
        if input_init is not None:
            input_ = input_(**input_init)

        conf = OmegaConf.create(input_)
        assert conf.null_default == expected.null_default
        assert conf.int_default == expected.int_default
        assert conf.float_default == expected.float_default
        assert conf.str_default == expected.str_default
        assert conf.bool_default == expected.bool_default
        # yes, this is weird.
        assert "mandatory_missing" in conf.keys() and "mandatory_missing" not in conf

        with pytest.raises(MissingMandatoryValue):
            # noinspection PyStatementEffect
            conf.mandatory_missing

        assert type(conf.get_node("null_default")) == AnyNode
        assert type(conf.get_node("int_default")) == AnyNode
        assert type(conf.get_node("float_default")) == AnyNode
        assert type(conf.get_node("str_default")) == AnyNode
        assert type(conf.get_node("bool_default")) == AnyNode
        assert type(conf.get_node("mandatory_missing")) == AnyNode

        assert conf.int_default == expected.int_default
        with pytest.raises(ValidationError):
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

    def test_interpolation(self, class_type):
        input_ = import_module("tests.structured_conf." + class_type).Interpolation()
        conf = OmegaConf.create(input_)
        assert conf.x == input_.x
        assert conf.z1 == conf.x
        assert conf.z2 == f"{conf.x}_{conf.y}"
        assert type(conf.x) == int
        assert type(conf.y) == int
        assert type(conf.z1) == int
        assert type(conf.z2) == str

    @pytest.mark.parametrize(
        "tested_type",
        [
            "BoolOptional",
            "IntegerOptional",
            "FloatOptional",
            "StringOptional",
            "EnumOptional",
        ],
    )
    def test_optional(self, class_type, tested_type):
        module = import_module("tests.structured_conf." + class_type)
        input_ = getattr(module, tested_type)
        obj = input_(no_default=None)
        conf = OmegaConf.create(input_)
        assert conf.no_default is None
        assert conf.as_none is None
        assert conf.with_default == obj.with_default
        # assign None to an optional field
        conf.with_default = None
        assert conf.with_default is None

        # verify non-optional fields are rejecting None
        with pytest.raises(ValidationError):
            conf.not_optional = None

    def test_typed_list(self, class_type):
        input_ = import_module("tests.structured_conf." + class_type).WithTypedList
        conf = OmegaConf.create(input_)
        with pytest.raises(ValidationError):
            conf.list[0] = "fail"

        with pytest.raises(ValidationError):
            conf.list.append("fail")

        with pytest.raises(ValidationError):
            cfg2 = OmegaConf.create({"list": ["fail"]})
            OmegaConf.merge(conf, cfg2)

    def test_typed_dict(self, class_type):
        input_ = import_module("tests.structured_conf." + class_type).WithTypedDict
        conf = OmegaConf.create(input_)
        with pytest.raises(ValidationError):
            conf.dict["foo"] = "fail"

        with pytest.raises(ValidationError):
            OmegaConf.merge(conf, OmegaConf.create({"dict": {"foo": "fail"}}))

    def test_typed_dict_key_error(self, class_type):
        input_ = import_module("tests.structured_conf." + class_type).ErrorDictIntKey
        with pytest.raises(UnsupportedKeyType):
            OmegaConf.create(input_)

    def test_typed_dict_value_error(self, class_type):
        input_ = import_module(
            "tests.structured_conf." + class_type
        ).ErrorDictUnsupportedValue
        with pytest.raises(ValidationError):
            OmegaConf.create(input_)

    def test_typed_list_value_error(self, class_type):
        input_ = import_module(
            "tests.structured_conf." + class_type
        ).ErrorListUnsupportedValue
        with pytest.raises(ValidationError):
            OmegaConf.create(input_)

    def test_list_examples(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.ListExamples)

        def test_any(name):
            conf[name].append(True)
            conf[name].extend([Color.RED, 3.1415])
            conf[name][2] = False
            assert conf[name] == [1, "foo", False, Color.RED, 3.1415]

        # any and untyped
        test_any("any1")
        test_any("any2")

        # test ints
        with pytest.raises(ValidationError):
            conf.ints[0] = "foo"
        conf.ints.append(10)
        assert conf.ints == [1, 2, 10]

        # test strings
        conf.strings.append(Color.BLUE)
        assert conf.strings == ["foo", "bar", "Color.BLUE"]
        # tests booleans
        with pytest.raises(ValidationError):
            conf.booleans[0] = "foo"
        conf.booleans.append(True)
        conf.booleans.append("off")
        conf.booleans.append(1)
        assert conf.booleans == [True, False, True, False, True]

        # test colors
        with pytest.raises(ValidationError):
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

    def test_dict_examples(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.DictExamples)
        # any1: Dict = {"a": 1, "b": "foo"}
        # any2: Dict[str, Any] = {"a": 1, "b": "foo"}
        # ints: Dict[str, int] = {"a": 10, "b": 20}
        # strings: Dict[str, str] = {"a": "foo", "b": "bar"}
        # booleans: Dict[str, bool] = {"a": True, "b": False}
        # colors: Dict[str, Color] = {"red": Color.RED, "green": "GREEN", "blue": 3}

        def test_any(name):
            conf[name].c = True
            conf[name].d = Color.RED
            conf[name].e = 3.1415
            assert conf[name] == {
                "a": 1,
                "b": "foo",
                "c": True,
                "d": Color.RED,
                "e": 3.1415,
            }

        # any and untyped
        test_any("any1")
        test_any("any2")

        # test ints
        with pytest.raises(ValidationError):
            conf.ints.a = "foo"
        conf.ints.c = 10
        assert conf.ints == {"a": 10, "b": 20, "c": 10}

        # test strings
        conf.strings.c = Color.BLUE
        assert conf.strings == {"a": "foo", "b": "bar", "c": "Color.BLUE"}

        # tests booleans
        with pytest.raises(ValidationError):
            conf.booleans.a = "foo"
        conf.booleans.c = True
        conf.booleans.d = "off"
        conf.booleans.e = 1
        assert conf.booleans == {
            "a": True,
            "b": False,
            "c": True,
            "d": False,
            "e": True,
        }

        # test colors
        with pytest.raises(ValidationError):
            conf.colors.foo = "foo"
        conf.colors.c = Color.BLUE
        conf.colors.d = "RED"
        conf.colors.e = "Color.GREEN"
        conf.colors.f = 3
        assert conf.colors == {
            "red": Color.RED,
            "green": Color.GREEN,
            "blue": Color.BLUE,
            "c": Color.BLUE,
            "d": Color.RED,
            "e": Color.GREEN,
            "f": Color.BLUE,
        }

    def test_enum_key(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.DictWithEnumKeys)

        # When an Enum is a dictionary key the name of the Enum is actually used
        # as the key
        assert conf.enum_key.RED == "red"
        assert conf.enum_key["GREEN"] == "green"
        assert conf.enum_key[Color.GREEN] == "green"

    def test_dict_of_objects(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.DictOfObjects)
        assert conf.users.joe.age == 18
        assert conf.users.joe.name == "Joe"

        conf.users.bond = module.User(name="James Bond", age=7)
        assert conf.users.bond.name == "James Bond"
        assert conf.users.bond.age == 7

        with pytest.raises(ValidationError):
            conf.users.fail = "fail"

    def test_list_of_objects(self, class_type):
        module = import_module("tests.structured_conf." + class_type)
        conf = OmegaConf.create(module.ListOfObjects)
        assert conf.users[0].age == 18
        assert conf.users[0].name == "Joe"

        conf.users.append(module.User(name="James Bond", age=7))
        assert conf.users[1].name == "James Bond"
        assert conf.users[1].age == 7

        with pytest.raises(ValidationError):
            conf.users.append("fail")


def validate_frozen_impl(conf):
    with pytest.raises(ReadonlyConfigError):
        conf.x = 20

    with pytest.raises(ReadonlyConfigError):
        conf.list[0] = 10

    with pytest.raises(ReadonlyConfigError):
        conf.user.age = 20


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_attr_frozen():
    from tests.structured_conf.attr_test_data import FrozenClass

    validate_frozen_impl(OmegaConf.create(FrozenClass))
    validate_frozen_impl(OmegaConf.create(FrozenClass()))


@pytest.mark.skipif(sys.version_info < (3, 6), reason="requires python3.6 or higher")
def test_dataclass_frozen():
    from tests.structured_conf.dataclass_test_data import FrozenClass

    validate_frozen_impl(OmegaConf.create(FrozenClass))
    validate_frozen_impl(OmegaConf.create(FrozenClass()))
