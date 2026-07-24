import re
import sys
from importlib import import_module
from typing import Any, Optional

from pytest import fixture, mark, param, raises

from omegaconf import (
    DictConfig,
    IntegerNode,
    Node,
    OmegaConf,
    ValidationError,
    _utils,
    flag_override,
)
from omegaconf._utils import _is_optional, get_type_hint
from omegaconf.errors import ConfigKeyError, ConfigValueError, UnsupportedValueType
from tests import IllegalType


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


class TestStructured:
    class TestBasic:
        def test_error_on_non_structured_config_class(self, module: Any) -> None:
            with raises(ValidationError, match="structured config"):
                OmegaConf.structured(module.NotStructuredConfig)

        def test_error_on_non_structured_nested_config_class(self, module: Any) -> None:
            with raises(
                ValidationError,
                match=re.escape("Unexpected type annotation: NotStructuredConfig"),
            ):
                OmegaConf.structured(module.StructuredWithInvalidField)

            ret = OmegaConf.structured(
                module.StructuredWithInvalidField, flags={"allow_objects": True}
            )
            assert list(ret.keys()) == ["bar"]
            assert ret.bar == module.NotStructuredConfig()

        def test_error_on_creation_with_bad_value_type(self, module: Any) -> None:
            with raises(
                ValidationError,
                match=re.escape(
                    "Value 'seven' of type 'str' could not be converted to Integer"
                ),
            ):
                OmegaConf.structured(module.User(age="seven"))

        def test_nested_creation_error_has_full_key(self, module: Any) -> None:
            with raises(ValidationError) as exc_info:
                OmegaConf.structured(module.StructuredWithInvalidNestedValue)

            assert exc_info.value.full_key == "inner.value"

        def test_assignment_of_subclass(self, module: Any) -> None:
            cfg = OmegaConf.create({"plugin": module.Plugin})
            cfg.plugin = OmegaConf.structured(module.ConcretePlugin)
            assert OmegaConf.get_type(cfg.plugin) == module.ConcretePlugin
            assert (
                OmegaConf.get_type(cfg.plugin.params)
                == module.ConcretePlugin.FoobarParams
            )

        def test_assignment_of_non_subclass_1(self, module: Any) -> None:
            cfg = OmegaConf.create(
                {"plugin": DictConfig(module.Plugin, ref_type=module.Plugin)}
            )
            with raises(ValidationError):
                cfg.plugin = OmegaConf.structured(module.FaultyPlugin)

        def test_merge(self, module: Any) -> None:
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.ConcretePlugin})
            assert cfg2.plugin == module.ConcretePlugin
            res: Any = OmegaConf.merge(cfg1, cfg2)
            assert OmegaConf.get_type(res.plugin) == module.ConcretePlugin
            assert (
                OmegaConf.get_type(res.plugin.params)
                == module.ConcretePlugin.FoobarParams
            )

        def test_merge_of_non_subclass_1(self, module: Any) -> None:
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.FaultyPlugin})
            with raises(ValidationError):
                OmegaConf.merge(cfg1, cfg2)

        def test_merge_error_new_attribute(self, module: Any) -> None:
            cfg = OmegaConf.structured(module.ConcretePlugin)
            cfg2 = OmegaConf.create({"params": {"bar": 10}})
            # raise if an invalid key is merged into a struct
            with raises(ConfigKeyError):
                OmegaConf.merge(cfg, cfg2)

        def test_merge_error_override_bad_type(self, module: Any) -> None:
            cfg = OmegaConf.structured(module.ConcretePlugin)

            # raise if an invalid key is merged into a struct
            with raises(ValidationError):
                OmegaConf.merge(cfg, {"params": {"foo": "zonk"}})

        def test_error_message(self, module: Any) -> None:
            cfg = OmegaConf.structured(module.StructuredOptional)
            msg = re.escape("field 'not_optional' is not Optional")
            with raises(ValidationError, match=msg):
                cfg.not_optional = None

    def test_none_assignment(self, module: Any) -> None:
        cfg = OmegaConf.create({"plugin": module.Plugin})
        # can assign None to params (type Any):
        cfg.plugin.params = None
        assert cfg.plugin.params is None

        cfg2 = OmegaConf.create({"plugin": module.ConcretePlugin})
        with raises(ValidationError):
            cfg2.plugin.params = None

    @mark.parametrize("rhs", [1, "foo"])
    class TestFailedAssignmentOrMerges:
        def test_assignment_of_non_subclass_2(self, module: Any, rhs: Any) -> None:
            cfg = OmegaConf.create(
                {"plugin": DictConfig(module.Plugin, ref_type=module.Plugin)}
            )
            with raises(ValidationError):
                cfg.plugin = rhs

        def test_merge_of_non_subclass_2(self, module: Any, rhs: Any) -> None:
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": rhs})
            with raises(ValidationError):
                OmegaConf.merge(cfg1, cfg2)

    def test_get_type(self, module: Any) -> None:
        cfg1 = OmegaConf.create(module.LinkedList)
        assert OmegaConf.get_type(cfg1) == module.LinkedList
        assert _utils.get_type_hint(cfg1, "next") == Optional[module.LinkedList]
        assert OmegaConf.get_type(cfg1, "next") is type(None)

        assert cfg1.next is None
        assert OmegaConf.is_missing(cfg1, "value")

        cfg2 = OmegaConf.create(module.MissingTest.Missing1)
        assert OmegaConf.is_missing(cfg2, "head")
        assert _utils.get_type_hint(cfg2, "head") == module.LinkedList
        assert OmegaConf.get_type(cfg2, "head") is None

    def test_merge_structured_into_dict(self, module: Any) -> None:
        c1 = OmegaConf.create({"name": 7})
        c2 = OmegaConf.merge(c1, module.User)
        assert c1 == {"name": 7}
        # type of name becomes str
        assert c2 == {"name": "7", "age": "???"}

    def test_merge_structured_into_dict_nested(self, module: Any) -> None:
        c1 = OmegaConf.create({"user": {"name": 7}})
        c2 = OmegaConf.merge(c1, module.MissingUserField)
        assert c1 == {"user": {"name": 7}}
        # type of name becomes str
        assert c2 == {"user": {"name": "7", "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_type_hint(c2, "user") == module.User

    def test_merge_structured_into_dict_nested2(self, module: Any) -> None:
        c1 = OmegaConf.create({"user": {"name": IntegerNode(value=7)}})
        c2 = OmegaConf.merge(c1, module.MissingUserField)
        assert c1 == {"user": {"name": 7}}
        # type of name remains int
        assert c2 == {"user": {"name": 7, "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_type_hint(c2, "user") == module.User

    def test_merge_structured_into_dict_nested3(self, module: Any) -> None:
        c1 = OmegaConf.create({"user": {"name": "alice"}})
        c2 = OmegaConf.merge(c1, module.MissingUserWithDefaultNameField)
        assert c1 == {"user": {"name": "alice"}}
        # name is not changed
        assert c2 == {"user": {"name": "alice", "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_type_hint(c2, "user") == module.UserWithDefaultName

    def test_merge_missing_object_onto_typed_dictconfig(self, module: Any) -> None:
        c1 = OmegaConf.structured(module.DictOfObjects)
        c2 = OmegaConf.merge(c1, {"users": {"bob": "???"}})
        assert isinstance(c2, DictConfig)
        assert OmegaConf.is_missing(c2.users, "bob")

    def test_merge_into_missing_sc(self, module: Any) -> None:
        c1 = OmegaConf.structured(module.PluginHolder)
        c2 = OmegaConf.merge(c1, {"plugin": "???"})
        assert c2.plugin == module.Plugin()

    def test_merge_missing_key_onto_structured_none(self, module: Any) -> None:
        c1 = OmegaConf.create({"foo": OmegaConf.structured(module.OptionalUser)})
        src = OmegaConf.create({"foo": {"user": "???"}})
        c2 = OmegaConf.merge(c1, src)
        assert c1.foo.user is None
        assert c2.foo.user is None
        assert c2.foo._get_node("user")._metadata.ref_type == module.User

    def test_merge_optional_structured_into_dict(self, module: Any) -> None:
        c1 = OmegaConf.create({"user": {"name": "bob"}})
        c2 = OmegaConf.merge(c1, module.OptionalUser(module.User(name="alice")))
        assert c2.user.name == "alice"
        assert get_type_hint(c2, "user") == Optional[module.User]
        assert isinstance(c2, DictConfig)
        c2_user = c2._get_node("user")
        assert isinstance(c2_user, Node)
        # Compared to the previous assert, here we verify that the `ref_type` found
        # in the metadata is *not* optional: instead, the `optional` flag must be set.
        assert c2_user._metadata.ref_type == module.User
        assert c2_user._metadata.optional

    def test_merge_structured_interpolation_onto_dict(self, module: Any) -> None:
        c1 = OmegaConf.create(
            {
                "user_1": {"name": "bob"},
                "user_2": {"name": "alice"},
                "user_3": {"name": "joe"},
            }
        )
        src = OmegaConf.create({"user_2": module.User(), "user_3": module.User()})
        src.user_2 = "${user_1}"
        src.user_3 = None
        c2 = OmegaConf.merge(c1, src)
        assert c2.user_2.name == "bob"
        assert get_type_hint(c2, "user_2") == Any
        assert c2.user_3 is None
        assert get_type_hint(c2, "user_3") == Any

    @mark.parametrize("resolve", [True, False])
    def test_interpolation_to_structured(self, module: Any, resolve: bool) -> None:
        cfg = OmegaConf.create(module.InterpolationToUser)
        if resolve:
            OmegaConf.resolve(cfg)
        assert OmegaConf.get_type(cfg.admin) is module.User
        assert cfg.admin == {"name": "Bond", "age": 7}
        assert OmegaConf.get_type(cfg.admin_list[0]) is module.User
        assert cfg.admin_list == [{"name": "Bond", "age": 7}]
        assert OmegaConf.get_type(cfg.admin_dict["bond"]) is module.User
        assert cfg.admin_dict == {"bond": {"name": "Bond", "age": 7}}

    class TestMissing:
        def test_missing1(self, module: Any) -> None:
            cfg = OmegaConf.create(module.MissingTest.Missing1)
            assert OmegaConf.is_missing(cfg, "head")

            assert OmegaConf.get_type(cfg, "head") is None

            with raises(ValidationError):
                cfg.head = 10

        def test_missing2(self, module: Any) -> None:
            cfg = OmegaConf.create(module.MissingTest.Missing2)
            assert cfg == {"head": {"next": "???", "value": 1}}
            assert OmegaConf.is_missing(cfg.head, "next")

            cfg.head.next = module.LinkedList(value=2)
            assert cfg == {"head": {"next": {"next": None, "value": 2}, "value": 1}}

        def test_plugin_holder(self, module: Any) -> None:
            cfg = OmegaConf.create(module.PluginHolder)

            assert _is_optional(cfg, "none")
            assert _utils.get_type_hint(cfg, "none") == Optional[module.Plugin]
            assert OmegaConf.get_type(cfg, "none") is type(None)

            assert not _is_optional(cfg, "missing")
            assert _utils.get_type_hint(cfg, "missing") == module.Plugin
            assert OmegaConf.get_type(cfg, "missing") is None

            assert not _is_optional(cfg, "plugin")
            assert _utils.get_type_hint(cfg, "plugin") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin") == module.Plugin

            cfg.plugin = module.ConcretePlugin()
            assert not _is_optional(cfg, "plugin")
            assert _utils.get_type_hint(cfg, "plugin") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin") == module.ConcretePlugin

            assert not _is_optional(cfg, "plugin2")
            assert _utils.get_type_hint(cfg, "plugin2") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin2") == module.ConcretePlugin

        def test_plugin_merge(self, module: Any) -> None:
            plugin = OmegaConf.structured(module.Plugin)
            concrete = OmegaConf.structured(module.ConcretePlugin)
            ret = OmegaConf.merge(plugin, concrete)
            assert ret == concrete
            assert OmegaConf.get_type(ret) == module.ConcretePlugin

        def test_plugin_merge_2(self, module: Any) -> None:
            plugin = OmegaConf.structured(module.Plugin)
            more_fields = OmegaConf.structured(module.PluginWithAdditionalField)
            ret = OmegaConf.merge(plugin, more_fields)
            assert ret == more_fields
            assert OmegaConf.get_type(ret) == module.PluginWithAdditionalField

        def test_native_missing(self, module: Any) -> None:
            cfg = OmegaConf.create(module.WithNativeMISSING)
            assert OmegaConf.is_missing(cfg, "num")

        def test_allow_objects(self, module: Any) -> None:
            cfg = OmegaConf.structured(module.Plugin)
            iv = IllegalType()
            with raises(UnsupportedValueType):
                cfg.params = iv
            cfg = OmegaConf.structured(module.Plugin, flags={"allow_objects": True})
            cfg.params = iv
            assert cfg.params == iv

            cfg = OmegaConf.structured(module.Plugin)
            with flag_override(cfg, "allow_objects", True):
                cfg.params = iv
                assert cfg.params == iv

            cfg = OmegaConf.structured({"plugin": module.Plugin})
            pwo = module.Plugin(name="foo", params=iv)
            with raises(UnsupportedValueType):
                cfg.plugin = pwo

            with flag_override(cfg, "allow_objects", True):
                cfg.plugin = pwo
                assert cfg.plugin == pwo


@mark.skipif(
    sys.version_info < (3, 12),
    reason="PEP 695 type alias syntax requires Python 3.12+",
)
class TestTypeAliases:
    def test_type_alias(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        # TypeAliasType is the runtime equivalent of `type MyInt = int` (PEP 695).
        # Using the constructor avoids a SyntaxError on Python < 3.12.
        # TODO: once Python 3.11 support is dropped, replace with `type MyInt = int`
        MyInt = TypeAliasType("MyInt", int)

        @dataclass
        class C:
            x: MyInt = 0

        cfg = OmegaConf.structured(C)
        assert cfg.x == 0

    def test_parameterized_type_alias(self) -> None:
        from dataclasses import dataclass
        from typing import List, TypeAliasType, TypeVar  # type: ignore[attr-defined]

        T = TypeVar("T")
        Vec = TypeAliasType("Vec", list[T], type_params=(T,))

        @dataclass
        class C:
            values: Vec[int]

        cfg = OmegaConf.structured(C)
        cfg["values"] = [1, 2]
        assert cfg["values"] == [1, 2]
        assert _utils.get_type_hint(cfg, "values") == List[int]

        with raises(ValidationError):
            cfg["values"] = ["invalid"]

    def test_parameterized_type_alias_substitution_order(self) -> None:
        from dataclasses import dataclass
        from typing import Tuple, TypeAliasType, TypeVar  # type: ignore[attr-defined]

        T = TypeVar("T")
        U = TypeVar("U")
        Pair = TypeAliasType("Pair", tuple[U, T], type_params=(T, U))

        @dataclass
        class C:
            value: Pair[str, int]

        cfg = OmegaConf.structured(C)
        cfg.value = (10, "text")
        assert cfg.value == (10, "text")
        assert _utils.get_type_hint(cfg, "value") == Tuple[int, str]

    def test_variadic_type_alias(self) -> None:
        import typing
        from dataclasses import dataclass
        from typing import Tuple, TypeVar

        TypeAliasType = typing.TypeAliasType  # type: ignore[attr-defined]
        TypeVarTuple = typing.TypeVarTuple  # type: ignore[attr-defined]
        Unpack = typing.Unpack  # type: ignore[attr-defined]
        T = TypeVar("T")
        Ts = TypeVarTuple("Ts")
        TupleOf = TypeAliasType("TupleOf", tuple[Unpack[Ts]], type_params=(Ts,))
        Reordered = TypeAliasType(
            "Reordered", tuple[T, Unpack[Ts]], type_params=(Ts, T)
        )

        @dataclass
        class C:
            values: TupleOf[int, str]
            reordered: Reordered[int, str, bool]

        cfg = OmegaConf.structured(C)
        cfg.values = (10, "text")
        cfg.reordered = (True, 10, "text")

        assert _utils.get_type_hint(cfg, "values") == Tuple[int, str]
        assert _utils.get_type_hint(cfg, "reordered") == Tuple[bool, int, str]

    @mark.skipif(
        sys.version_info < (3, 13), reason="type parameter defaults require 3.13+"
    )
    def test_parameterized_type_alias_default(self) -> None:
        import typing
        from dataclasses import dataclass
        from typing import List, Tuple, TypeVar

        TypeAliasType = typing.TypeAliasType  # type: ignore[attr-defined]
        TypeVarTuple = typing.TypeVarTuple  # type: ignore[attr-defined]
        Unpack = typing.Unpack  # type: ignore[attr-defined]
        T = TypeVar("T")
        U = TypeVar("U", default=list[T])
        Pair = TypeAliasType("Pair", tuple[T, U], type_params=(T, U))
        DefaultT = TypeVar("DefaultT", default=str)
        DefaultU = TypeVar("DefaultU", default=list[DefaultT])
        DefaultPair = TypeAliasType(
            "DefaultPair",
            tuple[DefaultT, DefaultU],
            type_params=(DefaultT, DefaultU),
        )
        DefaultTs = TypeVarTuple("DefaultTs", default=Unpack[tuple[int, str]])
        DefaultTuple = TypeAliasType(
            "DefaultTuple",
            tuple[Unpack[DefaultTs]],
            type_params=(DefaultTs,),
        )

        @dataclass
        class C:
            value: Pair[int]
            defaulted: DefaultPair
            variadic_default: DefaultTuple

        cfg = OmegaConf.structured(C)
        cfg.value = (10, [20])
        cfg.defaulted = ("text", ["item"])
        cfg.variadic_default = (30, "text")
        assert cfg.value == (10, [20])
        assert cfg.defaulted == ("text", ["item"])
        assert cfg.variadic_default == (30, "text")
        assert _utils.get_type_hint(cfg, "value") == Tuple[int, List[int]]
        assert _utils.get_type_hint(cfg, "defaulted") == Tuple[str, List[str]]
        assert _utils.get_type_hint(cfg, "variadic_default") == Tuple[int, str]

    def test_recursive_type_alias_is_rejected(self) -> None:
        from dataclasses import dataclass, field

        namespace: dict[str, Any] = {}
        exec(
            "type Recursive = dict[str, Recursive] | list[Recursive] | str",
            namespace,
        )
        Recursive = namespace["Recursive"]

        @dataclass
        class C:
            value: Recursive = field(default_factory=dict)

        with raises(
            ValidationError,
            match="Recursive type alias 'Recursive' is not supported",
        ):
            OmegaConf.structured(C)

    def test_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        MyInt = TypeAliasType("MyInt", int)
        MyList = TypeAliasType("MyList", list[int])
        assert _utils.is_supported_union_annotation(MyInt | MyList | str)

        @dataclass
        class C:
            value: MyInt | MyList | str = 0

        cfg = OmegaConf.structured(C)
        assert cfg.value == 0

        cfg.value = [1, 2]
        assert cfg.value == [1, 2]

        cfg.value = "text"
        assert cfg.value == "text"

    def test_type_alias_as_dict_key(self) -> None:
        from dataclasses import dataclass, field
        from typing import Any, TypeAliasType  # type: ignore[attr-defined]

        Key = TypeAliasType("Key", str)
        AnyKey = TypeAliasType("AnyKey", Any | int)

        @dataclass
        class C:
            values: dict[Key, int] = field(default_factory=dict)
            direct_any: dict[Any | int, str] = field(default_factory=dict)
            aliased_any: dict[AnyKey, str] = field(default_factory=dict)

        cfg = OmegaConf.structured(C)
        cfg["values"]["key"] = 10
        cfg.direct_any[10] = "direct"
        cfg.aliased_any["key"] = "aliased"

        assert cfg["values"] == {"key": 10}
        assert cfg["values"]._metadata.key_type is str
        assert cfg.direct_any == {10: "direct"}
        assert cfg.direct_any._metadata.key_type is Any
        assert cfg.aliased_any == {"key": "aliased"}
        assert cfg.aliased_any._metadata.key_type is Any

    def test_type_aliases_nested_in_containers(self) -> None:
        import typing
        from dataclasses import dataclass, field
        from typing import Any, Dict, List, Optional, Tuple, Union

        TypeAliasType = typing.TypeAliasType  # type: ignore[attr-defined]
        MyInt = TypeAliasType("MyInt", int)
        MaybeInt = TypeAliasType("MaybeInt", MyInt | None)
        AnyOrInt = TypeAliasType("AnyOrInt", Any | MyInt)

        @dataclass
        class C:
            values: list[MyInt | str] = field(default_factory=list)
            items: tuple[MaybeInt, ...] = ()
            mapping: dict[str, AnyOrInt] = field(default_factory=dict)
            nested: dict[str, list[MyInt | str]] = field(default_factory=dict)
            container_union: list[MyInt] | tuple[MyInt, ...] = field(
                default_factory=list
            )

        cfg = OmegaConf.structured(C)

        assert _utils.get_type_hint(cfg, "values") == List[Union[int, str]]
        assert _utils.get_type_hint(cfg, "items") == Tuple[Optional[int], ...]
        assert _utils.get_type_hint(cfg, "mapping") == Dict[str, Any]
        assert _utils.get_type_hint(cfg, "nested") == Dict[str, List[Union[int, str]]]
        assert (
            _utils.get_type_hint(cfg, "container_union")
            == Union[list[int], tuple[int, ...]]
        )

        cfg.values = [10, "text"]
        cfg.items = (None, 20)
        cfg.mapping = {"key": "text"}
        cfg.nested = {"key": [30, "text"]}
        cfg.container_union = (40,)

        merged = OmegaConf.merge(
            cfg,
            {
                "values": ["merged"],
                "items": [40],
                "mapping": {"other": 1.5},
                "nested": {"other": [50]},
                "container_union": [60],
            },
        )
        assert merged == {
            "values": ["merged"],
            "items": (40,),
            "mapping": {"key": "text", "other": 1.5},
            "nested": {"key": [30, "text"], "other": [50]},
            "container_union": [60],
        }

    def test_parameterized_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType, TypeVar  # type: ignore[attr-defined]

        T = TypeVar("T")
        Vec = TypeAliasType("Vec", list[T], type_params=(T,))

        @dataclass
        class C:
            value: Vec[int] | str = "default"

        cfg = OmegaConf.structured(C)
        cfg.value = [1, 2]
        assert cfg.value == [1, 2]

        with raises(ValidationError):
            cfg.value = ["invalid"]

    def test_nested_parameterized_type_alias(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType, TypeVar  # type: ignore[attr-defined]

        T = TypeVar("T")
        Vec = TypeAliasType("Vec", list[T], type_params=(T,))
        MaybeVec = TypeAliasType("MaybeVec", Vec[T] | None, type_params=(T,))

        @dataclass
        class C:
            value: MaybeVec[int] = None

        cfg = OmegaConf.structured(C)
        assert cfg.value is None

        cfg.value = [1, 2]
        assert cfg.value == [1, 2]

    def test_unsupported_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        class Unsupported:
            pass

        UnsupportedAlias = TypeAliasType("UnsupportedAlias", Unsupported)

        @dataclass
        class C:
            value: UnsupportedAlias | int = 0

        with raises(ConfigValueError, match="Unsupported type annotation in Union"):
            OmegaConf.structured(C)

    def test_structured_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        @dataclass
        class Plugin:
            name: str

        PluginAlias = TypeAliasType("PluginAlias", Plugin)

        @dataclass
        class C:
            value: PluginAlias | int = 0

        cfg = OmegaConf.structured(C)
        cfg.value = Plugin(name="demo")

        assert OmegaConf.get_type(cfg.value) is Plugin
        assert cfg.value == {"name": "demo"}

    def test_union_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        IntOrStr = TypeAliasType("IntOrStr", int | str)

        @dataclass
        class C:
            value: IntOrStr | float = 0

        cfg = OmegaConf.structured(C)
        cfg.value = "text"
        assert cfg.value == "text"

        cfg.value = 1.5
        assert cfg.value == 1.5

    def test_none_type_aliases_as_union_members(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        Nothing = TypeAliasType("Nothing", None)
        AlsoNothing = TypeAliasType("AlsoNothing", None)

        @dataclass
        class C:
            value: Nothing | AlsoNothing = None

        cfg = OmegaConf.structured(C)
        assert cfg.value is None

    def test_optional_type_alias_as_union_member(self) -> None:
        from dataclasses import dataclass
        from typing import TypeAliasType  # type: ignore[attr-defined]

        MaybeInt = TypeAliasType("MaybeInt", int | None)

        @dataclass
        class C:
            value: MaybeInt | str = None

        cfg = OmegaConf.structured(C)
        assert cfg.value is None

        cfg.value = 10
        assert cfg.value == 10

        cfg.value = "text"
        assert cfg.value == "text"

    def test_attrs_type_alias_as_union_member(self) -> None:
        from typing import TypeAliasType  # type: ignore[attr-defined]

        import attr

        MyInt = TypeAliasType("MyInt", int)

        @attr.s(auto_attribs=True)
        class C:
            value: MyInt | str = 0

        cfg = OmegaConf.structured(C)
        cfg.value = "text"
        assert cfg.value == "text"
