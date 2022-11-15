from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

from pytest import raises

from omegaconf import (
    MISSING,
    DictConfig,
    MissingMandatoryValue,
    OmegaConf,
    ReadonlyConfigError,
    ValidationError,
)


class Height(Enum):
    SHORT = 0
    TALL = 1


@dataclass
class SimpleTypes:
    num: int = 10
    pi: float = 3.1415
    is_awesome: bool = True
    height: Height = Height.SHORT
    description: str = "text"
    data: bytes = b"bin_data"


def test_simple_types_class() -> None:
    # Instantiate from a class
    conf = OmegaConf.structured(SimpleTypes)
    assert conf.num == 10
    assert conf.pi == 3.1415
    assert conf.is_awesome is True
    assert conf.height == Height.SHORT
    assert conf.description == "text"
    assert conf.data == b"bin_data"


def test_static_typing() -> None:
    conf: SimpleTypes = OmegaConf.structured(SimpleTypes)
    assert conf.description == "text"  # passes static type checking
    with raises(AttributeError):
        # This will fail both the static type checking and at runtime
        # noinspection PyStatementEffect
        conf.no_such_attribute  # type: ignore


def test_simple_types_obj() -> None:
    # Instantiate from an Object, any value can be overridden
    # at construction
    conf = OmegaConf.structured(SimpleTypes(num=20, pi=3))
    assert conf.num == 20
    assert conf.pi == 3
    # Everything not overridden at construction takes the default value
    assert conf.is_awesome is True
    assert conf.height == Height.SHORT
    assert conf.description == "text"
    assert conf.data == b"bin_data"


def test_conversions() -> None:
    conf: SimpleTypes = OmegaConf.structured(SimpleTypes)

    # OmegaConf can convert types at runtime
    conf.num = 20  # ok, type matches

    # ok, the String "20" is converted to the int 20
    conf.num = "20"  # type: ignore

    assert conf.num == 20
    with raises(ValidationError):
        # ValidationError: "one" cannot be converted to an integer
        conf.num = "one"  # type: ignore

    conf.description = "abc"  # ok, type matches
    assert conf.description == "abc"
    # ok, the int 20 is converted to the string "20"
    conf.description = 20  # type: ignore
    assert conf.description == "20"
    with raises(ValidationError):
        # bytes are not automatically converted to strings
        conf.description = b"binary"  # type: ignore

    assert conf.data == b"bin_data"
    conf.data = b"def"  # assignment ok, type matches
    with raises(ValidationError):
        # ValidationError: "text" cannot be converted to bytes
        conf.data = "text"  # type: ignore
    with raises(ValidationError):
        # ValidationError: 1234 cannot be converted to bytes
        conf.data = 1234  # type: ignore

    # booleans can take many forms
    for expected, values in {
        True: ["on", "yes", "true", True, "1"],
        False: ["off", "no", "false", False, "0"],
    }.items():
        for b in values:
            conf.is_awesome = b  # type: ignore
            assert conf.is_awesome == expected

    # Enums too
    for expected1, values1 in {
        Height.SHORT: [Height.SHORT, "Height.SHORT", "SHORT", 0],
        Height.TALL: [Height.TALL, "Height.TALL", "TALL", 1],
    }.items():
        for b in values1:
            conf.height = b  # type: ignore
            assert conf.height == expected1


@dataclass
class Modifiers:
    # regular field
    num: int = 10

    # Fields can be optional
    optional_num: Optional[int] = None

    # MISSING fields must be populated at runtime before access. accessing them while they
    # are missing will result in a MissingMandatoryValue exception
    another_num: int = MISSING


def test_modifiers() -> None:
    conf: Modifiers = OmegaConf.structured(Modifiers)
    # regular fields cannot take None
    with raises(ValidationError):
        conf.num = None  # type: ignore

    # but Optional fields can
    conf.optional_num = None
    assert conf.optional_num is None

    # Accessing a missing field will trigger MissingMandatoryValue exception
    with raises(MissingMandatoryValue):
        # noinspection PyStatementEffect
        conf.another_num

    # but you can access it once it's been assigned
    conf.another_num = 42
    assert conf.another_num == 42


