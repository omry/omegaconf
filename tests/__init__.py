from contextlib import contextmanager
from typing import Any, Iterator


class IllegalType:
    def __init__(self) -> None:
        pass


@contextmanager
def does_not_raise(enter_result: Any = None) -> Iterator[Any]:
    yield enter_result
