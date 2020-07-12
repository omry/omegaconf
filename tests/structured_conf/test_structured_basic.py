import re
from importlib import import_module
from typing import Any, Optional

import pytest

from omegaconf import OmegaConf, ValidationError, _utils
from omegaconf.errors import ConfigKeyError


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
            cfg = OmegaConf.create({"plugin": module.Plugin})
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
            cfg = OmegaConf.create({"plugin": module.Plugin})
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

            more_fields = OmegaConf.structured(module.PluginWithAdditionalField)
            ret = OmegaConf.merge(plugin, more_fields)
            assert ret == more_fields
            assert OmegaConf.get_type(ret) == module.PluginWithAdditionalField

        def test_native_missing(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            with pytest.raises(
                ValueError,
                match=re.escape(
                    "Missing default value for WithNativeMISSING.num,"
                    " to indicate default must be populated later use OmegaConf.MISSING"
                ),
            ):
                OmegaConf.create(module.WithNativeMISSING)
