import dataclasses
import inspect
import pathlib
import re
import sys
from importlib import import_module
from pathlib import Path
from types import LambdaType
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from _pytest.python_api import RaisesContext
from pytest import fixture, mark, param, raises

from omegaconf import (
    MISSING,
    AnyNode,
    Container,
    DictConfig,
    KeyValidationError,
    ListConfig,
    MissingMandatoryValue,
    OmegaConf,
    ReadonlyConfigError,
    ValidationError,
    _utils,
)
from omegaconf.errors import ConfigKeyError, InterpolationToMissingValueError
from tests import Color, Enum1, User, warns_dict_subclass_deprecated


@fixture(
    params=[
        param("tests.structured_conf.data.dataclasses", id="dataclasses"),
        param(
            "tests.structured_conf.data.dataclasses_pre_311",
            id="dataclasses_pre_311",
            marks=mark.skipif(
                sys.version_info >= (3, 11),
                reason="python >= 3.11 does not support mutable default dataclass arguments",
            ),
        ),
        param("tests.structured_conf.data.attr_classes", id="attr_classes"),
    ],
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
    illegal = ["foo", True, b"RED", False, 4, 1.0, Path("hello.txt")]


class IntegersConfigAssignments:
    legal = [("10", 10), ("-10", -10), 100, 0, 1]
    illegal = [
        "foo",
        1.0,
        float("inf"),
        b"123",
        float("nan"),
        Color.BLUE,
        True,
        Path("hello.txt"),
    ]


class StringConfigAssignments:
    legal = [
        "10",
        "-10",
        "foo",
        "",
        (Color.BLUE, "Color.BLUE"),
        (Path("hello.txt"), "hello.txt"),
    ]
    illegal = [b"binary"]


class BytesConfigAssignments:
    legal = [b"binary"]
    illegal = ["foo", 10, Color.BLUE, 10.1, True, Path("hello.txt")]


class PathConfigAssignments:
    legal = [Path("hello.txt"), ("hello.txt", Path("hello.txt"))]
    illegal = [10, Color.BLUE, 10.1, True, b"binary"]


class FloatConfigAssignments:
    legal = [
        ("inf", float("inf")),
        ("-inf", float("-inf")),
        (10, 10.0),
        (10.1, 10.1),
        ("10.2", 10.2),
        ("10e-3", 10e-3),
    ]
    illegal = ["foo", True, False, b"10.1", Color.BLUE, Path("hello.txt")]


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
    illegal = [100.0, b"binary", Color.BLUE, Path("hello.txt")]


class AnyTypeConfigAssignments:
    legal = [True, False, 10, 10.0, b"binary", "foobar", Color.BLUE, Path("hello.txt")]

    illegal: Any = []


class TestConfigs:
    def test_nested_config_is_none(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.NestedWithNone)
        assert cfg == {"plugin": None}
        assert OmegaConf.get_type(cfg, "plugin") is None
        assert _utils.get_type_hint(cfg, "plugin") == Optional[module.Plugin]

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

        conf2 = OmegaConf.structured(module.ConfigWithList())
        validate(conf2)

    def test_config_with_list_nondefault_values(self, module: Any) -> None:
        conf1 = OmegaConf.structured(module.ConfigWithList(list1=[4, 5, 6]))
        assert conf1.list1 == [4, 5, 6]

        conf2 = OmegaConf.structured(module.ConfigWithList(list1=MISSING))
        assert OmegaConf.is_missing(conf2, "list1")

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

        conf2 = OmegaConf.structured(module.ConfigWithDict())
        validate(conf2)

    def test_config_with_dict_nondefault_values(self, module: Any) -> None:
        conf1 = OmegaConf.structured(module.ConfigWithDict(dict1={"baz": "qux"}))
        assert conf1.dict1 == {"baz": "qux"}

        conf2 = OmegaConf.structured(module.ConfigWithDict(dict1=MISSING))
        assert OmegaConf.is_missing(conf2, "dict1")

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
            ("BytesConfig", BytesConfigAssignments, {}),
            ("PathConfig", PathConfigAssignments, {}),
            ("StringConfig", StringConfigAssignments, {}),
            ("EnumConfig", EnumConfigAssignments, {}),
            # Use instance to build config
            ("BoolConfig", BoolConfigAssignments, {"with_default": False}),
            ("IntegersConfig", IntegersConfigAssignments, {"with_default": 42}),
            ("FloatConfig", FloatConfigAssignments, {"with_default": 42.0}),
            ("BytesConfig", BytesConfigAssignments, {"with_default": b"bin"}),
            ("PathConfig", PathConfigAssignments, {"with_default": Path("file.txt")}),
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
        assert c2.with_default is None

    def test_merge_with_subclass_into_missing(self, module: Any) -> None:
        base = OmegaConf.structured(module.PluginHolder)
        assert _utils.get_type_hint(base, "missing") == module.Plugin
        assert OmegaConf.get_type(base, "missing") is None
        res = OmegaConf.merge(base, {"missing": module.Plugin})
        assert OmegaConf.get_type(res) == module.PluginHolder
        assert _utils.get_type_hint(base, "missing") == module.Plugin
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

    def test_dict_of_objects_missing(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictOfObjectsMissing)
        dct = conf.users

        assert OmegaConf.is_missing(dct, "moe")

        dct.miss = MISSING
        assert OmegaConf.is_missing(dct, "miss")

    def test_assign_dict_of_objects(self, module: Any) -> None:
        conf = OmegaConf.structured(module.DictOfObjects)
        conf.users = {"poe": module.User(name="Poe", age=8), "miss": MISSING}
        assert conf.users == {"poe": {"name": "Poe", "age": 8}, "miss": "???"}

    def test_list_of_objects(self, module: Any) -> None:
        conf = OmegaConf.structured(module.ListOfObjects)
        assert conf.users[0].age == 18
        assert conf.users[0].name == "Joe"

        conf.users.append(module.User(name="James Bond", age=7))
        assert conf.users[1].name == "James Bond"
        assert conf.users[1].age == 7

        with raises(ValidationError):
            conf.users.append("fail")

    def test_list_of_objects_missing(self, module: Any) -> None:
        conf = OmegaConf.structured(module.ListOfObjectsMissing)

        assert OmegaConf.is_missing(conf.users, 0)

        conf.users.append(MISSING)
        assert OmegaConf.is_missing(conf.users, 1)

    def test_assign_list_of_objects(self, module: Any) -> None:
        conf = OmegaConf.structured(module.ListOfObjects)
        conf.users = [module.User(name="Poe", age=8), MISSING]
        assert conf.users == [{"name": "Poe", "age": 8}, "???"]

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

    def test_promote_to_dataclass(self, module: Any) -> None:
        @dataclasses.dataclass
        class Foo:
            foo: pathlib.Path
            bar: str
            qub: int = 5

        x = DictConfig({"foo": "hello.txt", "bar": "hello.txt"})
        assert isinstance(x.foo, str)
        assert isinstance(x.bar, str)

        x._promote(Foo)
        assert isinstance(x.foo, pathlib.Path)
        assert isinstance(x.bar, str)
        assert x.qub == 5

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

    @mark.parametrize(
        "value",
        [
            1,
            True,
            "str",
            3.1415,
            ["foo", True, 1.2],
            User(),
            param([None]),
        ],
    )
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
            param(None),
            True,
            "str",
            3.1415,
            User(),
        ],
    )
    def test_insert_wrong_type_to_list(self, module: Any, value: Any) -> None:
        cfg = OmegaConf.structured(module.ListClass)
        with raises(ValidationError):
            cfg.list.insert(0, value)

    @mark.parametrize(
        "value",
        [
            1,
            True,
            "str",
            3.1415,
            ["foo", True, 1.2],
            {"foo": True},
            param({"foo": None}),
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
        assert _utils.get_type_hint(cfg, "dict") == Dict[Any, Any]
        assert _utils.get_type_hint(cfg, "opt_dict") == Optional[Dict[Any, Any]]
        assert cfg.dict == {"foo": "var"}
        assert cfg.opt_dict is None

    def test_create_untyped_list(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.UntypedList)
        assert _utils.get_type_hint(cfg, "list") == List[Any]
        assert _utils.get_type_hint(cfg, "opt_list") == Optional[List[Any]]
        assert cfg.list == [1, 2]
        assert cfg.opt_list is None

    def test_has_bad_annotation1(self, module: Any) -> None:
        with raises(ValidationError, match="Unexpected type annotation: object"):
            OmegaConf.structured(module.HasBadAnnotation1)

    def test_has_bad_annotation2(self, module: Any) -> None:
        with raises(
            ValidationError,
            match="Unexpected type annotation: <object object at 0x[a-fA-F0-9]*>",
        ):
            OmegaConf.structured(module.HasBadAnnotation2)

    @mark.parametrize(
        "input_, expected, expected_type, expected_ref_type, expected_object_type",
        [
            param(
                lambda module: module.HasBadAnnotation1,
                {"data": "???"},
                AnyNode,
                Any,
                None,
            ),
            param(
                lambda module: module.HasBadAnnotation1(123),
                {"data": 123},
                AnyNode,
                Any,
                None,
            ),
            param(
                lambda module: module.HasBadAnnotation1([1, 2, 3]),
                {"data": [1, 2, 3]},
                ListConfig,
                object,
                list,
            ),
            param(
                lambda module: module.HasBadAnnotation1({1: 2}),
                {"data": {1: 2}},
                DictConfig,
                object,
                dict,
            ),
            param(
                lambda module: module.HasBadAnnotation1(module.UserWithDefaultName),
                {"data": {"name": "bob", "age": "???"}},
                DictConfig,
                object,
                lambda module: module.UserWithDefaultName,
            ),
        ],
    )
    def test_bad_annotation_allow_objects(
        self,
        module: Any,
        input_: Any,
        expected: Any,
        expected_type: Any,
        expected_ref_type: Any,
        expected_object_type: Any,
    ) -> None:
        """
        Test how unsupported annotation types are handled when `allow_objects` is True
        """
        input_ = input_(module)
        if isinstance(expected_object_type, LambdaType):
            expected_object_type = expected_object_type(module)

        cfg = OmegaConf.structured(input_, flags={"allow_objects": True})

        assert cfg == expected
        assert isinstance(cfg._get_node("data"), expected_type)
        assert cfg._get_node("data")._metadata.ref_type is expected_ref_type
        assert cfg._get_node("data")._metadata.object_type is expected_object_type


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


def test_frozen(module: Any) -> None:
    FrozenClass = module.FrozenClass

    validate_frozen_impl(OmegaConf.structured(FrozenClass))
    validate_frozen_impl(OmegaConf.structured(FrozenClass()))


def test_forward_ref(module: Any) -> None:
    C = module.HasForwardRef
    obj = C(a=C.CA(), b=C.CB(C.CA(x=33)))
    OmegaConf.create(obj)


class TestDictSubclass:
    def test_str2str(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2Str):
            cfg = OmegaConf.structured(module.DictSubclass.Str2Str())
        cfg.hello = "world"
        assert cfg.hello == "world"

        with raises(KeyValidationError):
            cfg[Color.RED]

    def test_dict_subclass_data_preserved_upon_node_creation(self, module: Any) -> None:
        src = module.DictSubclass.Str2StrWithField()
        src["baz"] = "qux"
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2StrWithField):
            cfg = OmegaConf.structured(src)
        assert cfg.foo == "bar"
        assert cfg.baz == "qux"

    def test_create_dict_subclass_with_bad_value_type(self, module: Any) -> None:
        src = module.DictSubclass.Str2Int()
        src["baz"] = "qux"
        with raises(ValidationError):
            with warns_dict_subclass_deprecated(module.DictSubclass.Str2Int):
                OmegaConf.structured(src)

    def test_str2str_as_sub_node(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2Str):
            cfg = OmegaConf.create({"foo": module.DictSubclass.Str2Str})
        assert OmegaConf.get_type(cfg.foo) == module.DictSubclass.Str2Str
        assert _utils.get_type_hint(cfg.foo) == Any

        cfg.foo.hello = "world"
        assert cfg.foo.hello == "world"

        with raises(KeyValidationError):
            cfg.foo[Color.RED] = "fail"

        with raises(KeyValidationError):
            cfg.foo[123] = "fail"

    def test_int2str(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Int2Str):
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
        with warns_dict_subclass_deprecated(module.DictSubclass.Int2Str):
            cfg = OmegaConf.create({"foo": module.DictSubclass.Int2Str})
        assert OmegaConf.get_type(cfg.foo) == module.DictSubclass.Int2Str
        assert _utils.get_type_hint(cfg.foo) == Any

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
        with warns_dict_subclass_deprecated(module.DictSubclass.Color2Str):
            cfg = OmegaConf.structured(module.DictSubclass.Color2Str())
        cfg[Color.RED] = "red"

        with raises(KeyValidationError):
            cfg.greeen = "nope"

        with raises(KeyValidationError):
            cfg[123] = "nope"

    def test_color2color(self, module: Any) -> None:
        with warns_dict_subclass_deprecated(module.DictSubclass.Color2Color):
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
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2User):
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
        with warns_dict_subclass_deprecated(module.DictSubclass.Str2StrWithField):
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
            with warns_dict_subclass_deprecated(
                module.DictSubclass.Str2IntWithStrField
            ):
                cfg = OmegaConf.structured(module.DictSubclass.Str2IntWithStrField())
            with raises(ValidationError):
                cfg.foo = "str"


