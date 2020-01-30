from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional

from omegaconf import MISSING


class IllegalType:
    def __init__(self) -> None:
        pass


@contextmanager
def does_not_raise(enter_result: Any = None) -> Iterator[Any]:
    yield enter_result


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@dataclass
class StructuredWithMissing:
    num: int = MISSING
    opt_num: Optional[int] = MISSING
    dict: Dict[str, str] = MISSING
    opt_dict: Optional[Dict[str, str]] = MISSING
    list: List[str] = MISSING
    opt_list: Optional[List[str]] = MISSING