@dataclass
class User:
    # A simple user class with two missing fields
    name: str = MISSING
    height: Height = MISSING


# Group class contains two instances of User.
@dataclass
class Group:
    name: str = MISSING
    # data classes can be nested
    admin: User = User  # type: ignore

    # You can also specify different defaults for nested classes
    manager: User = field(
        default_factory=lambda: User(name="manager", height=Height.TALL)
    )


def test_nesting() -> None:
    conf = OmegaConf.structured(Group)
    assert conf == {
        "name": "???",
        "admin": {"name": MISSING, "height": MISSING},
        "manager": {"name": "manager", "height": Height.TALL},
    }

    expected = """name: ???
admin:
  name: ???
  height: ???
manager:
  name: manager
  height: TALL
"""
    assert OmegaConf.to_yaml(conf) == expected

    # you can assign a different object of the same type
    conf.admin = User(name="omry", height=Height.TALL)
    with raises(ValidationError):
        # but not incompatible types
        conf.admin = 10

    with raises(ValidationError):
        # You can't assign a dict even if the field matches
        conf.manager = {"name": "secret", "height": Height.TALL}


@dataclass
class Lists:
    # List with Any as type can take any primitive type OmegaConf supports:
    # int, float, bool, str, bytes and Enums as well as Any (which is the same as not having a specified type).
    untyped_list: List[Any] = field(default_factory=lambda: [1, "foo", True])

    # typed lists can hold int, bool, str, bytes, float or enums.
    int_list: List[int] = field(default_factory=lambda: [10, 20, 30])


def test_typed_list_runtime_validation() -> None:
    conf = OmegaConf.structured(Lists)

    conf.untyped_list[0] = True  # okay, list can hold any primitive type

    conf.int_list[0] = 999  # okay
    assert conf.int_list[0] == 999

    conf.int_list[0] = "1000"  # also ok!
    assert conf.int_list[0] == 1000

    with raises(ValidationError):
        conf.int_list[0] = "fail"


# Dicts
@dataclass
class Dicts:
    # Key must be a string or Enum, value can be any primitive type OmegaConf supports:
    # int, float, bool, str, bytes and Enums as well as Any (which is the same as not having a specified type).
    untyped_dict: Dict[str, Any] = field(
        default_factory=lambda: {"foo": True, "bar": 100}
    )

    # maps string to height Enum
    str_to_height: Dict[str, Height] = field(
        default_factory=lambda: {"Yoda": Height.SHORT, "3-CPO": Height.TALL}
    )


def test_typed_dict_runtime_validation() -> None:
    conf = OmegaConf.structured(Dicts)
    conf.untyped_dict["foo"] = "buzz"  # okay, list can hold any primitive type
    conf.str_to_height["Shorty"] = Height.SHORT  # Okay
    with raises(ValidationError):
        # runtime failure, cannot convert True to Height
        conf.str_to_height["Yoda"] = True


# Frozen
@dataclass(frozen=True)
class FrozenClass:
    x: int = 10
    list: List[int] = field(default_factory=lambda: [1, 2, 3])


def test_frozen() -> None:
    # frozen classes are read only, attempts to modify them at runtime
    # will result in a ReadonlyConfigError
    conf = OmegaConf.structured(FrozenClass)
    with raises(ReadonlyConfigError):
        conf.x = 20

    # Read-only flag is recursive
    with raises(ReadonlyConfigError):
        conf.list[0] = 20


class Protocol(Enum):
    HTTP = 0
    HTTPS = 1


@dataclass
class Domain:
    name: str = MISSING
    path: str = MISSING
    protocols: List[Protocol] = field(default_factory=lambda: [Protocol.HTTPS])


