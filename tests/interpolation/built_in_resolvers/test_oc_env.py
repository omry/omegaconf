import re
from typing import Any, Optional

from pytest import mark, param, raises

from omegaconf import OmegaConf
from omegaconf._utils import _ensure_container
from omegaconf.errors import InterpolationResolutionError


class TestEnvInterpolation:
    @mark.parametrize(
        ("cfg", "env_name", "env_val", "key", "expected"),
        [
            param(
                {"path": "/test/${oc.env:foo}"},
                "foo",
                "1234",
                "path",
                "/test/1234",
                id="simple",
            ),
            param(
                {"path": "/test/${oc.env:not_found,ZZZ}"},
                None,
                None,
                "path",
                "/test/ZZZ",
                id="not_found_with_default",
            ),
            param(
                {"path": "/test/${oc.env:not_found,a/b}"},
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
        monkeypatch: Any,
        cfg: Any,
        env_name: Optional[str],
        env_val: str,
        key: str,
        expected: Any,
    ) -> None:
        if env_name is not None:
            monkeypatch.setenv(env_name, env_val)

        cfg = OmegaConf.create(cfg)

        assert OmegaConf.select(cfg, key) == expected

    @mark.parametrize(
        ("cfg", "key", "expected"),
        [
            param(
                {"path": "/test/${oc.env:not_found}"},
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
        cfg: Any,
        key: str,
        expected: Any,
    ) -> None:
        cfg = _ensure_container(cfg)

        with expected:
            OmegaConf.select(cfg, key)


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


def test_env_default_none(monkeypatch: Any) -> None:
    monkeypatch.delenv("MYKEY", raising=False)
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, null}"})
    assert c.my_key is None


def test_env_non_str_default(monkeypatch: Any) -> None:
    c = OmegaConf.create({"my_key": "${oc.env:MYKEY, 123}"})

    monkeypatch.setenv("MYKEY", "456")
    assert c.my_key == "456"

    monkeypatch.delenv("MYKEY")
    assert c.my_key == "123"
