from dataclasses import dataclass, field
from typing import List, Any
from omegaconf import OmegaConf


@dataclass
class Example:
    num: int


@dataclass
class TestConfig(Example):
    common: Example = field(default_factory=Example)


for k, field_info in TestConfig.__dataclass_fields__.items():
    default_value = field_info.default
    default_factory = field_info.default_factory
    print(
        f"Field: {k}, Default Value: {default_value}, Default Factory: {default_factory}"
    )

    mis = OmegaConf.structured(default_factory)