@dataclass
class WebServer(DictConfig):
    protocol_ports: Dict[Protocol, int] = field(
        default_factory=lambda: {Protocol.HTTP: 80, Protocol.HTTPS: 443}
    )
    # Dict of name to domain
    domains: Dict[str, Domain] = field(default_factory=dict)

    # List of all domains
    domains_list: List[Domain] = field(default_factory=list)


# Test that Enum can be used a dictionary key
def test_enum_key() -> None:
    conf = OmegaConf.structured(WebServer)
    # When an Enum is a dictionary key the name of the Enum is actually used
    # as the key
    assert conf.protocol_ports.HTTP == 80
    assert conf.protocol_ports["HTTP"] == 80
    assert conf.protocol_ports[Protocol.HTTP] == 80


def test_dict_of_objects() -> None:
    conf: WebServer = OmegaConf.structured(WebServer)
    conf.domains["blog"] = Domain(name="blog.example.com", path="/www/blog.example.com")
    with raises(ValidationError):
        conf.domains.foo = 10  # type: ignore

    assert conf.domains["blog"].name == "blog.example.com"
    assert conf.domains["blog"].path == "/www/blog.example.com"
    assert conf == {
        "protocol_ports": {Protocol.HTTP: 80, Protocol.HTTPS: 443},
        "domains": {
            "blog": {
                "name": "blog.example.com",
                "path": "/www/blog.example.com",
                "protocols": [Protocol.HTTPS],
            }
        },
        "domains_list": [],
    }


def test_list_of_objects() -> None:
    conf: WebServer = OmegaConf.structured(WebServer)
    conf.domains_list.append(
        Domain(name="blog.example.com", path="/www/blog.example.com")
    )
    with raises(ValidationError):
        conf.domains_list.append(10)  # type: ignore

    assert conf.domains_list[0].name == "blog.example.com"
    assert conf.domains_list[0].path == "/www/blog.example.com"
    assert conf == {
        "protocol_ports": {Protocol.HTTP: 80, Protocol.HTTPS: 443},
        "domains": {},
        "domains_list": [
            {
                "name": "blog.example.com",
                "path": "/www/blog.example.com",
                "protocols": [Protocol.HTTPS],
            }
        ],
    }


def test_merge() -> None:
    @dataclass
    class Config:
        num: int = 10
        user: User = field(default_factory=lambda: User(name=MISSING, height=MISSING))
        domains: Dict[str, Domain] = field(default_factory=dict)

    yaml = """
user:
    name: Omry
domains:
    blog_website:
        name: blog
        protocols:
          - HTTPS
"""

    schema: Config = OmegaConf.structured(Config)
    cfg = OmegaConf.create(yaml)
    merged: Any = OmegaConf.merge(schema, cfg)
    assert merged == {
        "num": 10,
        "user": {"name": "Omry", "height": "???"},
        "domains": {
            "blog_website": {
                "name": "blog",
                "path": "???",
                "protocols": [Protocol.HTTPS],
            }
        },
    }
    assert OmegaConf.is_missing(merged.domains.blog_website, "path")


def test_merge_example() -> None:
    @dataclass
    class Server:
        port: int = MISSING

    @dataclass
    class Log:
        file: str = MISSING
        rotation: int = MISSING

    @dataclass
    class MyConfig:
        server: Server = field(default_factory=Server)
        log: Log = field(default_factory=Log)
        users: List[str] = field(default_factory=list)
        numbers: List[int] = field(default_factory=list)

    schema = OmegaConf.structured(MyConfig)
    with raises(ValidationError):
        OmegaConf.merge(schema, OmegaConf.create({"log": {"rotation": "foo"}}))

    with raises(ValidationError):
        cfg = schema.copy()
        cfg.numbers.append("fo")

    with raises(ValidationError):
        OmegaConf.merge(schema, OmegaConf.create({"numbers": ["foo"]}))
