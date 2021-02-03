import re
from importlib import import_module
from typing import Any, Optional

import pytest

from omegaconf import (
    DictConfig,
    IntegerNode,
    Node,
    OmegaConf,
    ValidationError,
    _utils,
    flag_override,
)
from omegaconf._utils import get_ref_type
from omegaconf.errors import ConfigKeyError, UnsupportedValueType
from tests import IllegalType


@pytest.mark.parametrize(
    "class_type",
    [
        "tests.structured_conf.data.dataclasses",
        "tests.structured_conf.data.attr_classes",
    ],
)
class TestStructured:
    class TestBasic:
        def test_error_on_non_structured_config_class(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            with pytest.raises(ValidationError, match="structured config"):
                OmegaConf.structured(module.NotStructuredConfig)

        def test_error_on_non_structured_nested_config_class(
            self, class_type: str
        ) -> None:
            module: Any = import_module(class_type)
            with pytest.raises(
                ValidationError,
                match=re.escape("Unexpected object type : NotStructuredConfig"),
            ):
                OmegaConf.structured(module.StructuredWithInvalidField)

            ret = OmegaConf.structured(
                module.StructuredWithInvalidField, flags={"allow_objects": True}
            )
            assert list(ret.keys()) == ["bar"]
            assert ret.bar == module.NotStructuredConfig()

        def test_assignment_of_subclass(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create({"plugin": module.Plugin})
            cfg.plugin = OmegaConf.structured(module.ConcretePlugin)
            assert OmegaConf.get_type(cfg.plugin) == module.ConcretePlugin
            assert (
                OmegaConf.get_type(cfg.plugin.params)
                == module.ConcretePlugin.FoobarParams
            )

        def test_assignment_of_non_subclass_1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(
                {"plugin": DictConfig(module.Plugin, ref_type=module.Plugin)}
            )
            with pytest.raises(ValidationError):
                cfg.plugin = OmegaConf.structured(module.FaultyPlugin)

        def test_merge(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.ConcretePlugin})
            assert cfg2.plugin == module.ConcretePlugin
            res: Any = OmegaConf.merge(cfg1, cfg2)
            assert OmegaConf.get_type(res.plugin) == module.ConcretePlugin
            assert (
                OmegaConf.get_type(res.plugin.params)
                == module.ConcretePlugin.FoobarParams
            )

        def test_merge_of_non_subclass_1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.FaultyPlugin})
            with pytest.raises(ValidationError):
                OmegaConf.merge(cfg1, cfg2)

        def test_merge_error_new_attribute(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.structured(module.ConcretePlugin)
            cfg2 = OmegaConf.create({"params": {"bar": 10}})
            # raise if an invalid key is merged into a struct
            with pytest.raises(ConfigKeyError):
                OmegaConf.merge(cfg, cfg2)

        def test_merge_error_override_bad_type(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.structured(module.ConcretePlugin)

            # raise if an invalid key is merged into a struct
            with pytest.raises(ValidationError):
                OmegaConf.merge(cfg, {"params": {"foo": "zonk"}})

        def test_error_message(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.structured(module.StructuredOptional)
            msg = re.escape("child 'not_optional' is not Optional")
            with pytest.raises(ValidationError, match=msg):
                cfg.not_optional = None

    def test_none_assignment(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        cfg = OmegaConf.create({"plugin": module.Plugin})
        # can assign None to params (type Any):
        cfg.plugin.params = None
        assert cfg.plugin.params is None

        cfg2 = OmegaConf.create({"plugin": module.ConcretePlugin})
        with pytest.raises(ValidationError):
            cfg2.plugin.params = None

    @pytest.mark.parametrize("rhs", [1, "foo"])
    class TestFailedAssignmentOrMerges:
        def test_assignment_of_non_subclass_2(self, class_type: str, rhs: Any) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(
                {"plugin": DictConfig(module.Plugin, ref_type=module.Plugin)}
            )
            with pytest.raises(ValidationError):
                cfg.plugin = rhs

        def test_merge_of_non_subclass_2(self, class_type: str, rhs: Any) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": rhs})
            with pytest.raises(ValidationError):
                OmegaConf.merge(cfg1, cfg2)

    def test_get_type(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        cfg1 = OmegaConf.create(module.LinkedList)
        assert OmegaConf.get_type(cfg1) == module.LinkedList
        assert _utils.get_ref_type(cfg1, "next") == Optional[module.LinkedList]
        assert OmegaConf.get_type(cfg1, "next") is None

        assert cfg1.next is None
        assert OmegaConf.is_missing(cfg1, "value")

        cfg2 = OmegaConf.create(module.MissingTest.Missing1)
        assert OmegaConf.is_missing(cfg2, "head")
        assert _utils.get_ref_type(cfg2, "head") == module.LinkedList
        assert OmegaConf.get_type(cfg2, "head") is None

    def test_merge_structured_onto_dict(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"name": 7})
        c2 = OmegaConf.merge(c1, module.User)
        assert c1 == {"name": 7}
        # type of name becomes str
        assert c2 == {"name": "7", "age": "???"}

    def test_merge_structured_onto_dict_nested(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"user": {"name": 7}})
        c2 = OmegaConf.merge(c1, module.MissingUserField)
        assert c1 == {"user": {"name": 7}}
        # type of name becomes str
        assert c2 == {"user": {"name": "7", "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_ref_type(c2, "user") == module.User

    def test_merge_structured_onto_dict_nested2(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"user": {"name": IntegerNode(value=7)}})
        c2 = OmegaConf.merge(c1, module.MissingUserField)
        assert c1 == {"user": {"name": 7}}
        # type of name remains int
        assert c2 == {"user": {"name": 7, "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_ref_type(c2, "user") == module.User

    def test_merge_structured_onto_dict_nested3(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"user": {"name": "alice"}})
        c2 = OmegaConf.merge(c1, module.MissingUserWithDefaultNameField)
        assert c1 == {"user": {"name": "alice"}}
        # name is not changed
        assert c2 == {"user": {"name": "alice", "age": "???"}}
        assert isinstance(c2, DictConfig)
        assert get_ref_type(c2, "user") == module.UserWithDefaultName

    def test_merge_missing_object_onto_typed_dictconfig(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.structured(module.DictOfObjects)
        c2 = OmegaConf.merge(c1, {"users": {"bob": "???"}})
        assert isinstance(c2, DictConfig)
        assert OmegaConf.is_missing(c2.users, "bob")

    def test_merge_into_missing_sc(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.structured(module.PluginHolder)
        c2 = OmegaConf.merge(c1, {"plugin": "???"})
        assert c2.plugin == module.Plugin()

    def test_merge_missing_key_onto_structured_none(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"foo": OmegaConf.structured(module.OptionalUser)})
        src = OmegaConf.create({"foo": {"user": "???"}})
        c2 = OmegaConf.merge(c1, src)
        assert c1.foo.user is None
        assert c2.foo.user is None
        assert c2.foo._get_node("user")._metadata.ref_type == module.User

    def test_merge_optional_structured_onto_dict(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        c1 = OmegaConf.create({"user": {"name": "bob"}})
        c2 = OmegaConf.merge(c1, module.OptionalUser(module.User(name="alice")))
        assert c2.user.name == "alice"
        assert get_ref_type(c2, "user") == Optional[module.User]
        assert isinstance(c2, DictConfig)
        c2_user = c2._get_node("user")
        assert isinstance(c2_user, Node)
        # Compared to the previous assert, here we verify that the `ref_type` found
        # in the metadata is *not* optional: instead, the `optional` flag must be set.
        assert c2_user._metadata.ref_type == module.User
        assert c2_user._metadata.optional

    def test_merge_structured_interpolation_onto_dict(self, class_type: str) -> None:
        module: Any = import_module(class_type)
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
        assert get_ref_type(c2, "user_2") == Any
        assert c2.user_3 is None
        assert get_ref_type(c2, "user_3") == Any

    class TestMissing:
        def test_missing1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.MissingTest.Missing1)
            assert OmegaConf.is_missing(cfg, "head")

            assert OmegaConf.get_type(cfg, "head") is None

            with pytest.raises(ValidationError):
                cfg.head = 10

        def test_missing2(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.MissingTest.Missing2)
            assert cfg == {"head": {"next": "???", "value": 1}}
            assert OmegaConf.is_missing(cfg.head, "next")

            cfg.head.next = module.LinkedList(value=2)
            assert cfg == {"head": {"next": {"next": None, "value": 2}, "value": 1}}

        def test_plugin_holder(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.PluginHolder)

            assert OmegaConf.is_optional(cfg, "none")
            assert _utils.get_ref_type(cfg, "none") == Optional[module.Plugin]
            assert OmegaConf.get_type(cfg, "none") is None

            assert not OmegaConf.is_optional(cfg, "missing")
            assert _utils.get_ref_type(cfg, "missing") == module.Plugin
            assert OmegaConf.get_type(cfg, "missing") is None

            assert not OmegaConf.is_optional(cfg, "plugin")
            assert _utils.get_ref_type(cfg, "plugin") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin") == module.Plugin

            cfg.plugin = module.ConcretePlugin()
            assert not OmegaConf.is_optional(cfg, "plugin")
            assert _utils.get_ref_type(cfg, "plugin") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin") == module.ConcretePlugin

            assert not OmegaConf.is_optional(cfg, "plugin2")
            assert _utils.get_ref_type(cfg, "plugin2") == module.Plugin
            assert OmegaConf.get_type(cfg, "plugin2") == module.ConcretePlugin

        def test_plugin_merge(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            plugin = OmegaConf.structured(module.Plugin)
            concrete = OmegaConf.structured(module.ConcretePlugin)
            ret = OmegaConf.merge(plugin, concrete)
            assert ret == concrete
            assert OmegaConf.get_type(ret) == module.ConcretePlugin

        def test_plugin_merge_2(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            plugin = OmegaConf.structured(module.Plugin)
            more_fields = OmegaConf.structured(module.PluginWithAdditionalField)
            ret = OmegaConf.merge(plugin, more_fields)
            assert ret == more_fields
            assert OmegaConf.get_type(ret) == module.PluginWithAdditionalField

        def test_native_missing(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.WithNativeMISSING)
            assert OmegaConf.is_missing(cfg, "num")

        def test_allow_objects(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.structured(module.Plugin)
            iv = IllegalType()
            with pytest.raises(UnsupportedValueType):
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
            with pytest.raises(UnsupportedValueType):
                cfg.plugin = pwo

            with flag_override(cfg, "allow_objects", True):
                cfg.plugin = pwo
                assert cfg.plugin == pwo
