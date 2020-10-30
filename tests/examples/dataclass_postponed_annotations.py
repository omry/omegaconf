# `from __future__` has to be the very first thing in a module
# otherwise a syntax error is raised
from __future__ import annotations  # type: ignore # noqa  # Python 3.6 linters complain

from dataclasses import dataclass, fields
from enum import Enum

import pytest

from omegaconf import OmegaConf, ValidationError


class Height(Enum):
    SHORT = 0
    TALL = 1


@dataclass
class SimpleTypes:
    num: int = 10
    pi: float = 3.1415
    is_awesome: bool = True
    height: "Height" = Height.SHORT  # test forward ref
    description: str = "text"


def simple_types_class() -> None:
    # confirm that the type annotations are in fact stored as strings
    # i.e., that the `from future` import worked
    num_field = fields(SimpleTypes)[0]
    assert isinstance(num_field.type, str)
    assert num_field.type == "int"

    conf = OmegaConf.structured(SimpleTypes)
    assert conf.num == 10
    assert conf.pi == 3.1415
    assert conf.is_awesome is True
    assert conf.height == Height.SHORT
    assert conf.description == "text"


def conversions() -> None:
    conf: SimpleTypes = OmegaConf.structured(SimpleTypes)
    conf.num = 20

    conf.num = "20"  # type: ignore
    assert conf.num == 20

    with pytest.raises(ValidationError):
        # ValidationError: "one" cannot be converted to an integer
        conf.num = "one"  # type: ignore