class TestConfigs2:
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

    def test_set_value_after_merge_into_none_dict(self, module: Any) -> None:
        cfg = OmegaConf.structured(module.DictOptional)
        merged = OmegaConf.merge(cfg, {"as_none": {"x": 100}})
        with raises(ValidationError):
            merged.as_none.x = "abc"
        with raises(ValidationError):
            merged.as_none.y = "abc"

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
            OmegaConf.update(cfg, "list", update_value)
            assert cfg == expected
        else:
            with raises(ValidationError):
                OmegaConf.update(cfg, "list", update_value)

    def test_merge_missing_list_promotes_target_type(self, module: Any) -> None:
        c1 = OmegaConf.create({"missing": []})
        c2 = OmegaConf.structured(module.ConfigWithList)
        c3 = OmegaConf.merge(c1, c2)
        with raises(ValidationError):
            c3.missing.append("xx")

    def test_ignore_metadata_class_with_required_args(self, module: Any) -> None:
        cfg = OmegaConf.create(module.HasIgnoreMetadataRequired)
        assert cfg == {"no_ignore": "???"}

    def test_ignore_metadata_instance_with_required_args(self, module: Any) -> None:
        cfg = OmegaConf.create(module.HasIgnoreMetadataRequired(3, 4))
        assert cfg == {"no_ignore": 4}

    def test_ignore_metadata_class_with_default_args(self, module: Any) -> None:
        cfg = OmegaConf.create(module.HasIgnoreMetadataWithDefault)
        assert cfg == {"no_ignore": 2}

    def test_ignore_metadata_instance_with_default_args(self, module: Any) -> None:
        cfg = OmegaConf.create(module.HasIgnoreMetadataWithDefault(3, 4))
        assert cfg == {"no_ignore": 4}


