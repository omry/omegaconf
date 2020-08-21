import dataclasses
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple, Union

import pytest

from omegaconf import II, MISSING, SI
from tests import Color

# skip test if dataclasses are not available
pytest.importorskip("dataclasses")


class NotStructuredConfig:
    name: str = "Bond"
    age: int = 7


@dataclass
class StructuredWithInvalidField:
    bar: NotStructuredConfig = NotStructuredConfig()


@dataclass
class User:
    name: str = MISSING
    age: int = MISSING


@dataclass
class UserList:
    list: List[User] = MISSING


@dataclass
class UserDict:
    dict: Dict[str, User] = MISSING


@dataclass
class AnyTypeConfig:
    with_default: Any = "Can get any type at runtime"
    null_default: Any = None
    # Access to this prior to assigning a value to it will result in
    # a MissingMandatoryValue exception.
    # Equivalent to "???" in YAML files
    mandatory_missing: Any = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: Any = II("with_default")

    # specific types assigned
    int_default: Any = 12
    float_default: Any = 10.0
    str_default: Any = "foobar"
    bool_default: Any = True
    enum_default: Any = Color.BLUE

    # test mixing with variable with a specific type annotation
    typed_int_default: int = 10


@dataclass
class BoolConfig:
    # with default value
    with_default: bool = True

    # default is None
    null_default: Optional[bool] = None

    # explicit no default
    mandatory_missing: bool = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: bool = II("with_default")


@dataclass
class IntegersConfig:
    # with default value
    with_default: int = 10

    # default is None
    null_default: Optional[int] = None

    # explicit no default
    mandatory_missing: int = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: int = II("with_default")


@dataclass
class StringConfig:
    # with default value
    with_default: str = "foo"

    # default is None
    null_default: Optional[str] = None

    # explicit no default
    mandatory_missing: str = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: str = II("with_default")


@dataclass
class FloatConfig:
    # with default value
    with_default: float = 0.10

    # default is None
    null_default: Optional[float] = None

    # explicit no default
    mandatory_missing: float = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: float = II("with_default")


@dataclass
class EnumConfig:
    # with default value
    with_default: Color = Color.BLUE

    # default is None
    null_default: Optional[Color] = None

    # explicit no default
    mandatory_missing: Color = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: Color = II("with_default")


@dataclass
class ConfigWithList:
    list1: List[int] = field(default_factory=lambda: [1, 2, 3])
    list2: Tuple[int, int, int] = field(default_factory=lambda: (1, 2, 3))
    missing: List[int] = MISSING


@dataclass
class ConfigWithDict:
    dict1: Dict[str, Any] = field(default_factory=lambda: {"foo": "bar"})
    missing: Dict[str, Any] = MISSING


@dataclass
class ConfigWithDict2:
    dict1: Dict[str, int] = field(default_factory=lambda: {"foo": 2})


@dataclass
class Nested:
    # with default value
    with_default: int = 10

    # default is None
    null_default: Optional[int] = None

    # explicit no default
    mandatory_missing: int = MISSING

    # Note that since relative interpolations are not yet supported,
    # Nested configs and interpolations does not play too well together
    interpolation: int = II("value_at_root")


@dataclass
class NestedSubclass(Nested):
    additional: int = 20


@dataclass
class NestedConfig:
    default_value: Nested

    # with default value
    user_provided_default: Nested = Nested(with_default=42)

    value_at_root: int = 1000


@dataclass
class NestedWithAny:
    var: Any = Nested()


@dataclass
class NoDefaultErrors:
    no_default: Any


@dataclass
class Interpolation:
    x: int = 100
    y: int = 200
    # The real type of y is int, cast the interpolation string
    # to help static type checkers to see this truth
    z1: int = II("x")
    z2: str = SI("${x}_${y}")


@dataclass
class BoolOptional:
    with_default: Optional[bool] = True
    as_none: Optional[bool] = None
    not_optional: bool = True


@dataclass
class IntegerOptional:
    with_default: Optional[int] = 1
    as_none: Optional[int] = None
    not_optional: int = 1


@dataclass
class FloatOptional:
    with_default: Optional[float] = 1.0
    as_none: Optional[float] = None
    not_optional: float = 1


@dataclass
class StringOptional:
    with_default: Optional[str] = "foo"
    as_none: Optional[str] = None
    not_optional: str = "foo"


@dataclass
class ListOptional:
    with_default: Optional[List[int]] = field(default_factory=lambda: [1, 2, 3])
    as_none: Optional[List[int]] = None
    not_optional: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class TupleOptional:
    with_default: Optional[Tuple[int, int, int]] = field(
        default_factory=lambda: (1, 2, 3)
    )
    as_none: Optional[Tuple[int, int, int]] = None
    not_optional: Tuple[int, int, int] = field(default_factory=lambda: (1, 2, 3))


@dataclass
class EnumOptional:
    with_default: Optional[Color] = Color.BLUE
    as_none: Optional[Color] = None
    not_optional: Color = Color.BLUE


@dataclass
class DictOptional:
    with_default: Optional[Dict[str, int]] = field(default_factory=lambda: {"a": 10})
    as_none: Optional[Dict[str, int]] = None
    not_optional: Dict[str, int] = field(default_factory=lambda: {"a": 10})


