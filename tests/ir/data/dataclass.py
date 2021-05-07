from dataclasses import MISSING as backend_MISSING
from dataclasses import dataclass, field

from omegaconf import MISSING


@dataclass
class User:
    name: str
    age: int


@dataclass
class UserWithMissing:
    name: str = MISSING
    age: int = MISSING


@dataclass
class UserWithBackendMissing:
    name: str = backend_MISSING  # type: ignore
    age: int = backend_MISSING  # type: ignore


@dataclass
class UserWithDefault:
    name: str = "bond"
    age: int = 7


@dataclass
class UserWithDefaultFactory:
    name: str = field(default_factory=lambda: "bond")
    age: int = field(default_factory=lambda: 7)
