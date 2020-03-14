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
            assert cfg2.plugin == module.ConcretePlugin
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
        linked_list = module.LinkedList
        cfg1 = OmegaConf.create(linked_list)
        assert OmegaConf.get_type(cfg1) == linked_list

        cfg2 = OmegaConf.create(module.MissingTest.Missing1)
        assert OmegaConf.is_missing(cfg2, "head")
        assert OmegaConf.get_type(cfg2, "head") == module.LinkedList

    class TestMissing:
        def test_missing1(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.MissingTest.Missing1)
            assert OmegaConf.is_missing(cfg, "head")

            assert OmegaConf.get_type(cfg, "head") == module.LinkedList

            with pytest.raises(ValidationError):
                cfg.head = 10

        def test_missing2(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg = OmegaConf.create(module.MissingTest.Missing2)
            assert cfg == {"head": {"next": "???", "value": 1}}
            assert OmegaConf.is_missing(cfg.head, "next")

            cfg.head.next = module.LinkedList(value=2)
            assert cfg == {"head": {"next": {"next": None, "value": 2}, "value": 1}}
