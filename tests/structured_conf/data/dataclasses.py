import dataclasses
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

from pytest import importorskip

from omegaconf import II, MISSING, SI
from tests import Color, Enum1

if sys.version_info >= (3, 8):  # pragma: no cover
    from typing import TypedDict

# skip test if dataclasses are not available
importorskip("dataclasses")


class NotStructuredConfig:
    name: str = "Bond"
    age: int = 7

    def __eq__(self, other: Any) -> Any:
        if isinstance(other, type(self)):
            return self.name == other.name and self.age == other.age
        return False


if sys.version_info >= (3, 8):  # pragma: no cover

    class TypedDictSubclass(TypedDict):
        foo: str


@dataclass
class StructuredWithInvalidField:
    bar: NotStructuredConfig = field(default_factory=NotStructuredConfig)


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
class UserWithDefaultName(User):
    name: str = "bob"


@dataclass
class MissingUserField:
    user: User = MISSING


@dataclass
class MissingUserWithDefaultNameField:
    user: UserWithDefaultName = MISSING


@dataclass
class OptionalUser:
    user: Optional[User] = None


@dataclass
class InterpolationToUser:
    user: User = field(default_factory=lambda: User("Bond", 7))
    admin: User = II("user")


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
class BytesConfig:
    # with default value
    with_default: bytes = b"binary"

    # default is None
    null_default: Optional[bytes] = None

    # explicit no default
    mandatory_missing: bytes = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: bytes = II("with_default")


@dataclass
class PathConfig:
    # with default value
    with_default: Path = Path("hello.txt")

    # default is None
    null_default: Optional[Path] = None

    # explicit no default
    mandatory_missing: Path = MISSING

    # interpolation, will inherit the type and value of `with_default'
    interpolation: Path = II("with_default")


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
    user_provided_default: Nested = field(
        default_factory=lambda: Nested(with_default=42)
    )

    value_at_root: int = 1000


@dataclass
class NestedWithAny:
    var: Any = field(default_factory=Nested)


@dataclass
class NoDefaultValue:
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
class RelativeInterpolation:
    x: int = 100
    y: int = 200
    z1: int = II(".x")
    z2: str = SI("${.x}_${.y}")


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
class RecursiveDict:
    d: Dict[str, "RecursiveDict"] = MISSING


@dataclass
class StructuredOptional:
    with_default: Optional[Nested] = field(default_factory=Nested)
    as_none: Optional[Nested] = None
    not_optional: Nested = field(default_factory=Nested)


@dataclass(frozen=True)
class FrozenClass:
    user: User = field(default_factory=lambda: User(name="Bart", age=10))
    x: int = 10
    list: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class ContainsFrozen:
    x: int = 10
    frozen: FrozenClass = FrozenClass()


@dataclass
class WithListField:
    list: List[int] = field(default_factory=lambda: [1, 2, 3])


@dataclass
class WithDictField:
    dict: Dict[str, int] = field(default_factory=lambda: {"foo": 10, "bar": 20})


if sys.version_info >= (3, 8):  # pragma: no cover

    @dataclass
    class WithTypedDictField:
        dict: TypedDictSubclass


@dataclass
class ErrorDictObjectKey:
    # invalid dict key, must be str
    dict: Dict[object, str] = field(
        default_factory=lambda: {object(): "foo", object(): "bar"}
    )


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
    int_keys: Dict[int, str] = field(default_factory=lambda: {1: "one", 2: "two"})
    float_keys: Dict[float, str] = field(
        default_factory=lambda: {1.1: "one", 2.2: "two"}
    )
    bool_keys: Dict[bool, str] = field(default_factory=lambda: {True: "T", False: "F"})
    enum_key: Dict[Color, str] = field(
        default_factory=lambda: {Color.RED: "red", Color.GREEN: "green"}
    )


@dataclass
class DictOfObjects:
    users: Dict[str, User] = field(
        default_factory=lambda: {"joe": User(name="Joe", age=18)}
    )


@dataclass
class DictOfObjectsMissing:
    users: Dict[str, User] = field(default_factory=lambda: {"moe": MISSING})


@dataclass
class ListOfObjects:
    users: List[User] = field(default_factory=lambda: [User(name="Joe", age=18)])


@dataclass
class ListOfObjectsMissing:
    users: List[User] = field(default_factory=lambda: [MISSING])


