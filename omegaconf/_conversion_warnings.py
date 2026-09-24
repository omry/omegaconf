import functools
import sys
import warnings
from contextlib import contextmanager
from contextvars import ContextVar
from typing import Any, Callable, Iterator, ParamSpec, TypeVar

_P = ParamSpec("_P")
_R = TypeVar("_R")
# None: outside a mutation; True: direct mutation; False: construction or an
# explicit conversion path, including nested writes made by that operation.
_conversion_warning_mode: ContextVar[bool | None] = ContextVar(
    "conversion_warning_mode", default=None
)


def _warn_implicit_conversion(
    source_type: type[Any], target_type: type[Any], full_key: str
) -> None:
    level = 2
    frame = sys._getframe(1)
    while frame is not None and frame.f_globals.get("__name__", "").startswith(
        "omegaconf."
    ):
        level += 1
        frame = frame.f_back
    warnings.warn(
        f"Implicit conversion from {source_type.__name__} to "
        f"{target_type.__name__} at '{full_key}' during assignment is "
        "deprecated; pass the declared type or use OmegaConf.update() for an "
        "existing path.",
        FutureWarning,
        stacklevel=level,
    )


@contextmanager
def _conversion_warnings(
    enabled: bool, *, only_if_unset: bool = False
) -> Iterator[None]:
    if only_if_unset and _conversion_warning_mode.get() is not None:
        yield
        return
    token = _conversion_warning_mode.set(enabled)
    try:
        yield
    finally:
        _conversion_warning_mode.reset(token)


def _warn_on_conversion(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(func)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with _conversion_warnings(True, only_if_unset=True):
            return func(*args, **kwargs)

    return wrapped


def _suppress_conversion_warnings(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(func)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with _conversion_warnings(False):
            return func(*args, **kwargs)

    return wrapped


def _suppress_conversion_warnings_if_unset(func: Callable[_P, _R]) -> Callable[_P, _R]:
    @functools.wraps(func)
    def wrapped(*args: _P.args, **kwargs: _P.kwargs) -> _R:
        with _conversion_warnings(False, only_if_unset=True):
            return func(*args, **kwargs)

    return wrapped
