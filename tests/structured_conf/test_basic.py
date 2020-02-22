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

    class TestReplace:
        def test_replace_any2(self, class_type: str) -> None:
            module: Any = import_module(class_type)
            cfg1 = OmegaConf.structured(module.Plugin)
            cfg2 = OmegaConf.structured(module.ConcretePlugin)
            res = OmegaConf.merge(cfg1, cfg2)
            assert res._type == module.ConcretePlugin
            assert res.params._type == module.ConcretePlugin.FoobarParams