class DictSubclass:
    @dataclass
    class Str2Str(Dict[str, str]):
        pass

    @dataclass
    class Str2Int(Dict[str, int]):
        pass

    @dataclass
    class Int2Str(Dict[int, str]):
        pass

    @dataclass
    class Float2Str(Dict[float, str]):
        pass

    @dataclass
    class Bool2Str(Dict[bool, str]):
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
        foo: int = 1

    @dataclass
    class Str2UserWithField(Dict[str, User]):
        foo: User = field(default_factory=lambda: User("Bond", 7))

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

    params: FoobarParams = field(default_factory=FoobarParams)


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
    plugin: Plugin = field(default_factory=Plugin)
    plugin2: Plugin = field(default_factory=ConcretePlugin)


@dataclass
class LinkedList:
    next: Optional["LinkedList"] = None
    value: Any = MISSING


@dataclass
class RecursiveList:
    d: List["RecursiveList"] = MISSING


class MissingTest:
    @dataclass
    class Missing1:
        head: LinkedList = MISSING

    @dataclass
    class Missing2:
        head: LinkedList = field(
            default_factory=lambda: LinkedList(next=MISSING, value=1)
        )


@dataclass
class NestedWithNone:
    plugin: Optional[Plugin] = None


@dataclass
class UnionError:
    x: Union[int, List[str]] = 10


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


@dataclass
class UntypedList:
    list: List = field(default_factory=lambda: [1, 2])  # type: ignore
    opt_list: Optional[List] = None  # type: ignore


@dataclass
class UntypedDict:
    dict: Dict = field(default_factory=lambda: {"foo": "var"})  # type: ignore
    opt_dict: Optional[Dict] = None  # type: ignore


class StructuredSubclass:
    @dataclass
    class ParentInts:
        int1: int
        int2: int
        int3: int = dataclasses.MISSING  # type: ignore
        int4: int = MISSING

    @dataclass
    class ChildInts(ParentInts):
        int2: int = 5
        int3: int = 10
        int4: int = 15

    @dataclass
    class ParentContainers:
        list1: List[int] = MISSING
        list2: List[int] = field(default_factory=lambda: [5, 6])
        dict: Dict[str, Any] = MISSING

    @dataclass
    class ChildContainers(ParentContainers):
        list1: List[int] = field(default_factory=lambda: [1, 2, 3])
        dict: Dict[str, Any] = field(default_factory=lambda: {"a": 5, "b": 6})

    @dataclass
    class ParentNoDefaultFactory:
        no_default_to_list: Any
        int_to_list: Any = 1

    @dataclass
    class ChildWithDefaultFactory(ParentNoDefaultFactory):
        no_default_to_list: Any = field(default_factory=lambda: ["hi"])
        int_to_list: Any = field(default_factory=lambda: ["hi"])


@dataclass
class HasInitFalseFields:
    post_initialized: str = field(init=False)
    without_default: str = field(init=False)
    with_default: str = field(init=False, default="default")

    def __post_init__(self) -> None:
        self.post_initialized = "set_by_post_init"


class NestedContainers:
    @dataclass
    class ListOfLists:
        lls: List[List[str]]
        llx: List[List[User]]
        llla: List[List[List[Any]]]
        lloli: List[List[Optional[List[int]]]]
        lls_default: List[List[str]] = field(
            default_factory=lambda: [[], ["abc", "def", 123, MISSING], MISSING]  # type: ignore
        )
        lolx_default: List[Optional[List[User]]] = field(
            default_factory=lambda: [
                [],
                [User(), User(age=7, name="Bond"), MISSING],
                MISSING,
            ]
        )

    @dataclass
    class DictOfDicts:
        dsdsi: Dict[str, Dict[str, int]]
        dsdbi: Dict[str, Dict[bool, int]]
        dsdsx: Dict[str, Dict[str, User]]
        odsdsi_default: Optional[Dict[str, Dict[str, int]]] = field(
            default_factory=lambda: {
                "dsi1": {},
                "dsi2": {"s1": 1, "s2": "123", "s3": MISSING},
                "dsi3": MISSING,
            }
        )
        dsdsx_default: Dict[str, Dict[str, User]] = field(
            default_factory=lambda: {
                "dsx1": {},
                "dsx2": {
                    "s1": User(),
                    "s2": User(age=7, name="Bond"),
                    "s3": MISSING,
                },
                "dsx3": MISSING,
            }
        )

    @dataclass
    class ListsAndDicts:
        lldsi: List[List[Dict[str, int]]]
        ldaos: List[Dict[Any, Optional[str]]]
        dedsle: Dict[Color, Dict[str, List[Enum1]]]
        dsolx: Dict[str, Optional[List[User]]]
        oldfox: Optional[List[Dict[float, Optional[User]]]]
        dedsle_default: Dict[Color, Dict[str, List[Enum1]]] = field(
            default_factory=lambda: {
                Color.RED: {"a": [Enum1.FOO, Enum1.BAR]},
                Color.GREEN: {"b": []},
                Color.BLUE: {},
            }
        )

    @dataclass
    class WithDefault:
        dsolx_default: Dict[str, Optional[List[User]]] = field(
            default_factory=lambda: {"lx": [User()], "n": None}
        )


