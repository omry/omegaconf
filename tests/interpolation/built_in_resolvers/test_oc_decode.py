import re
from typing import Any, Optional

from pytest import mark, param, raises

from omegaconf import OmegaConf
from omegaconf.errors import InterpolationResolutionError


@mark.parametrize(
    "value,expected",
    [
        # We only test a few typical cases: more extensive grammar tests are
        # found in `test_grammar.py`.
        # bool
        ("false", False),
        ("true", True),
        # int
        ("10", 10),
        ("-10", -10),
        # float
        ("10.0", 10.0),
        ("-10.0", -10.0),
        # null
        ("null", None),
        ("NulL", None),
        # strings
        ("hello", "hello"),
        ("hello world", "hello world"),
        ("  123  ", "  123  "),
        ('"123"', "123"),
        # lists and dicts
        ("[1, 2, 3]", [1, 2, 3]),
        ("{a: 0, b: 1}", {"a": 0, "b": 1}),
        ("[\t1, 2, 3\t]", [1, 2, 3]),
        ("{   a: b\t  }", {"a": "b"}),
        # interpolations
        ("${parent.sibling}", 1),
        ("${.sibling}", 1),
        ("${..parent.sibling}", 1),
        ("${uncle}", 2),
        ("${..uncle}", 2),
        ("${oc.env:MYKEY}", 456),
    ],
)
def test_decode(monkeypatch: Any, value: Optional[str], expected: Any) -> None:
    monkeypatch.setenv("MYKEY", "456")
    c = OmegaConf.create(
        {
            # The node of interest is "node" (others are used to test interpolations).
            "parent": {
                "node": f"${{oc.decode:'{value}'}}",
                "sibling": 1,
            },
            "uncle": 2,
        }
    )
    assert c.parent.node == expected


def test_decode_none() -> None:
    c = OmegaConf.create({"x": "${oc.decode:null}"})
    assert c.x is None


@mark.parametrize(
    ("value", "exc"),
    [
        param(
            123,
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "TypeError raised while resolving interpolation: "
                    "`oc.decode` can only take strings or None as input, but `123` is of type int"
                ),
            ),
            id="bad_type",
        ),
        param(
            "'[1, '",
            raises(
                InterpolationResolutionError,
                match=re.escape(
                    "GrammarParseError raised while resolving interpolation: "
                    "missing BRACKET_CLOSE at '<EOF>'"
                ),
            ),
            id="parse_error",
        ),
        param(
            # Must be escaped to prevent resolution before feeding it to `oc.decode`.
            "'\\${foo}'",
            raises(
                InterpolationResolutionError,
                match=re.escape("Interpolation key 'foo' not found"),
            ),
            id="interpolation_not_found",
        ),
    ],
)
def test_decode_error(monkeypatch: Any, value: Any, exc: Any) -> None:
    c = OmegaConf.create({"x": f"${{oc.decode:{value}}}"})
    with exc:
        c.x
