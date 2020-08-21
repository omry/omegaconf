from typing import Any, Dict, List, Optional, Tuple, Union

import attr
import pytest

from omegaconf import II, MISSING, SI
from tests import Color

# attr is a dependency of pytest which means it's always available when testing with pytest.
pytest.importorskip("attr")


class NotStructuredConfig:
    name: str = "Bond"
    age: int = 7


@attr.s(auto_attribs=True)
class StructuredWithInvalidField:
    bar: NotStructuredConfig = NotStructuredConfig()


@attr.s(auto_attribs=True)
class User:
    name: str = MISSING
    age: int = MISSING


@attr.s(auto_attribs=True)
class UserList:
    list: List[User] = MISSING


@attr.s(auto_attribs=True)
class UserDict:
    dict: Dict[str, User] = MISSING


@attr.s(auto_attribs=True)
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


@attr.s(auto_attribs=True)
class BoolConfig:

    # with default value
    with_default: bool = True

    # default is None
    null_default: Optional[bool] = None

    # explicit no default
    mandatory_missing: bool = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: bool = II("with_default")


@attr.s(auto_attribs=True)
class IntegersConfig:

    # with default value
    with_default: int = 10

    # default is None
    null_default: Optional[int] = None

    # explicit no default
    mandatory_missing: int = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: int = II("with_default")


@attr.s(auto_attribs=True)
class StringConfig:

    # with default value
    with_default: str = "foo"

    # default is None
    null_default: Optional[str] = None

    # explicit no default
    mandatory_missing: str = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: str = II("with_default")


@attr.s(auto_attribs=True)
class FloatConfig:

    # with default value
    with_default: float = 0.10

    # default is None
    null_default: Optional[float] = None

    # explicit no default
    mandatory_missing: float = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: float = II("with_default")


@attr.s(auto_attribs=True)
class EnumConfig:

    # with default value
    with_default: Color = Color.BLUE

    # default is None
    null_default: Optional[Color] = None

    # explicit no default
    mandatory_missing: Color = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: Color = II("with_default")


@attr.s(auto_attribs=True)
class ConfigWithList:
    list1: List[int] = [1, 2, 3]
    list2: Tuple[int, int, int] = (1, 2, 3)
    missing: List[int] = MISSING


@attr.s(auto_attribs=True)
class ConfigWithDict:
    dict1: Dict[str, Any] = {"foo": "bar"}
    missing: Dict[str, Any] = MISSING


@attr.s(auto_attribs=True)
class ConfigWithDict2:
    dict1: Dict[str, int] = {"foo": 2}


@attr.s(auto_attribs=True)
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


@attr.s(auto_attribs=True)
class NestedSubclass(Nested):
    additional: int = 20


@attr.s(auto_attribs=True)
class NestedConfig:
    default_value: Nested

    # with default value
    user_provided_default: Nested = Nested(with_default=42)

    value_at_root: int = 1000


@attr.s(auto_attribs=True)
class NestedWithAny:
    var: Any = Nested()


@attr.s(auto_attribs=True)
class NoDefaultErrors:
    no_default: Any


@attr.s(auto_attribs=True)
class Interpolation:
    x: int = 100
    y: int = 200
    # The real type of y is int, cast the interpolation string
    # to help static type checkers to see this truth
    z1: int = II("x")
    z2: str = SI("${x}_${y}")


@attr.s(auto_attribs=True)
class BoolOptional:
    with_default: Optional[bool] = True
    as_none: Optional[bool] = None
    not_optional: bool = True


@attr.s(auto_attribs=True)
class IntegerOptional:
    with_default: Optional[int] = 1
    as_none: Optional[int] = None
    not_optional: int = 1


@attr.s(auto_attribs=True)
class FloatOptional:
    with_default: Optional[float] = 1.0
    as_none: Optional[float] = None
    not_optional: float = 1


@attr.s(auto_attribs=True)
class StringOptional:
    with_default: Optional[str] = "foo"
    as_none: Optional[str] = None
    not_optional: str = "foo"


@attr.s(auto_attribs=True)
class ListOptional:
    with_default: Optional[List[int]] = [1, 2, 3]
    as_none: Optional[List[int]] = None
    not_optional: List[int] = [1, 2, 3]


@attr.s(auto_attribs=True)
class TupleOptional:
    with_default: Optional[Tuple[int, int, int]] = (1, 2, 3)
    as_none: Optional[Tuple[int, int, int]] = None
    not_optional: Tuple[int, int, int] = (1, 2, 3)


@attr.s(auto_attribs=True)
class EnumOptional:
    with_default: Optional[Color] = Color.BLUE
    as_none: Optional[Color] = None
    not_optional: Color = Color.BLUE


@attr.s(auto_attribs=True)
class DictOptional:
    with_default: Optional[Dict[str, int]] = {"a": 10}
    as_none: Optional[Dict[str, int]] = None
    not_optional: Dict[str, int] = {"a": 10}


@attr.s(auto_attribs=True)
class StructuredOptional:
    with_default: Optional[Nested] = Nested()
    as_none: Optional[Nested] = None
    not_optional: Nested = Nested()


@attr.s(auto_attribs=True, frozen=True)
class FrozenClass:
    user: User = User(name="Bart", age=10)
    x: int = 10
    list: List[int] = [1, 2, 3]


