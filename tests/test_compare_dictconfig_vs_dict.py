"""
This file compares DictConfig methods with the corresponding
methods of standard python's dict.
The following methods are compared:
    __contains__
    __delitem__
    __eq__
    __getitem__
    __setitem__
    get
    pop
    keys
    values
    items

We have separate test classes for the following cases:
    TestUntypedDictConfig: for DictConfig without a set key_type
    TestPrimitiveTypeDunderMethods: for DictConfig where key_type is primitive
    TestEnumTypeDunderMethods: for DictConfig where key_type is Enum
"""
from copy import deepcopy
from enum import Enum
from typing import Any, Dict, Optional

from pytest import fixture, mark, param, raises

from omegaconf import DictConfig, OmegaConf
from omegaconf.errors import ConfigKeyError, ConfigTypeError, KeyValidationError
from tests import Enum1


@fixture(
    params=[
        "str",
        b"abc",
        1,
        3.1415,
        True,
        Enum1.FOO,
    ]
)
def key(request: Any) -> Any:
    """A key to test indexing into DictConfig."""
    return request.param


@fixture
def python_dict(data: Dict[Any, Any]) -> Dict[Any, Any]:
    """Just a standard python dictionary, to be used in comparison with DictConfig."""
    return deepcopy(data)


@fixture(params=[None, False, True])
def struct_mode(request: Any) -> Optional[bool]:
    struct_mode: Optional[bool] = request.param
    return struct_mode


@mark.parametrize(
    "data",
    [
        param({"a": 10}, id="str"),
        param({b"abc": 10}, id="bytes"),
        param({1: "a"}, id="int"),
        param({123.45: "a"}, id="float"),
        param({True: "a"}, id="bool"),
        param({Enum1.FOO: "foo"}, id="Enum1"),
    ],
)
class TestUntypedDictConfig:
    """Compare DictConfig with python dict in the case where key_type is not set."""

    @fixture
    def cfg(self, python_dict: Any, struct_mode: Optional[bool]) -> DictConfig:
        """Create a DictConfig instance from the given data"""
        cfg: DictConfig = DictConfig(content=python_dict)
        OmegaConf.set_struct(cfg, struct_mode)
        return cfg

    def test__setitem__(
        self, python_dict: Any, cfg: DictConfig, key: Any, struct_mode: Optional[bool]
    ) -> None:
        """Ensure that __setitem__ has same effect on python dict and on DictConfig."""
        if struct_mode and key not in cfg:
            with raises(ConfigKeyError):
                cfg[key] = "sentinel"
        else:
            python_dict[key] = "sentinel"
            cfg[key] = "sentinel"
            assert python_dict == cfg

    def test__getitem__(self, python_dict: Any, cfg: DictConfig, key: Any) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        try:
            result = python_dict[key]
        except KeyError:
            with raises(ConfigKeyError):
                cfg[key]
        else:
            assert result == cfg[key]

    @mark.parametrize("struct_mode", [False, None])
    def test__delitem__(self, python_dict: Any, cfg: DictConfig, key: Any) -> None:
        """Ensure that __delitem__ has same result with python dict as with DictConfig."""
        try:
            del python_dict[key]
            assert key not in python_dict
        except KeyError:
            with raises(ConfigKeyError):
                del cfg[key]
        else:
            del cfg[key]
            assert key not in cfg

    @mark.parametrize("struct_mode", [True])
    def test__delitem__struct_mode(
        self, python_dict: Any, cfg: DictConfig, key: Any
    ) -> None:
        """Ensure that __delitem__ fails in struct_mode"""
        with raises(ConfigTypeError):
            del cfg[key]

    def test__contains__(self, python_dict: Any, cfg: Any, key: Any) -> None:
        """Ensure that __contains__ has same result with python dict as with DictConfig."""
        assert (key in python_dict) == (key in cfg)

    def test__eq__(self, python_dict: Any, cfg: Any, key: Any) -> None:
        assert python_dict == cfg

    def test_get(self, python_dict: Any, cfg: DictConfig, key: Any) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        assert python_dict.get(key) == cfg.get(key)

    def test_get_with_default(
        self, python_dict: Any, cfg: DictConfig, key: Any
    ) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        assert python_dict.get(key, "DEFAULT") == cfg.get(key, "DEFAULT")

    @mark.parametrize("struct_mode", [False, None])
    def test_pop(
        self,
        python_dict: Any,
        cfg: DictConfig,
        key: Any,
    ) -> None:
        """Ensure that pop has same result with python dict as with DictConfig."""
        try:
            result = python_dict.pop(key)
        except KeyError:
            with raises(ConfigKeyError):
                cfg.pop(key)
        else:
            assert result == cfg.pop(key)
        assert python_dict.keys() == cfg.keys()

    @mark.parametrize("struct_mode", [True])
    def test_pop_struct_mode(
        self,
        python_dict: Any,
        cfg: DictConfig,
        key: Any,
    ) -> None:
        """Ensure that pop fails in struct mode."""
        with raises(ConfigTypeError):
            cfg.pop(key)

    @mark.parametrize("struct_mode", [False, None])
    def test_pop_with_default(
        self,
        python_dict: Any,
        cfg: DictConfig,
        key: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) has same result with python dict as with DictConfig."""
        assert python_dict.pop(key, "DEFAULT") == cfg.pop(key, "DEFAULT")
        assert python_dict.keys() == cfg.keys()

    @mark.parametrize("struct_mode", [True])
    def test_pop_with_default_struct_mode(
        self,
        python_dict: Any,
        cfg: DictConfig,
        key: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) fails in struct mode."""
        with raises(ConfigTypeError):
            cfg.pop(key, "DEFAULT")

    def test_keys(self, python_dict: Any, cfg: Any) -> None:
        assert python_dict.keys() == cfg.keys()

    def test_values(self, python_dict: Any, cfg: Any) -> None:
        assert list(python_dict.values()) == list(cfg.values())

    def test_items(self, python_dict: Any, cfg: Any) -> None:
        assert list(python_dict.items()) == list(cfg.items())


