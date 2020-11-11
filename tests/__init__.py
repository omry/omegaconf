from contextlib import contextmanager
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Iterator, List, Optional, Union

import attr

from omegaconf import II, MISSING


class IllegalType:
    def __init__(self) -> None:
        pass

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, IllegalType):
            return True
        return False


@contextmanager
def does_not_raise(enter_result: Any = None) -> Iterator[Any]:
    yield enter_result


class Color(Enum):
    RED = 1
    GREEN = 2
    BLUE = 3


@dataclass
class User:
    name: str = MISSING
    age: int = MISSING


@dataclass
class Group:
    admin: Optional[User] = None


class Enum1(Enum):
    FOO = 1
    BAR = 2


@dataclass
class Users:
    name2user: Dict[str, User] = field(default_factory=dict)


@dataclass
class ConfWithMissingDict:
    dict: Dict[str, Any] = MISSING


@dataclass
class Plugin:
    name: str = MISSING
    params: Any = MISSING


@dataclass
class ConcretePlugin(Plugin):
    name: str = "foobar_plugin"

    @dataclass
    class FoobarParams:
        foo: int = 10

    params: FoobarParams = FoobarParams()


@dataclass
class StructuredWithMissing:
    num: int = MISSING
    opt_num: Optional[int] = MISSING
    dict: Dict[str, str] = MISSING
    opt_dict: Optional[Dict[str, str]] = MISSING
    list: List[str] = MISSING
    opt_list: Optional[List[str]] = MISSING
    user: User = MISSING
    opt_user: Optional[User] = MISSING
    inter_num: int = II("num")
    inter_user: User = II("user")
    inter_opt_user: Optional[User] = II("opt_user")


@dataclass
class UnionError:
    x: Union[int, str] = 10


@dataclass
class MissingList:
    list: List[str] = MISSING


@dataclass
class MissingDict:
    dict: Dict[str, str] = MISSING


@dataclass
class DictEnum:
    color_key: Dict[Color, str] = field(default_factory=lambda: {})
    color_val: Dict[str, Color] = field(default_factory=lambda: {})


@dataclass
class A:
    a: int = 10


@dataclass
class B:
    x: A = MISSING


@dataclass
class C:
    x: Optional[A] = None


@dataclass
class PersonD:
    age: int = 18
    registered: bool = True


@attr.s(auto_attribs=True)
class PersonA:
    age: int = 18
    registered: bool = True


@dataclass
class Module:
    name: str = MISSING
    classes: List[str] = MISSING


@dataclass
class Package:
    modules: List[Module] = MISSING


@dataclass
class InterpolationList:
    list: List[float] = II("optimization.lr")


@dataclass
class InterpolationDict:
    dict: Dict[str, int] = II("optimization.lr")
