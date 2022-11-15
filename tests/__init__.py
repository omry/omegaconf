import re
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, Generic, List, NamedTuple, Optional, Tuple, TypeVar, Union

import attr
from pytest import warns

from omegaconf import II, MISSING


class IllegalType:
    def __init__(self) -> None:
        pass

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, IllegalType):
            return True
        return False


T = TypeVar("T")


class IllegalTypeGeneric(Generic[T]):
    ...


class NonCopyableIllegalType:
    def __init__(self) -> None:
        pass

    def __eq__(self, other: Any) -> bool:
        if isinstance(other, NonCopyableIllegalType):
            return True
        return False

    def __copy__(self) -> Any:
        raise NotImplementedError()

    def __deepcopy__(self, memo: Any) -> Any:
        raise NotImplementedError()


class Dataframe:
    """Emulates Pandas Dataframe equality and boolean behavior."""

    def __init__(self) -> None:
        pass

    def __eq__(self, other: Any) -> Any:
        """Mimic pandas DataFrame __eq__, which returns a pandas DataFrame object"""
        return self

    def __bool__(self) -> None:
        """Mimic pandas DataFrame __bool__, which raises a ValueError"""
        raise ValueError


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
class OptionalUsers:
    name2user: Dict[str, Optional[User]] = field(default_factory=dict)


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

    params: FoobarParams = field(default_factory=FoobarParams)


@dataclass
class NestedInterpolationToMissing:
    @dataclass
    class BazParams:
        baz: str = "${..name}"

    subcfg: BazParams = field(default_factory=BazParams)
    name: str = MISSING


@dataclass
class StructuredInterpolationKeyError:
    name: str = "${bar}"


@dataclass
class StructuredInterpolationValidationError:
    x: Optional[int] = None
    y: int = II(".x")


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
    x: Union[int, List[str]] = 10


@dataclass
class StructuredWithBadDict:
    foo: Dict[str, str] = 123  # type: ignore


@dataclass
class StructuredWithBadList:
    foo: List[str] = 123  # type: ignore


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
class UntypedList:
    list: List = field(default_factory=lambda: [1, 2])  # type: ignore
    opt_list: Optional[List] = None  # type: ignore


@dataclass
class SubscriptedList:
    list: List[int] = field(default_factory=lambda: [1, 2])


@dataclass
class SubscriptedListOpt:
    opt_list: Optional[List[int]] = field(default_factory=lambda: [1, 2])
    list_opt: List[Optional[int]] = field(default_factory=lambda: [1, 2, None])


@dataclass
class ListOfAny:
    list: List[Any]


@dataclass
class UntypedDict:
    dict: Dict = field(default_factory=lambda: {"foo": "var"})  # type: ignore
    opt_dict: Optional[Dict] = None  # type: ignore


@dataclass
class SubscriptedDict:
    dict_str: Dict[str, int] = field(default_factory=lambda: {"foo": 4})
    dict_enum: Dict[Color, int] = field(default_factory=lambda: {Color.RED: 4})
    dict_int: Dict[int, int] = field(default_factory=lambda: {123: 4})
    dict_float: Dict[float, int] = field(default_factory=lambda: {123.45: 4})
    dict_bool: Dict[bool, int] = field(default_factory=lambda: {True: 4, False: 5})
    dict_bytes: Dict[bytes, int] = field(default_factory=lambda: {b"binary": 4})


@dataclass
class SubscriptedDictOpt:
    opt_dict: Optional[Dict[str, int]] = field(default_factory=lambda: {"foo": 4})
    dict_opt: Dict[str, Optional[int]] = field(
        default_factory=lambda: {"foo": 4, "bar": None}
    )


@dataclass
class DictOfAny:
    dict: Dict[Any, Any]


@dataclass
class InterpolationList:
    list: List[float] = II("optimization.lr")


@dataclass
class InterpolationDict:
    dict: Dict[str, int] = II("optimization.lr")


@dataclass
class Str2Int(Dict[str, int]):
    pass


class DictSubclass(Dict[Any, Any]):
    pass


class ListSubclass(List[Any]):
    pass


class Shape(NamedTuple):
    channels: int
    height: int
    width: int


@dataclass
class OptTuple:
    x: Optional[Tuple[int, ...]] = None


@dataclass
class NestedContainers:
    dict_of_dict: Dict[str, Dict[str, int]] = field(
        default_factory=lambda: {"foo": {"bar": 123}}
    )
    list_of_list: List[List[int]] = field(default_factory=lambda: [[123]])
    dict_of_list: Dict[str, List[int]] = field(default_factory=lambda: {"foo": [123]})
    list_of_dict: List[Dict[str, int]] = field(default_factory=lambda: [{"bar": 123}])


@dataclass
class UnionAnnotations:
    ubf: Union[bool, float] = True
    oubf: Optional[Union[bool, float]] = None


def warns_dict_subclass_deprecated(dict_subclass: Any) -> Any:
    return warns(
        UserWarning,
        match=re.escape(
            f"Class `{dict_subclass.__name__}` subclasses `Dict`."
            + " Subclassing `Dict` in Structured Config classes is deprecated,"
            + " see github.com/omry/omegaconf/issues/663"
        ),
    )


@dataclass
class InnerX:
    d: int
    p: int


@dataclass
class InnerY(InnerX):
    q: int


@dataclass
class OuterA:
    x: InnerX


@dataclass
class OuterB(OuterA):
    x: InnerY