@attr.s(auto_attribs=True)
class ContainsFrozen:
    x: int = 10
    frozen: FrozenClass = FrozenClass()


@attr.s(auto_attribs=True)
class WithTypedList:
    list: List[int] = [1, 2, 3]


@attr.s(auto_attribs=True)
class WithTypedDict:
    dict: Dict[str, int] = {"foo": 10, "bar": 20}


@attr.s(auto_attribs=True)
class ErrorDictIntKey:
    # invalid dict key, must be str
    dict: Dict[int, str] = {10: "foo", 20: "bar"}


class RegularClass:
    pass


@attr.s(auto_attribs=True)
class ErrorDictUnsupportedValue:
    # invalid dict value type, not one of the supported types
    dict: Dict[str, RegularClass] = {}


@attr.s(auto_attribs=True)
class ErrorListUnsupportedValue:
    # invalid dict value type, not one of the supported types
    dict: List[RegularClass] = []


@attr.s(auto_attribs=True)
class ListExamples:
    any: List[Any] = [1, "foo"]
    ints: List[int] = [1, 2]
    strings: List[str] = ["foo", "bar"]
    booleans: List[bool] = [True, False]
    colors: List[Color] = [Color.RED, Color.GREEN]


@attr.s(auto_attribs=True)
class TupleExamples:
    any: Tuple[Any, Any] = (1, "foo")
    ints: Tuple[int, int] = (1, 2)
    strings: Tuple[str, str] = ("foo", "bar")
    booleans: Tuple[bool, bool] = (True, False)
    colors: Tuple[Color, Color] = (Color.RED, Color.GREEN)


@attr.s(auto_attribs=True)
class DictExamples:
    any: Dict[str, Any] = {"a": 1, "b": "foo"}
    ints: Dict[str, int] = {"a": 10, "b": 20}
    strings: Dict[str, str] = {"a": "foo", "b": "bar"}
    booleans: Dict[str, bool] = {"a": True, "b": False}
    colors: Dict[str, Color] = {
        "red": Color.RED,
        "green": Color.GREEN,
        "blue": Color.BLUE,
    }


@attr.s(auto_attribs=True)
class DictWithEnumKeys:
    enum_key: Dict[Color, str] = {Color.RED: "red", Color.GREEN: "green"}


@attr.s(auto_attribs=True)
class DictOfObjects:
    users: Dict[str, User] = {"joe": User(name="Joe", age=18)}


@attr.s(auto_attribs=True)
class ListOfObjects:
    users: List[User] = [User(name="Joe", age=18)]


class DictSubclass:
    @attr.s(auto_attribs=True)
    class Str2Str(Dict[str, str]):
        pass

    @attr.s(auto_attribs=True)
    class Color2Str(Dict[Color, str]):
        pass

    @attr.s(auto_attribs=True)
    class Color2Color(Dict[Color, Color]):
        pass

    @attr.s(auto_attribs=True)
    class Str2User(Dict[str, User]):
        pass

    @attr.s(auto_attribs=True)
    class Str2StrWithField(Dict[str, str]):
        foo: str = "bar"

    @attr.s(auto_attribs=True)
    class Str2IntWithStrField(Dict[str, int]):
        foo: str = "bar"

    class Error:
        @attr.s(auto_attribs=True)
        class User2Str(Dict[User, str]):
            pass


@attr.s(auto_attribs=True)
class Plugin:
    name: str = MISSING
    params: Any = MISSING


@attr.s(auto_attribs=True)
class ConcretePlugin(Plugin):
    name: str = "foobar_plugin"

    @attr.s(auto_attribs=True)
    class FoobarParams:
        foo: int = 10

    params: FoobarParams = FoobarParams()


@attr.s(auto_attribs=True)
class PluginWithAdditionalField(Plugin):
    name: str = "foobar2_plugin"
    additional: int = 10


# Does not extend Plugin, cannot be assigned or merged
@attr.s(auto_attribs=True)
class FaultyPlugin:
    name: str = "faulty_plugin"


@attr.s(auto_attribs=True)
class PluginHolder:
    none: Optional[Plugin] = None
    missing: Plugin = MISSING
    plugin: Plugin = Plugin()
    plugin2: Plugin = ConcretePlugin()


@attr.s(auto_attribs=True)
class LinkedList:
    next: Optional["LinkedList"] = None
    value: Any = MISSING


class MissingTest:
    @attr.s(auto_attribs=True)
    class Missing1:
        head: LinkedList = MISSING

    @attr.s(auto_attribs=True)
    class Missing2:
        head: LinkedList = LinkedList(next=MISSING, value=1)


@attr.s(auto_attribs=True)
class NestedWithNone:
    plugin: Optional[Plugin] = None


@attr.s(auto_attribs=True)
class UnionError:
    x: Union[int, str] = 10


@attr.s(auto_attribs=True)
class WithNativeMISSING:
    num: int = attr.NOTHING  # type: ignore


@attr.s(auto_attribs=True)
class MissingStructuredConfigField:
    plugin: Plugin = MISSING


@attr.s(auto_attribs=True)
class ListClass:
    list: List[int] = []
    tuple: Tuple[int, int] = (1, 2)
