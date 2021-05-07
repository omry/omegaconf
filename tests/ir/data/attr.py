import attr
from attr import NOTHING as backend_MISSING

from omegaconf import MISSING


@attr.s(auto_attribs=True)
class User:
    name: str
    age: int


@attr.s(auto_attribs=True)
class UserWithMissing:
    name: str = MISSING
    age: int = MISSING


@attr.s(auto_attribs=True)
class UserWithBackendMissing:
    name: str = backend_MISSING  # type: ignore
    age: int = backend_MISSING  # type: ignore


@attr.s(auto_attribs=True)
class UserWithDefault:
    name: str = "bond"
    age: int = 7


@attr.s(auto_attribs=True)
class UserWithDefaultFactory:
    name: str = attr.ib(factory=lambda: "bond")
    age: int = attr.ib(factory=lambda: 7)
