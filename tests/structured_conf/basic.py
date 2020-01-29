from importlib import import_module
from typing import Any

import pytest

from omegaconf import OmegaConf, ValidationError


@pytest.mark.parametrize(
    "class_type",
    [
        "tests.structured_conf.data.dataclass_test_data",
        "tests.structured_conf.data.attr_test_data",
    ],
)
class TestBasic:
    def test_error_on_non_structured_config_class(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        with pytest.raises(ValidationError, match="structured config"):
            OmegaConf.structured(module.NotStructuredConfig)

    def test_error_on_non_structured_nested_config_class(self, class_type: str) -> None:
        module: Any = import_module(class_type)
        with pytest.raises(ValidationError, match="structured config"):
            OmegaConf.structured(module.StructuredWithInvalidField)