class TestStructredConfigInheritance:
    def test_leaf_node_inheritance(self, module: Any) -> None:
        parent = OmegaConf.structured(module.StructuredSubclass.ParentInts)
        child = OmegaConf.structured(module.StructuredSubclass.ChildInts)

        assert OmegaConf.is_missing(parent, "int1")
        assert OmegaConf.is_missing(child, "int1")

        assert OmegaConf.is_missing(parent, "int2")
        assert child.int2 == 5

        assert OmegaConf.is_missing(parent, "int3")
        assert child.int3 == 10

        assert OmegaConf.is_missing(parent, "int4")
        assert child.int4 == 15

    def test_container_inheritance(self, module: Any) -> None:
        parent = OmegaConf.structured(module.StructuredSubclass.ParentContainers)
        child = OmegaConf.structured(module.StructuredSubclass.ChildContainers)

        assert OmegaConf.is_missing(parent, "list1")
        assert child.list1 == [1, 2, 3]

        assert parent.list2 == [5, 6]
        assert child.list2 == [5, 6]

        assert OmegaConf.is_missing(parent, "dict")
        assert child.dict == {"a": 5, "b": 6}

    @mark.parametrize(
        "create_fn",
        [
            param(lambda cls: OmegaConf.structured(cls), id="create_from_class"),
            param(lambda cls: OmegaConf.structured(cls()), id="create_from_instance"),
        ],
    )
    def test_subclass_using_default_factory(
        self, module: Any, create_fn: Callable[[Any], DictConfig]
    ) -> None:
        """
        When a structured config field has a default and a subclass defines a
        default_factory for the same field, ensure that the DictConfig created
        from the subclass uses the subclass' default_factory (not the parent
        class' default).
        """
        cfg = create_fn(module.StructuredSubclass.ChildWithDefaultFactory)
        assert cfg.no_default_to_list == ["hi"]
        assert cfg.int_to_list == ["hi"]