@dataclass
class StructuredOptional:
    with_default: Optional[Nested] = Nested()
    as_none: Optional[Nested] = None
    not_optional: Nested = Nested()


@dataclass(frozen=True)
class FrozenClass:
    user: User = User(name="Bart", age=10)
    x: int = 10
    list: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class ContainsFrozen:
    x: int = 10
    frozen: FrozenClass = FrozenClass()


@dataclass
class WithTypedList:
    list: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class WithTypedDict:
    dict: Dict[str, int] = field(default_factory=lambda: {"foo": 10, "bar": 20})


@dataclass
class ErrorDictIntKey:
    # invalid dict key, must be str
    dict: Dict[int, str] = field(default_factory=lambda: {10: "foo", 20: "bar"})


class RegularClass:
    pass


@dataclass
class ErrorDictUnsupportedValue:
    # invalid dict value type, not one of the supported types
    dict: Dict[str, RegularClass] = field(default_factory=dict)


@dataclass
class ErrorListUnsupportedValue:
    # invalid dict value type, not one of the supported types
    dict: List[RegularClass] = field(default_factory=list)


@dataclass
class ErrorListUnsupportedStructuredConfig:
    # Nesting of structured configs in Dict and List is not currently supported
    list: List[User] = field(default_factory=list)


@dataclass
class ListExamples:
    any: List[Any] = field(default_factory=lambda: [1, "foo"])
    ints: List[int] = field(default_factory=lambda: [1, 2])
    strings: List[str] = field(default_factory=lambda: ["foo", "bar"])
    booleans: List[bool] = field(default_factory=lambda: [True, False])
    colors: List[Color] = field(default_factory=lambda: [Color.RED, Color.GREEN])


@dataclass
class TupleExamples:
    any: Tuple[Any, Any] = field(default_factory=lambda: (1, "foo"))
    ints: Tuple[int, int] = field(default_factory=lambda: (1, 2))
    strings: Tuple[str, str] = field(default_factory=lambda: ("foo", "bar"))
    booleans: Tuple[bool, bool] = field(default_factory=lambda: (True, False))
    colors: Tuple[Color, Color] = field(
        default_factory=lambda: (Color.RED, Color.GREEN)
    )


@dataclass
class DictExamples:
    any: Dict[str, Any] = field(default_factory=lambda: {"a": 1, "b": "foo"})
    ints: Dict[str, int] = field(default_factory=lambda: {"a": 10, "b": 20})
    strings: Dict[str, str] = field(default_factory=lambda: {"a": "foo", "b": "bar"})
    booleans: Dict[str, bool] = field(default_factory=lambda: {"a": True, "b": False})
    colors: Dict[str, Color] = field(
        default_factory=lambda: {
            "red": Color.RED,
            "green": Color.GREEN,
            "blue": Color.BLUE,
        }
    )


@dataclass
class DictWithEnumKeys:
    enum_key: Dict[Color, str] = field(
        default_factory=lambda: {Color.RED: "red", Color.GREEN: "green"}
    )


@dataclass
class DictOfObjects:
    users: Dict[str, User] = field(
        default_factory=lambda: {"joe": User(name="Joe", age=18)}
    )


@dataclass
class ListOfObjects:
    users: List[User] = field(default_factory=lambda: [User(name="Joe", age=18)])


class DictSubclass:
    @dataclass
    class Str2Str(Dict[str, str]):
        pass

    @dataclass
    class Color2Str(Dict[Color, str]):
        pass

    @dataclass
    class Color2Color(Dict[Color, Color]):
        pass

    @dataclass
    class Str2User(Dict[str, User]):
        pass

    @dataclass
    class Str2StrWithField(Dict[str, str]):
        foo: str = "bar"

    @dataclass
    class Str2IntWithStrField(Dict[str, int]):
        foo: str = "bar"

    class Error:
        @dataclass
        class User2Str(Dict[User, str]):
            pass


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
class PluginWithAdditionalField(Plugin):
    name: str = "foobar2_plugin"
    additional: int = 10


# Does not extend Plugin, cannot be assigned or merged
@dataclass
class FaultyPlugin:
    name: str = "faulty_plugin"


@dataclass
class PluginHolder:
    none: Optional[Plugin] = None
    missing: Plugin = MISSING
    plugin: Plugin = Plugin()
    plugin2: Plugin = ConcretePlugin()


@dataclass
class LinkedList:
    next: Optional["LinkedList"] = None
    value: Any = MISSING


class MissingTest:
    @dataclass
    class Missing1:
        head: LinkedList = MISSING

    @dataclass
    class Missing2:
        head: LinkedList = LinkedList(next=MISSING, value=1)


@dataclass
class NestedWithNone:
    plugin: Optional[Plugin] = None


@dataclass
class UnionError:
    x: Union[int, str] = 10


@dataclass
class WithNativeMISSING:
    num: int = dataclasses.MISSING  # type: ignore


@dataclass
class MissingStructuredConfigField:
    plugin: Plugin = MISSING


@dataclass
class ListClass:
    list: List[int] = field(default_factory=lambda: [])
    tuple: Tuple[int, int] = field(default_factory=lambda: (1, 2))