class UnionsOfPrimitveTypes:
    @dataclass
    class Simple:
        uis: Union[int, str]
        ubc: Union[bool, Color]
        uxf: Union[bytes, float]
        ouis: Optional[Union[int, str]]
        uois: Union[Optional[int], str]
        uisn: Union[int, str, None]
        uisN: Union[int, str, type(None)]  # type: ignore

    @dataclass
    class WithDefaults:
        uis: Union[int, str] = "abc"
        ubc1: Union[bool, Color] = True
        ubc2: Union[bool, Color] = Color.RED
        uxf: Union[bytes, float] = 1.2
        ouis: Optional[Union[int, str]] = None
        uisn: Union[int, str, None] = 123
        uisN: Union[int, str, type(None)] = "abc"  # type: ignore

    @dataclass
    class WithExplicitMissing:
        uis_missing: Union[int, str] = MISSING

    @dataclass
    class WithBadDefaults1:
        uis: Union[int, str] = None  # type: ignore

    @dataclass
    class WithBadDefaults2:
        ubc: Union[bool, Color] = "abc"  # type: ignore

    @dataclass
    class WithBadDefaults3:
        uxf: Union[bytes, float] = True

    @dataclass
    class WithBadDefaults4:
        oufb: Optional[Union[float, bool]] = Color.RED  # type: ignore

    @dataclass
    class ContainersOfUnions:
        lubc: List[Union[bool, Color]]
        dsubf: Dict[str, Union[bool, float]]
        dsoubf: Dict[str, Optional[Union[bool, float]]]
        lubc_with_default: List[Union[bool, Color]] = field(
            default_factory=lambda: [True, Color.RED]
        )
        dsubf_with_default: Dict[str, Union[bool, float]] = field(
            default_factory=lambda: {"abc": True, "xyz": 1.2}
        )

    @dataclass
    class InterpolationFromUnion:
        ubi: Union[bool, int]
        oubi: Optional[Union[bool, int]]
        an_int: int = 123
        a_string: str = "abc"
        missing: int = MISSING
        none: Optional[int] = None
        ubi_with_default: Union[bool, int] = II("an_int")
        oubi_with_default: Optional[Union[bool, int]] = II("none")

    @dataclass
    class InterpolationToUnion:
        a_float: float = II("ufs")
        bad_int_interp: bool = II("ufs")
        ufs: Union[float, str] = 10.1

    @dataclass
    class BadInterpolationFromUnion:
        a_float: float = 10.1
        ubi: Union[bool, int] = II("a_float")

    if sys.version_info >= (3, 10):

        @dataclass
        class SupportPEP604:
            """https://peps.python.org/pep-0604/"""

            uis: int | str
            ouis: Optional[int | str]
            uisn: int | str | None = None
            uis_with_default: int | str = 123


if sys.version_info >= (3, 9):

    @dataclass
    class SupportPEP585:
        """
        PEP 585 – Type Hinting Generics In Standard Collections
        https://peps.python.org/pep-0585/

        This means lower-case dict/list/tuple annotations
        can be used instad of uppercase Dict/List/Tuple.
        """

        dict_: dict[int, str] = field(default_factory=lambda: {123: "abc"})
        list_: list[int] = field(default_factory=lambda: [123])
        tuple_: tuple[int] = (123,)
        dict_no_subscript: dict = field(default_factory=lambda: {123: "abc"})
        list_no_subscript: list = field(default_factory=lambda: [123])
        tuple_no_subscript: tuple = (123,)


@dataclass
class HasForwardRef:
    @dataclass
    class CA:
        x: int = 3

    @dataclass
    class CB:
        sub: "HasForwardRef.CA"

    a: CA
    b: CB


@dataclass
class HasBadAnnotation1:
    data: object


@dataclass
class HasBadAnnotation2:
    data: object()  # type: ignore


@dataclass
class HasIgnoreMetadataRequired:
    ignore: int = field(metadata={"omegaconf_ignore": True})
    no_ignore: int = field(metadata={"omegaconf_ignore": False})


@dataclass
class HasIgnoreMetadataWithDefault:
    ignore: int = field(default=1, metadata={"omegaconf_ignore": True})
    no_ignore: int = field(default=2, metadata={"omegaconf_ignore": False})
