import re
from typing import Any

from pytest import mark, warns

from omegaconf import OmegaConf


def test_legacy_env_is_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("FOOBAR", "1234")
    c = OmegaConf.create({"foobar": "${env:FOOBAR}"})
    with warns(UserWarning):
        before = c.foobar
        monkeypatch.setenv("FOOBAR", "3456")
        assert c.foobar == before


@mark.parametrize(
    "value,expected",
    [
        # bool
        ("false", False),
        ("true", True),
        # int
        ("10", 10),
        ("-10", -10),
        # float
        ("10.0", 10.0),
        ("-10.0", -10.0),
        # strings
        ("off", "off"),
        ("no", "no"),
        ("on", "on"),
        ("yes", "yes"),
        (">1234", ">1234"),
        (":1234", ":1234"),
        ("/1234", "/1234"),
        # yaml strings are not getting parsed by the env resolver
        ("foo: bar", "foo: bar"),
        ("foo: \n - bar\n - baz", "foo: \n - bar\n - baz"),
        # more advanced uses of the grammar
        ("ab \\{foo} cd", "ab \\{foo} cd"),
        ("ab \\\\{foo} cd", "ab \\\\{foo} cd"),
        ("  1 2 3  ", "  1 2 3  "),
        ("\t[1, 2, 3]\t", "\t[1, 2, 3]\t"),
        ("   {a: b}\t  ", "   {a: b}\t  "),
    ],
)
def test_legacy_env_values_are_typed(
    monkeypatch: Any, value: Any, expected: Any
) -> None:
    monkeypatch.setenv("MYKEY", value)
    c = OmegaConf.create({"my_key": "${env:MYKEY}"})
    with warns(UserWarning, match=re.escape("The `env` resolver is deprecated")):
        assert c.my_key == expected
