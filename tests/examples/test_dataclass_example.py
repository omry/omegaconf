from enum import Enum

import pytest

from dataclasses import dataclass, field
from typing import List, Dict, Optional

from omegaconf import (
    OmegaConf,
    ValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    MISSING,
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


def test_simple_types_class():
    # Instantiate from a class
    conf = OmegaConf.create(SimpleTypes)
    assert conf.num == 10
    assert conf.pi == 3.1415
    assert conf.is_awesome is True
    assert conf.height == Height.SHORT
    assert conf.description == "text"


def test_static_typing():
    conf: SimpleTypes = OmegaConf.create(SimpleTypes)
    assert conf.description == "text"  # passes static type checking
    with pytest.raises(KeyError):
        # This will fail both the static type checking and at runtime
        # noinspection PyStatementEffect
        conf.no_such_attribute


def test_simple_types_obj():
    # Instantiate from an Object, any value can be overridden
    # at construction
    conf = OmegaConf.create(SimpleTypes(num=20, pi=3))
    assert conf.num == 20
    assert conf.pi == 3
    # Everything not overridden at construction takes the default value
    assert conf.is_awesome is True
    assert conf.height == Height.SHORT
    assert conf.description == "text"


def test_conversions():
    conf = OmegaConf.create(SimpleTypes)

    # OmegaConf can convert types at runtime
    conf.num = 20  # ok, type matches
    conf.num = "20"  # ok, the String "20" is converted to the int 20
    assert conf.num == 20
    with pytest.raises(ValidationError):
        conf.num = "one"  # ValidationError: "one" cannot be converted to an integer

    # booleans can take many forms
    for expected, values in {
        True: ["on", "yes", "true", True, "1"],
        False: ["off", "no", "false", False, "0"],
    }.items():
        for b in values:
            conf.is_awesome = b
            assert conf.is_awesome == expected

    # Enums too
    for expected, values in {
        Height.SHORT: [Height.SHORT, "Height.SHORT", "SHORT", 0],
        Height.TALL: [Height.TALL, "Height.TALL", "TALL", 1],
    }.items():
        for b in values:
            conf.height = b
            assert conf.height == expected


@dataclass
class Modifiers:
    # regular field
    num: int = 10

    # Fields can be optional
    optional_num: Optional[int] = None

    # MISSING fields must be populated at runtime before access. accessing them while they
    # are missing will result in a MissingMandatoryValue exception
    another_num: int = MISSING


def test_modifiers():
    conf: Modifiers = OmegaConf.create(Modifiers)
    # regular fields cannot take None
    with pytest.raises(ValidationError):
        conf.num = None

    # but Optional fields can
    conf.optional_num = None
    assert conf.optional_num is None

    # Accessing a missing field will trigger MissingMandatoryValue exception
    with pytest.raises(MissingMandatoryValue):
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
    manager: User = User(name="manager", height=Height.TALL)


def test_nesting():
    conf = OmegaConf.create(Group)
    assert conf == {
        "name": "???",
        "admin": {"name": MISSING, "height": MISSING},
        "manager": {"name": "manager", "height": Height.TALL},
    }

    assert (
        conf.pretty()
        == """admin:
  height: ???
  name: ???
manager:
  height: Height.TALL
  name: manager
name: ???
"""
    )

    # you can assign a different object of the same type
    conf.admin = User(name="omry", height=Height.TALL)
    with pytest.raises(ValidationError):
        # but not incompatible types
        conf.admin = 10

    with pytest.raises(ValidationError):
        # You can't assign a dict even if the field matches
        conf.manager = {"name": "secret", "height": Height.TALL}


@dataclass
class Lists:
    # List without a specified type. can take any primitive type OmegaConf supports:
    # int, float, bool, str and Enums as well as Any (which is the same as not having a specified type).
    untyped_list: List = field(default_factory=lambda: [1, "foo", True])

    # typed lists can hold int, bool, str, float or enums.
    int_list: List[int] = field(default_factory=lambda: [10, 20, 30])


def test_typed_list_runtime_validation():
    conf = OmegaConf.create(Lists)

    conf.untyped_list[0] = True  # okay, list can hold any primitive type

    conf.int_list[0] = 999  # okay
    assert conf.int_list[0] == 999

    conf.int_list[0] = "1000"  # also ok!
    assert conf.int_list[0] == 1000

    with pytest.raises(ValidationError):
        conf.int_list[0] = "fail"


# Dicts
@dataclass
class Dicts:
    # Dict without specified types.
    # Key must be a string, value can be any primitive type OmegaConf supports:
    # int, float, bool, str and Enums as well as Any (which is the same as not having a specified type).
    untyped_dict: Dict = field(default_factory=lambda: {"foo": True, "bar": 100})

    # maps string to height Enum
    str_to_height: Dict[str, Height] = field(
        default_factory=lambda: {"Yoda": Height.SHORT, "3-CPO": Height.TALL}
    )


def test_typed_dict_runtime_validation():
    conf = OmegaConf.create(Dicts)
    conf.untyped_dict["foo"] = "buzz"  # okay, list can hold any primitive type
    conf.str_to_height["Shorty"] = Height.SHORT  # Okay
    with pytest.raises(ValidationError):
        # runtime failure, cannot convert True to Height
        conf.str_to_height["Yoda"] = True


# Frozen
@dataclass(frozen=True)
class FrozenClass:
    x: int = 10
    list: List = field(default_factory=lambda: [1, 2, 3])


def test_frozen():
    # frozen classes are read only, attempts to modify them at runtime
    # will result in a ReadonlyConfigError
    conf = OmegaConf.create(FrozenClass)
    with pytest.raises(ReadonlyConfigError):
        conf.x = 20

    # Read-only flag is recursive
    with pytest.raises(ReadonlyConfigError):
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
class WebServer:
    protocol_ports: Dict[Protocol, int] = field(
        default_factory=lambda: {Protocol.HTTP: 80, Protocol.HTTPS: 443}
    )
    # Dict of name to domain
    domains: Dict[str, Domain] = field(default_factory=lambda: {})

    # List of all domains
    domains_list: List[Domain] = field(default_factory=lambda: [])


# Test that Enum can be used a dictionary key
def test_enum_key():
    conf = OmegaConf.create(WebServer)
    # When an Enum is a dictionary key the name of the Enum is actually used
    # as the key
    assert conf.protocol_ports.HTTP == 80
    assert conf.protocol_ports["HTTP"] == 80
    assert conf.protocol_ports[Protocol.HTTP] == 80


def test_dict_of_objects():
    conf: WebServer = OmegaConf.create(WebServer)
    conf.domains["blog"] = Domain(name="blog.example.com", path="/www/blog.example.com")
    with pytest.raises(ValidationError):
        conf.domains.foo = 10

    assert conf.domains["blog"].name == "blog.example.com"
    assert conf.domains["blog"].path == "/www/blog.example.com"
    assert conf == {
        "protocol_ports": {"HTTP": 80, "HTTPS": 443},
        "domains": {
            "blog": {
                "name": "blog.example.com",
                "path": "/www/blog.example.com",
                "protocols": [Protocol.HTTPS],
            }
        },
        "domains_list": [],
    }


def test_list_of_objects():
    conf: WebServer = OmegaConf.create(WebServer)
    conf.domains_list.append(
        Domain(name="blog.example.com", path="/www/blog.example.com")
    )
    with pytest.raises(ValidationError):
        conf.domains_list.append(10)

    assert conf.domains_list[0].name == "blog.example.com"
    assert conf.domains_list[0].path == "/www/blog.example.com"
    assert conf == {
        "protocol_ports": {"HTTP": 80, "HTTPS": 443},
        "domains": {},
        "domains_list": [
            {
                "name": "blog.example.com",
                "path": "/www/blog.example.com",
                "protocols": [Protocol.HTTPS],
            }
        ],
    }


def test_merge():
    @dataclass
    class Config:
        num: int = 10
        user: User = User(name=MISSING, height=MISSING)
        domains: Dict[str, Domain] = field(default_factory=lambda: {})

    yaml = """
user:
    name: Omry
domains:
    blog_website:
        name: blog
        protocols:
          - HTTPS
"""

    schema: Config = OmegaConf.create(Config)
    cfg = OmegaConf.create(yaml)
    merged = OmegaConf.merge(schema, cfg)
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


def test_merge_example():
    @dataclass
    class Server:
        port: int = MISSING

    @dataclass
    class Log:
        file: str = MISSING
        rotation: int = MISSING

    @dataclass
    class MyConfig:
        server: Server = Server()
        log: Log = Log()
        users: List[str] = field(default_factory=lambda: [])
        numbers: List[int] = field(default_factory=lambda: [])

    schema = OmegaConf.create(MyConfig)
    with pytest.raises(ValidationError):
        OmegaConf.merge(schema, OmegaConf.create({"log": {"rotation": "foo"}}))

    with pytest.raises(ValidationError):
        cfg = schema.copy()
        cfg.numbers.append("fo")

    with pytest.raises(ValidationError):
        OmegaConf.merge(schema, OmegaConf.create({"numbers": ["foo"]}))
