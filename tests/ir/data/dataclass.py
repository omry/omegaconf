from dataclasses import dataclass

from omegaconf import MISSING


@dataclass
class User:
    name: str
    age: int


@dataclass
class UserWithMissing:
    name: str = MISSING
    age: int = MISSING
