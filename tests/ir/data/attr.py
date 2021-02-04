import attr

from omegaconf import MISSING


@attr.s(auto_attribs=True)
class User:
    name: str
    age: int


@attr.s(auto_attribs=True)
class UserWithMissing:
    name: str = MISSING
    age: int = MISSING
