import re
from typing import Any, Optional

from pytest import mark, param, raises, warns

from omegaconf import OmegaConf
from omegaconf._utils import _ensure_container
from omegaconf.errors import InterpolationResolutionError


@mark.parametrize("env_func", ["env", "oc.env"])
class TestEnvInterpolation:
    @mark.parametrize(
        ("cfg", "env_name", "env_val", "key", "expected"),
        [
            param(
                {"path": "/test/${${env_func}:foo}"},
                "foo",
                "1234",
                "path",
                "/test/1234",
                id="simple",
            ),
            param(
                {"path": "/test/${${env_func}:not_found,ZZZ}"},
                None,
                None,
                "path",
                "/test/ZZZ",
                id="not_found_with_default",
            ),
            param(
                {"path": "/test/${${env_func}:not_found,a/b}"},
                None,
                None,
                "path",
                "/test/a/b",
                id="not_found_with_default",
            ),
        ],
    )
    def test_env_interpolation(
        self,
        # DEPRECATED: remove in 2.2 with the legacy env resolver
        recwarn: Any,
        monkeypatch: Any,
        env_func: str,
        cfg: Any,
        env_name: Optional[str],
        env_val: str,
        key: str,
        expected: Any,
    ) -> None:
        if env_name is not None:
            monkeypatch.setenv(env_name, env_val)

        cfg["env_func"] = env_func  # allows choosing which env resolver to use
        cfg = OmegaConf.create(cfg)

        assert OmegaConf.select(cfg, key) == expected

    @mark.parametrize(
        ("cfg", "key", "expected"),
        [
            param(
                {"path": "/test/${${env_func}:not_found}"},
                "path",
                raises(
                    InterpolationResolutionError,
                    match=re.escape("Environment variable 'not_found' not found"),
                ),
                id="not_found",
            ),
        ],
    )
    def test_env_interpolation_error(
        self,
        # DEPRECATED: remove in 2.2 with the legacy env resolver
        recwarn: Any,
        env_func: str,
        cfg: Any,
        key: str,
        expected: Any,
    ) -> None:
        cfg["env_func"] = env_func  # allows choosing which env resolver to use
        cfg = _ensure_container(cfg)

        with expected:
            OmegaConf.select(cfg, key)


def test_legacy_env_is_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("FOOBAR", "1234")
    c = OmegaConf.create({"foobar": "${env:FOOBAR}"})
    with warns(UserWarning):
        before = c.foobar
        monkeypatch.setenv("FOOBAR", "3456")
        assert c.foobar == before


def test_env_is_not_cached(monkeypatch: Any) -> None:
    monkeypatch.setenv("FOOBAR", "1234")
    c = OmegaConf.create({"foobar": "${oc.env:FOOBAR}"})
    before = c.foobar
    monkeypatch.setenv("FOOBAR", "3456")
    assert c.foobar != before


@mark.parametrize(
    "value",
    ["false", "true", "10", "1.5", "null", "None", "${foo}"],
)
def test_env_preserves_string(monkeypatch: Any, value: str) -> None:
    monkeypatch.setenv("MYKEY", value)
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY}"})
    assert c.my_key == value


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


def test_env_default_none(monkeypatch: Any) -> None:
    monkeypatch.delenv("MYKEY", raising=False)
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, null}"})
    assert c.my_key is None


@mark.parametrize("has_var", [True, False])
def test_env_non_str_default(monkeypatch: Any, has_var: bool) -> None:
    if has_var:
        monkeypatch.setenv("MYKEY", "456")
    else:
        monkeypatch.delenv("MYKEY", raising=False)

    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, 123}"})
    with raises(
        InterpolationResolutionError,
        match=re.escape(
            "TypeError raised while resolving interpolation: The default value "
            "of the `oc.env` resolver must be a string or None, but `123` is of type int"
        ),
    ):
        c.my_key
