from importlib import import_module
from typing import Any

import pytest

from omegaconf import OmegaConf, ValidationError


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
            with pytest.raises(ValidationError, match="structured config"):
                OmegaConf.structured(module.StructuredWithInvalidField)

        def test_assignment_of_subclass(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create({"plugin": module.Plugin})
            cfg.plugin = OmegaConf.structured(module.ConcretePlugin)
            assert cfg.plugin._type == module.ConcretePlugin
            assert cfg.plugin.params._type == module.ConcretePlugin.FoobarParams

        def test_assignment_of_non_subclass_1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create({"plugin": module.Plugin})
            with pytest.raises(ValidationError):
                cfg.plugin = OmegaConf.structured(module.FaultyPlugin)

        def test_merge(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.ConcretePlugin})
            # TODO: fix __eq__ to support comparing to Structured Configs directly
            assert cfg2.plugin == OmegaConf.create(module.ConcretePlugin)
            res = OmegaConf.merge(cfg1, cfg2)
            assert res.plugin._type == module.ConcretePlugin
            assert res.plugin.params._type == module.ConcretePlugin.FoobarParams

        def test_merge_of_non_subclass_1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.create({"plugin": module.Plugin})
            cfg2 = OmegaConf.create({"plugin": module.FaultyPlugin})
            with pytest.raises(ValidationError):
                OmegaConf.merge(cfg1, cfg2)

        @pytest.mark.parametrize("rhs", [1, "foo", None])
        class TestFailedCases:
            def test_assignment_of_non_subclass_2(
                self, class_type: str, rhs: Any
            ) -> None:
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