class TestNestedContainers:
    @mark.parametrize(
        "class_name",
        [
            "ListOfLists",
            "DictOfDicts",
            "ListsAndDicts",
            "WithDefault",
        ],
    )
    def test_instantiation(self, module: Any, class_name: str) -> None:
        cls = getattr(module.NestedContainers, class_name)
        OmegaConf.structured(cls)

    @mark.parametrize(
        "class_name, keys, expected_optional, expected_ref_type",
        [
            param("ListOfLists", "lls", False, List[List[str]], id="lls"),
            param(
                "ListOfLists",
                "llx",
                False,
                lambda module: List[List[module.User]],  # type: ignore
                id="llx",
            ),
            param("ListOfLists", "llla", False, List[List[List[Any]]], id="llla"),
            param(
                "ListOfLists",
                "lloli",
                False,
                List[List[Optional[List[int]]]],
                id="lloli",
            ),
            param(
                "ListOfLists",
                "lloli",
                False,
                List[List[Optional[List[int]]]],
                id="lloli",
            ),
            param(
                "ListOfLists", "lls_default", False, List[List[str]], id="lls_default"
            ),
            param(
                "ListOfLists", "lls_default", False, List[List[str]], id="lls_default"
            ),
            param(
                "ListOfLists", ["lls_default", 0], False, List[str], id="lls_default-0"
            ),
            param(
                "ListOfLists", ["lls_default", 1], False, List[str], id="lls_default-1"
            ),
            param(
                "ListOfLists", ["lls_default", 2], False, List[str], id="lls_default-2"
            ),
            param(
                "ListOfLists",
                "lolx_default",
                False,
                lambda module: List[Optional[List[module.User]]],  # type: ignore
                id="lolx_default",
            ),
            param(
                "ListOfLists",
                ["lolx_default", 0],
                True,
                lambda module: List[module.User],  # type: ignore
                id="lolx_default-0",
            ),
            param(
                "ListOfLists",
                ["lolx_default", 1],
                True,
                lambda module: List[module.User],  # type: ignore
                id="lolx_default-1",
            ),
            param(
                "ListOfLists",
                ["lolx_default", 2],
                True,
                lambda module: List[module.User],  # type: ignore
                id="lolx_default-2",
            ),
            param("DictOfDicts", "dsdsi", False, Dict[str, Dict[str, int]], id="dsdsi"),
            param(
                "DictOfDicts",
                ["odsdsi_default", "dsi1"],
                False,
                Dict[str, int],
                id="odsdsi_default-dsi1",
            ),
            param(
                "DictOfDicts",
                ["odsdsi_default", "dsi2"],
                False,
                Dict[str, int],
                id="odsdsi_default-dsi2",
            ),
            param(
                "DictOfDicts",
                ["odsdsi_default", "dsi3"],
                False,
                Dict[str, int],
                id="odsdsi_default-dsi3",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx1"],
                False,
                lambda module: Dict[str, module.User],  # type: ignore
                id="dsdsx_default-dsx1",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2"],
                False,
                lambda module: Dict[str, module.User],  # type: ignore
                id="dsdsx_default-dsx2",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s1"],
                False,
                lambda module: module.User,
                id="dsdsx_default-dsx2-s1",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s2"],
                False,
                lambda module: module.User,
                id="dsdsx_default-dsx2-s2",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s3"],
                False,
                lambda module: module.User,
                id="dsdsx_default-dsx2-s3",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx3"],
                False,
                lambda module: Dict[str, module.User],  # type: ignore
                id="dsdsx_default-dsx3",
            ),
            param(
                "ListsAndDicts", "lldsi", False, List[List[Dict[str, int]]], id="lldsi"
            ),
            param(
                "ListsAndDicts",
                "oldfox",
                True,
                lambda module: List[Dict[float, Optional[module.User]]],  # type: ignore
                id="oldfox",
            ),
            param(
                "ListsAndDicts",
                "oldfox",
                True,
                lambda module: List[Dict[float, Optional[module.User]]],  # type: ignore
                id="oldfox",
            ),
            param(
                "ListsAndDicts",
                ["dedsle_default", Color.RED],
                False,
                Dict[str, List[Enum1]],
                id="dedsle_default-RED",
            ),
            param(
                "WithDefault",
                "dsolx_default",
                False,
                lambda module: Dict[str, Optional[List[module.User]]],  # type: ignore
                id="dsolx_default",
            ),
            param(
                "WithDefault",
                ["dsolx_default", "lx"],
                True,
                lambda module: List[module.User],  # type: ignore
                id="dsolx_default-lx",
            ),
            param(
                "WithDefault",
                ["dsolx_default", "lx", 0],
                False,
                lambda module: module.User,
                id="dsolx_default-lx-0",
            ),
        ],
    )
    def test_metadata(
        self,
        module: Any,
        class_name: str,
        keys: Any,
        expected_optional: bool,
        expected_ref_type: Any,
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        node = OmegaConf.structured(cls)

        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            node = node._get_node(key)

        if inspect.isfunction(expected_ref_type):
            expected_ref_type = expected_ref_type(module)

        assert node._metadata.optional == expected_optional
        assert node._metadata.ref_type == expected_ref_type

        if _utils.is_dict_annotation(expected_ref_type):
            expected_key_type, expected_element_type = _utils.get_dict_key_value_types(
                expected_ref_type
            )
            assert node._metadata.key_type == expected_key_type
            assert node._metadata.element_type == expected_element_type

        if _utils.is_list_annotation(expected_ref_type):
            expected_element_type = _utils.get_list_element_type(expected_ref_type)
            assert node._metadata.element_type == expected_element_type

    @mark.parametrize(
        "class_name, key, value",
        [
            param("ListOfLists", "lls", [["a", "b"], ["c"]], id="lls"),
            param("ListOfLists", "lls", [], id="lls-empty"),
            param("ListOfLists", "lls", [[]], id="lls-list-of-empty"),
            param(
                "ListOfLists",
                "lls_default",
                [["a", "b"], ["c"]],
                id="lls_default",
            ),
            param(
                "ListOfLists",
                "llx",
                lambda module: [[module.User("Bond", 7)]],
                id="llx",
            ),
            param(
                "ListOfLists",
                "lolx_default",
                lambda module: [[module.User("Bond", 7)]],
                id="lolx_default",
            ),
            param("DictOfDicts", "dsdsi", {"abc": {"xyz": 123}}, id="dsdsi"),
            param("DictOfDicts", "dsdbi", {"abc": {True: 456}}, id="dsdbi"),
            param(
                "DictOfDicts",
                "dsdsx",
                lambda module: {"abc": {"xyz": module.User("Bond", 7)}},
                id="dsdsx",
            ),
        ],
    )
    def test_legal_assignment(
        self, module: Any, class_name: str, key: str, value: Any
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        cfg = OmegaConf.structured(cls)
        if inspect.isfunction(value):
            value = value(module)

        cfg[key] = value

        assert cfg[key] == value

    @mark.parametrize(
        "class_name, key, value, expected",
        [
            param(
                "ListOfLists",
                "lls",
                [["123", 456]],
                [["123", "456"]],
                id="lls-conversion-from-int",
            ),
            param("ListOfLists", "lls", [["123", 456]], [["123", "456"]], id="lls"),
            param("ListOfLists", "llla", [[["123", 456]]], [[["123", 456]]], id="llla"),
            param("ListOfLists", "lloli", [[["123", 456]]], [[[123, 456]]], id="lloli"),
            param(
                "DictOfDicts",
                "dsdbi",
                {"abc": {True: "456"}},
                {"abc": {True: 456}},
                id="dsdbi",
            ),
        ],
    )
    def test_assignment_conversion(
        self, module: Any, class_name: str, key: str, value: Any, expected: Any
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        cfg = OmegaConf.structured(cls)
        if inspect.isfunction(value):
            value = value(module)

        cfg[key] = value

        assert cfg[key] == expected

    @mark.parametrize(
        "class_name, key, value, err_type",
        [
            param(
                "ListOfLists",
                "lloli",
                [[["abc"]]],
                ValidationError,
                id="assign-llls-to-lloli",
            ),
            param(
                "ListOfLists",
                "llx",
                [[{"name": "Bond", "age": 7}]],
                ValidationError,
                id="assign-lld-to-llx",
            ),
            param(
                "DictOfDicts",
                "dsdbi",
                {123: {True: 456}},
                KeyValidationError,
                id="assign-didbi-to-dsdbi",
            ),
            param(
                "DictOfDicts",
                "dsdbi",
                {"abc": {"True": 456}},
                KeyValidationError,
                id="assign-dsdsi-to-dsdbi",
            ),
        ],
    )
    def test_illegal_assignment(
        self, module: Any, class_name: str, key: str, value: Any, err_type: Any
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        cfg = OmegaConf.structured(cls)

        with raises(err_type):
            cfg[key] = value

    @mark.parametrize(
        "class_name, keys, expected",
        [
            param("ListOfLists", ["lls"], MISSING, id="lls-missing"),
            param("ListOfLists", ["lls_default", 0], [], id="lls_default-empty-list"),
            param("ListOfLists", ["lls_default", 1, 0], "abc", id="lls_default-str"),
            param(
                "ListOfLists",
                ["lls_default", 1, 2],
                "123",
                id="lls_default-int-converted",
            ),
            param(
                "ListOfLists",
                ["lls_default", 1, 3],
                MISSING,
                id="lls_default-missing-nested",
            ),
            param("ListOfLists", ["lls_default", 2], MISSING, id="lls_default-missing"),
            param("DictOfDicts", ["dsdsi"], MISSING, id="dsdsi-missing"),
            param(
                "DictOfDicts", ["dsdsx_default", "dsx1"], {}, id="dsdsx_default-empty"
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s1"],
                {"name": "???", "age": "???"},
                id="dsdsx_default-user-missing-data",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s2"],
                {"name": "Bond", "age": 7},
                id="dsdsx_default-user",
            ),
            param(
                "DictOfDicts",
                ["dsdsx_default", "dsx2", "s3"],
                MISSING,
                id="dsdsx_default-missing-user",
            ),
            param(
                "DictOfDicts",
                ["odsdsi_default", "dsi2", "s2"],
                123,
                id="dsdsi-str-converted-to-int",
            ),
        ],
    )
    def test_default_values(
        self, module: Any, class_name: str, keys: Any, expected: Any
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        node = OmegaConf.structured(cls)

        if not isinstance(keys, list):
            keys = [keys]
        for key in keys:
            node = node._get_node(key)

        if expected is MISSING:
            assert node._is_missing()
        else:
            assert node == expected

    @mark.parametrize(
        "class_name, keys, value, is_legal",
        [
            param("WithDefault", "dsolx_default", None, False, id="dsolx=none-illegal"),
            param(
                "WithDefault", ["dsolx_default", "lx"], None, True, id="olx=none-legal"
            ),
            param(
                "WithDefault", "dsolx_default", {"s": None}, True, id="dsolx=dn-legal"
            ),
            param(
                "WithDefault",
                ["dsolx_default", "lx", 0],
                None,
                False,
                id="x=none-illegal",
            ),
            param("DictOfDicts", "odsdsi_default", None, True, id="odsdsi=none-legal"),
            param("DictOfDicts", "dsdsx", None, False, id="dsdsx=none-illegal"),
            param(
                "DictOfDicts",
                ["odsdsi_default", "dsi1"],
                None,
                False,
                id="dsi=none-illegal",
            ),
            param("DictOfDicts", "dsdsx", {"s": None}, False, id="dsdsx=dsn-illegal"),
            param("ListOfLists", "lloli", None, False, id="lloli=n-illegal"),
            param("ListOfLists", "lloli", [None], False, id="lloli=ln-illegal"),
            param("ListOfLists", "lloli", [[None]], True, id="lloli=lln-legal"),
            param("ListOfLists", "lloli", [[[None]]], False, id="lloli=llln-illegal"),
            param("ListOfLists", ["lolx_default"], None, False, id="lolx=n-illegal"),
            param("ListOfLists", ["lolx_default", 1], None, True, id="olx=n-legal"),
            param(
                "ListOfLists", ["lolx_default", 1, 0], None, False, id="lx=n-illegal"
            ),
        ],
    )
    def test_assign_none(
        self, module: Any, class_name: str, keys: Any, value: Any, is_legal: bool
    ) -> None:
        cls = getattr(module.NestedContainers, class_name)
        node = OmegaConf.structured(cls)

        if not isinstance(keys, list):
            keys = [keys]
        for key in keys[:-1]:
            node = node[key]
        last_key = keys[-1]

        if is_legal:
            node[last_key] = value
            assert node[last_key] == value
        else:
            with raises(ValidationError):
                node[last_key] = value


class TestUnionsOfPrimitiveTypes:
    @mark.parametrize(
        "class_name, key, expected_type_hint, expected_val",
        [
            param("Simple", "uis", Union[int, str], MISSING, id="simple-uis"),
            param("Simple", "ubc", Union[bool, Color], MISSING, id="simple-ubc"),
            param("Simple", "uxf", Union[bytes, float], MISSING, id="simple-uxf"),
            param(
                "Simple", "ouis", Optional[Union[int, str]], MISSING, id="simple-ouis"
            ),
            param("Simple", "uisn", Union[int, str, None], MISSING, id="simple-uisn"),
            param(
                "Simple", "uisN", Union[int, str, type(None)], MISSING, id="simple-uisN"
            ),
            param("WithDefaults", "uis", Union[int, str], "abc", id="defaults-uis"),
            param("WithDefaults", "ubc1", Union[bool, Color], True, id="defaults-ubc1"),
            param(
                "WithDefaults",
                "ubc2",
                Union[bool, Color],
                Color.RED,
                id="defaults-ubc2",
            ),
            param("WithDefaults", "uxf", Union[bytes, float], 1.2, id="defaults-uxf"),
            param(
                "WithDefaults",
                "ouis",
                Optional[Union[int, str]],
                None,
                id="defaults-ouis",
            ),
            param(
                "WithDefaults", "uisn", Union[int, str, None], 123, id="defaults-uisn"
            ),
            param(
                "WithDefaults",
                "uisN",
                Union[int, str, type(None)],
                "abc",
                id="defaults-uisN",
            ),
            param(
                "WithExplicitMissing",
                "uis_missing",
                Union[int, str],
                MISSING,
                id="uis_missing",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                List[Union[bool, Color]],
                MISSING,
                id="lubc",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                Dict[str, Union[bool, float]],
                MISSING,
                id="dsubf",
            ),
            param(
                "ContainersOfUnions",
                "lubc_with_default",
                List[Union[bool, Color]],
                [True, Color.RED],
                id="lubc_with_default",
            ),
            param(
                "ContainersOfUnions",
                "dsubf_with_default",
                Dict[str, Union[bool, float]],
                {"abc": True, "xyz": 1.2},
                id="dsubf_with_default",
            ),
            param(
                "InterpolationFromUnion",
                "ubi_with_default",
                Union[bool, int],
                "${an_int}",
                id="iterp-from-union",
            ),
            param(
                "InterpolationFromUnion",
                "ubi_with_default",
                Union[bool, int],
                123,
                id="iterp-from-union-resolved",
            ),
            param(
                "InterpolationToUnion",
                "a_float",
                float,
                10.1,
                id="iterp-to-union-resolved",
            ),
        ],
    )
    def test_union_instantiation(
        self,
        module: Any,
        class_name: str,
        key: str,
        expected_type_hint: Any,
        expected_val: Any,
    ) -> None:
        class_ = getattr(module.UnionsOfPrimitveTypes, class_name)
        cfg = OmegaConf.structured(class_)

        assert _utils.get_type_hint(cfg, key) == expected_type_hint

        vk = _utils.get_value_kind(expected_val)

        if vk is _utils.ValueKind.VALUE:
            assert cfg[key] == expected_val
            if _utils.is_primitive_type_annotation(type(expected_val)):
                assert type(cfg[key]) == type(expected_val)
            else:
                assert isinstance(cfg[key], Container)

        elif vk is _utils.ValueKind.MANDATORY_MISSING:
            assert OmegaConf.is_missing(cfg, key)
            assert cfg._get_node(key)._value() == expected_val

        elif vk is _utils.ValueKind.INTERPOLATION:
            assert OmegaConf.is_interpolation(cfg, key)
            assert cfg._get_node(key)._value() == expected_val

    @mark.parametrize(
        "class_name, expected_err",
        [
            param(
                "WithBadDefaults1",
                re.escape(
                    "Value 'None' is incompatible with type hint 'Union[int, str]"
                ),
                id="assign-none-to-uis",
            ),
            param(
                "WithBadDefaults2",
                re.escape(
                    "Value 'abc' of type 'str' is incompatible with type hint 'Union[bool, Color]'"
                ),
                id="assign-str-to-ubc",
            ),
            param(
                "WithBadDefaults3",
                re.escape(
                    "Value 'True' of type 'bool' is incompatible with type hint 'Union[bytes, float]'"
                ),
                id="assign-bool-to-uxf",
            ),
            param(
                "WithBadDefaults4",
                re.escape(
                    "Value 'Color.RED' of type 'tests.Color' is incompatible"
                    + " with type hint 'Optional[Union["
                )
                + r"(bool, float)|(float, bool)\]\]'",
                id="assign-enum-to-oufb",
            ),
        ],
    )
    def test_union_instantiation_with_bad_defaults(
        self, module: Any, class_name: str, expected_err: str
    ) -> None:
        class_ = getattr(module.UnionsOfPrimitveTypes, class_name)
        with raises(ValidationError, match=expected_err):
            OmegaConf.structured(class_)

    @mark.parametrize(
        "class_name, key, value, expected",
        [
            param("Simple", "uis", 123, 123, id="simple-uis-int"),
            param("Simple", "uis", "123", "123", id="simple-uis-int_string"),
            param("Simple", "uis", "abc", "abc", id="simple-uis-str"),
            param("Simple", "uis", None, raises(ValidationError), id="simple-uis-none"),
            param("Simple", "uis", MISSING, MISSING, id="simple-uis-missing"),
            param("Simple", "uis", "${interp}", "${interp}", id="simple-uis-interp"),
            param("Simple", "ubc", True, True, id="simple-ubc-bool"),
            param("Simple", "ubc", Color.RED, Color.RED, id="simple-ubc-color"),
            param(
                "Simple",
                "ubc",
                "RED",
                raises(ValidationError),
                id="simple-ubc-color_str",
            ),
            param(
                "Simple",
                "ubc",
                "a_string",
                raises(ValidationError),
                id="simple-ubc-str",
            ),
            param("Simple", "ubc", None, raises(ValidationError), id="simple-ubc-none"),
            param("Simple", "ubc", MISSING, MISSING, id="simple-ubc-missing"),
            param("Simple", "ubc", "${interp}", "${interp}", id="simple-ubc-interp"),
            param("Simple", "ouis", None, None, id="simple-ouis-none"),
            param("WithDefaults", "uis", 123, 123, id="with_defaults-uis-int"),
            param(
                "WithDefaults", "uis", "123", "123", id="with_defaults-uis-int_string"
            ),
            param("WithDefaults", "uis", "abc", "abc", id="with_defaults-uis-str"),
            param(
                "WithDefaults",
                "uis",
                None,
                raises(ValidationError),
                id="with_defaults-uis-none",
            ),
            param(
                "WithDefaults", "uis", MISSING, MISSING, id="with_defaults-uis-missing"
            ),
            param(
                "WithDefaults",
                "uis",
                "${interp}",
                "${interp}",
                id="with_defaults-uis-interp",
            ),
            param("WithDefaults", "ubc1", True, True, id="with_defaults-ubc-bool"),
            param(
                "WithDefaults",
                "ubc1",
                Color.RED,
                Color.RED,
                id="with_defaults-ubc-color",
            ),
            param(
                "WithDefaults",
                "ubc1",
                "RED",
                raises(ValidationError),
                id="with_defaults-ubc-color_str",
            ),
            param(
                "WithDefaults",
                "ubc1",
                "a_string",
                raises(ValidationError),
                id="with_defaults-ubc-str",
            ),
            param(
                "WithDefaults",
                "ubc1",
                None,
                raises(ValidationError),
                id="with_defaults-ubc-none",
            ),
            param(
                "WithDefaults", "ubc1", MISSING, MISSING, id="with_defaults-ubc-missing"
            ),
            param(
                "WithDefaults",
                "ubc1",
                "${interp}",
                "${interp}",
                id="with_defaults-ubc-interp",
            ),
            param("WithDefaults", "ouis", None, None, id="with_defaults-ouis-none"),
            param("ContainersOfUnions", "lubc", MISSING, MISSING, id="lubc-missing"),
            param(
                "ContainersOfUnions",
                "lubc",
                None,
                raises(ValidationError),
                id="lubc-none",
            ),
            param(
                "ContainersOfUnions", "lubc", "${interp}", "${interp}", id="lubc-interp"
            ),
            param("ContainersOfUnions", "lubc", [], [], id="lubc-list-empty"),
            param(
                "ContainersOfUnions",
                "lubc",
                [Color.GREEN],
                [Color.GREEN],
                id="lubc-list-enum",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                ["GREEN"],
                raises(ValidationError),
                id="lubc-list-enum_str",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                ["abc"],
                raises(ValidationError),
                id="lubc-list-str",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                [None],
                raises(ValidationError),
                id="lubc-list-none",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                [MISSING],
                [MISSING],
                id="lubc-list-missing",
            ),
            param(
                "ContainersOfUnions",
                "lubc",
                ["${interp}"],
                ["${interp}"],
                id="lubc-list-interp",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"bool": True, "float": 10.1},
                {"bool": True, "float": 10.1},
                id="dsubf",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"float-str": "10.1"},
                raises(ValidationError),
                id="dsubf-float-str",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"str": "abc"},
                raises(ValidationError),
                id="dsubf-dict-str",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"none": None},
                raises(ValidationError),
                id="dsubf-dict-none",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"missing": MISSING},
                {"missing": MISSING},
                id="dsubf-dict-missing",
            ),
            param(
                "ContainersOfUnions",
                "dsubf",
                {"interp": "${interp}"},
                {"interp": "${interp}"},
                id="dsubf-dict-interp",
            ),
            param(
                "ContainersOfUnions",
                "dsoubf",
                {"none": None},
                {"none": None},
                id="dsoubf-dict-none",
            ),
        ],
    )
    def test_assignment_to_union(
        self, module: Any, class_name: str, key: str, value: Any, expected: Any
    ) -> None:
        class_ = getattr(module.UnionsOfPrimitveTypes, class_name)
        cfg = OmegaConf.structured(class_)

        if isinstance(expected, RaisesContext):
            with expected:
                cfg[key] = value

        else:
            cfg[key] = value

            vk = _utils.get_value_kind(expected)

            if vk is _utils.ValueKind.VALUE:
                assert cfg[key] == expected

            elif vk is _utils.ValueKind.MANDATORY_MISSING:
                assert OmegaConf.is_missing(cfg, key)
                assert _utils._get_value(cfg._get_node(key)) == expected

            elif vk is _utils.ValueKind.INTERPOLATION:
                assert OmegaConf.is_interpolation(cfg, key)
                assert _utils._get_value(cfg._get_node(key)) == expected

    @mark.parametrize(
        "key, value, expected",
        [
            param("ubi", "${an_int}", 123, id="interp-to-int"),
            param(
                "ubi",
                "${none}",
                raises(ValidationError),
                id="interp-to-none-err",
                marks=mark.xfail(reason="interpolations from unions are not validated"),
            ),
            param(
                "ubi",
                "${a_string}",
                raises(ValidationError),
                id="interp-to-str-err",
                marks=mark.xfail(reason="interpolations from unions are not validated"),
            ),
            param(
                "ubi",
                "${missing}",
                raises(InterpolationToMissingValueError),
                id="interp-to-missing",
            ),
            param("oubi", "${none}", None, id="interp-to-none"),
        ],
    )
    @mark.parametrize("overwrite_default", [True, False])
    def test_interpolation_from_union(
        self, module: Any, key: str, overwrite_default: bool, value: Any, expected: Any
    ) -> None:
        class_ = module.UnionsOfPrimitveTypes.InterpolationFromUnion
        cfg = OmegaConf.structured(class_)

        if overwrite_default:
            key += "_with_default"

        cfg[key] = value

        assert _utils._get_value(cfg._get_node(key)) == value

        if isinstance(expected, RaisesContext):
            with expected:
                cfg[key]
        else:
            assert cfg[key] == expected

    def test_resolve_union_interpolation(self, module: Any) -> None:
        class_ = module.UnionsOfPrimitveTypes.InterpolationFromUnion
        cfg = OmegaConf.structured(class_)
        assert OmegaConf.is_interpolation(cfg, "ubi_with_default")
        assert OmegaConf.is_interpolation(cfg, "oubi_with_default")
        OmegaConf.resolve(cfg)
        assert not OmegaConf.is_interpolation(cfg, "ubi_with_default")
        assert not OmegaConf.is_interpolation(cfg, "oubi_with_default")

    def test_resolve_union_interpolation_error(self, module: Any) -> None:
        class_ = module.UnionsOfPrimitveTypes.BadInterpolationFromUnion
        cfg = OmegaConf.structured(class_)
        assert OmegaConf.is_interpolation(cfg, "ubi")
        with raises(ValidationError):
            OmegaConf.resolve(cfg)

    @mark.parametrize(
        "key, expected",
        [
            param("a_float", 10.1, id="interp-to-float"),
            param("bad_int_interp", raises(ValidationError), id="bad-int-interp"),
        ],
    )
    def test_interpolation_to_union(self, module: Any, key: str, expected: Any) -> None:
        class_ = module.UnionsOfPrimitveTypes.InterpolationToUnion
        cfg = OmegaConf.structured(class_)

        if isinstance(expected, RaisesContext):
            with expected:
                cfg[key]
        else:
            assert cfg[key] == expected

    @mark.skipif(sys.version_info < (3, 10), reason="requires Python 3.10 or newer")
    def test_support_pep_604(self, module: Any) -> None:
        class_ = module.UnionsOfPrimitveTypes.SupportPEP604
        cfg = OmegaConf.structured(class_)
        assert _utils.get_type_hint(cfg, "uis") == Union[int, str]
        assert _utils.get_type_hint(cfg, "ouis") == Optional[Union[int, str]]
        assert _utils.get_type_hint(cfg, "uisn") == Optional[Union[int, str]]
        assert _utils.get_type_hint(cfg, "uis_with_default") == Union[int, str]
        assert cfg.uisn is None
        assert cfg.uis_with_default == 123

    @mark.skipif(sys.version_info < (3, 9), reason="requires Python 3.9 or newer")
    def test_support_pep_585(self, module: Any) -> None:
        class_ = module.SupportPEP585
        cfg = OmegaConf.structured(class_)
        assert _utils.get_type_hint(cfg, "dict_") == Dict[int, str]
        assert _utils.get_type_hint(cfg, "list_") == List[int]
        assert _utils.get_type_hint(cfg, "tuple_") == Tuple[int]
        assert _utils.get_type_hint(cfg, "dict_no_subscript") == Dict[Any, Any]
        assert _utils.get_type_hint(cfg, "list_no_subscript") == List[Any]
        assert _utils.get_type_hint(cfg, "tuple_no_subscript") == Tuple[Any, ...]

    def test_assign_path_to_string_typed_field(self, module: Any) -> None:
        cfg = OmegaConf.create(module.StringConfig)
        cfg.null_default = Path("hello.txt")
        assert isinstance(cfg.null_default, str)
        assert cfg.null_default == "hello.txt"