@fixture
def cfg_typed(
    python_dict: Any, cfg_key_type: Any, struct_mode: Optional[bool]
) -> DictConfig:
    """Create a DictConfig instance that has strongly-typed keys"""
    cfg_typed: DictConfig = DictConfig(content=python_dict, key_type=cfg_key_type)
    OmegaConf.set_struct(cfg_typed, struct_mode)
    return cfg_typed


@mark.parametrize(
    "cfg_key_type,data",
    [
        (str, {"a": 10}),
        (bytes, {b"abc": "a"}),
        (int, {1: "a"}),
        (float, {123.45: "a"}),
        (bool, {True: "a"}),
    ],
)
class TestPrimitiveTypeDunderMethods:
    """Compare DictConfig with python dict in the case where key_type is a primitive type."""

    def test__setitem__primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
        struct_mode: Optional[bool],
    ) -> None:
        """When DictConfig keys are strongly typed,
        ensure that __setitem__ has same effect on python dict and on DictConfig."""
        if struct_mode and key not in cfg_typed:
            if isinstance(key, cfg_key_type) or (
                cfg_key_type == bool and key in (0, 1)
            ):
                with raises(ConfigKeyError):
                    cfg_typed[key] = "sentinel"
            else:
                with raises(KeyValidationError):
                    cfg_typed[key] = "sentinel"
        else:
            python_dict[key] = "sentinel"
            if isinstance(key, cfg_key_type) or (
                cfg_key_type == bool and key in (0, 1)
            ):
                cfg_typed[key] = "sentinel"
                assert python_dict == cfg_typed
            else:
                with raises(KeyValidationError):
                    cfg_typed[key] = "sentinel"

    def test__getitem__primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """When Dictconfig keys are strongly typed,
        ensure that __getitem__ has same result with python dict as with DictConfig."""
        try:
            result = python_dict[key]
        except KeyError:
            if isinstance(key, cfg_key_type) or (
                cfg_key_type == bool and key in (0, 1)
            ):
                with raises(ConfigKeyError):
                    cfg_typed[key]
            else:
                with raises(KeyValidationError):
                    cfg_typed[key]
        else:
            assert result == cfg_typed[key]

    @mark.parametrize("struct_mode", [False, None])
    def test__delitem__primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """When Dictconfig keys are strongly typed,
        ensure that __delitem__ has same result with python dict as with DictConfig."""
        try:
            del python_dict[key]
            assert key not in python_dict
        except KeyError:
            if isinstance(key, cfg_key_type) or (
                cfg_key_type == bool and key in (0, 1)
            ):
                with raises(ConfigKeyError):
                    del cfg_typed[key]
            else:
                with raises(KeyValidationError):
                    del cfg_typed[key]
        else:
            del cfg_typed[key]
            assert key not in cfg_typed

    @mark.parametrize("struct_mode", [True])
    def test__delitem__primitive_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure ensure that struct-mode __delitem__ raises ConfigTypeError or KeyValidationError"""
        if isinstance(key, cfg_key_type) or (cfg_key_type == bool and key in (0, 1)):
            with raises(ConfigTypeError):
                del cfg_typed[key]
        else:
            with raises(KeyValidationError):
                del cfg_typed[key]

    def test__contains__primitive_typed(
        self, python_dict: Any, cfg_typed: Any, key: Any
    ) -> None:
        """Ensure that __contains__ has same result with python dict as with DictConfig."""
        assert (key in python_dict) == (key in cfg_typed)

    def test__eq__primitive_typed(
        self, python_dict: Any, cfg_typed: Any, key: Any
    ) -> None:
        assert python_dict == cfg_typed

    def test_get_primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        if isinstance(key, cfg_key_type) or (cfg_key_type == bool and key in (0, 1)):
            assert python_dict.get(key) == cfg_typed.get(key)
        else:
            with raises(KeyValidationError):
                cfg_typed.get(key)

    def test_get_with_default_primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        if isinstance(key, cfg_key_type) or (cfg_key_type == bool and key in (0, 1)):
            assert python_dict.get(key, "DEFAULT") == cfg_typed.get(key, "DEFAULT")
        else:
            with raises(KeyValidationError):
                cfg_typed.get(key, "DEFAULT")

    @mark.parametrize("struct_mode", [False, None])
    def test_pop_primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop has same result with python dict as with DictConfig."""
        if isinstance(key, cfg_key_type) or (cfg_key_type == bool and key in (0, 1)):
            try:
                result = python_dict.pop(key)
            except KeyError:
                with raises(ConfigKeyError):
                    cfg_typed.pop(key)
            else:
                assert result == cfg_typed.pop(key)
            assert python_dict.keys() == cfg_typed.keys()
        else:
            with raises(KeyValidationError):
                cfg_typed.pop(key)

    @mark.parametrize("struct_mode", [True])
    def test_pop_primitive_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop fails in struct mode."""
        with raises(ConfigTypeError):
            cfg_typed.pop(key)

    @mark.parametrize("struct_mode", [False, None])
    def test_pop_with_default_primitive_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) has same result with python dict as with DictConfig."""
        if isinstance(key, cfg_key_type) or (cfg_key_type == bool and key in (0, 1)):
            assert python_dict.pop(key, "DEFAULT") == cfg_typed.pop(key, "DEFAULT")
            assert python_dict.keys() == cfg_typed.keys()
        else:
            with raises(KeyValidationError):
                cfg_typed.pop(key, "DEFAULT")

    @mark.parametrize("struct_mode", [True])
    def test_pop_with_default_primitive_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) fails in struct mode"""
        with raises(ConfigTypeError):
            cfg_typed.pop(key)

    def test_keys_primitive_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert python_dict.keys() == cfg_typed.keys()

    def test_values_primitive_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert list(python_dict.values()) == list(cfg_typed.values())

    def test_items_primitive_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert list(python_dict.items()) == list(cfg_typed.items())


@mark.parametrize("cfg_key_type,data", [(Enum1, {Enum1.FOO: "foo"})])
class TestEnumTypeDunderMethods:
    """Compare DictConfig with python dict in the case where key_type is an Enum type."""

    @fixture
    def key_coerced(self, key: Any, cfg_key_type: Any) -> Any:
        """
        This handles key coersion in the special case where DictConfig key_type
        is a subclass of Enum: keys of type `str` or `int` are coerced to `key_type`.
        See https://github.com/omry/omegaconf/pull/484#issuecomment-765772019
        """
        assert issubclass(cfg_key_type, Enum)
        if type(key) == str and key in [e.name for e in cfg_key_type]:
            return cfg_key_type[key]
        elif type(key) == int and key in [e.value for e in cfg_key_type]:
            return cfg_key_type(key)
        else:
            return key

    def test__setitem__enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
        struct_mode: Optional[bool],
    ) -> None:
        """When DictConfig keys are strongly typed,
        ensure that __setitem__ has same effect on python dict and on DictConfig."""
        if struct_mode and key_coerced not in cfg_typed:
            if isinstance(key_coerced, cfg_key_type):
                with raises(ConfigKeyError):
                    cfg_typed[key] = "sentinel"
            else:
                with raises(KeyValidationError):
                    cfg_typed[key] = "sentinel"
        else:
            python_dict[key_coerced] = "sentinel"
            if isinstance(key_coerced, cfg_key_type):
                cfg_typed[key] = "sentinel"
                assert python_dict == cfg_typed
            else:
                with raises(KeyValidationError):
                    cfg_typed[key] = "sentinel"

    def test__getitem__enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """When Dictconfig keys are strongly typed,
        ensure that __getitem__ has same result with python dict as with DictConfig."""
        try:
            result = python_dict[key_coerced]
        except KeyError:
            if isinstance(key_coerced, cfg_key_type):
                with raises(ConfigKeyError):
                    cfg_typed[key]
            else:
                with raises(KeyValidationError):
                    cfg_typed[key]
        else:
            assert result == cfg_typed[key]

    @mark.parametrize("struct_mode", [False, None])
    def test__delitem__enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """When Dictconfig keys are strongly typed,
        ensure that __delitem__ has same result with python dict as with DictConfig."""
        try:
            del python_dict[key_coerced]
            assert key_coerced not in python_dict
        except KeyError:
            if isinstance(key_coerced, cfg_key_type):
                with raises(ConfigKeyError):
                    del cfg_typed[key]
            else:
                with raises(KeyValidationError):
                    del cfg_typed[key]
        else:
            del cfg_typed[key]
            assert key not in cfg_typed

    @mark.parametrize("struct_mode", [True])
    def test__delitem__enum_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that __delitem__ errors in struct mode"""
        if isinstance(key_coerced, cfg_key_type):
            with raises(ConfigTypeError):
                del cfg_typed[key]
        else:
            with raises(KeyValidationError):
                del cfg_typed[key]

    def test__contains__enum_typed(
        self, python_dict: Any, cfg_typed: Any, key: Any, key_coerced: Any
    ) -> None:
        """Ensure that __contains__ has same result with python dict as with DictConfig."""
        assert (key_coerced in python_dict) == (key in cfg_typed)

    def test__eq__enum_typed(self, python_dict: Any, cfg_typed: Any, key: Any) -> None:
        assert python_dict == cfg_typed

    def test_get_enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        if isinstance(key_coerced, cfg_key_type):
            assert python_dict.get(key_coerced) == cfg_typed.get(key)
        else:
            with raises(KeyValidationError):
                cfg_typed.get(key)

    def test_get_with_default_enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that __getitem__ has same result with python dict as with DictConfig."""
        if isinstance(key_coerced, cfg_key_type):
            assert python_dict.get(key_coerced, "DEFAULT") == cfg_typed.get(
                key, "DEFAULT"
            )
        else:
            with raises(KeyValidationError):
                cfg_typed.get(key, "DEFAULT")

    @mark.parametrize("struct_mode", [False, None])
    def test_pop_enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop has same result with python dict as with DictConfig."""
        if isinstance(key_coerced, cfg_key_type):
            try:
                result = python_dict.pop(key_coerced)
            except KeyError:
                with raises(ConfigKeyError):
                    cfg_typed.pop(key)
            else:
                assert result == cfg_typed.pop(key)
            assert python_dict.keys() == cfg_typed.keys()
        else:
            with raises(KeyValidationError):
                cfg_typed.pop(key)

    @mark.parametrize("struct_mode", [True])
    def test_pop_enum_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop fails in struct mode"""
        with raises(ConfigTypeError):
            cfg_typed.pop(key)

    @mark.parametrize("struct_mode", [False, None])
    def test_pop_with_default_enum_typed(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) has same result with python dict as with DictConfig."""
        if isinstance(key_coerced, cfg_key_type):
            assert python_dict.pop(key_coerced, "DEFAULT") == cfg_typed.pop(
                key, "DEFAULT"
            )
            assert python_dict.keys() == cfg_typed.keys()
        else:
            with raises(KeyValidationError):
                cfg_typed.pop(key, "DEFAULT")

    @mark.parametrize("struct_mode", [True])
    def test_pop_with_default_enum_typed_struct_mode(
        self,
        python_dict: Any,
        cfg_typed: DictConfig,
        key: Any,
        key_coerced: Any,
        cfg_key_type: Any,
    ) -> None:
        """Ensure that pop(..., DEFAULT) errors in struct mode"""
        with raises(ConfigTypeError):
            cfg_typed.pop(key)

    def test_keys_enum_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert python_dict.keys() == cfg_typed.keys()

    def test_values_enum_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert list(python_dict.values()) == list(cfg_typed.values())

    def test_items_enum_typed(self, python_dict: Any, cfg_typed: Any) -> None:
        assert list(python_dict.items()) == list(cfg_typed.items())
