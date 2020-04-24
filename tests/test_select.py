import re
from typing import Any, Optional

import pytest
from pytest import raises

from omegaconf import MissingMandatoryValue, OmegaConf

from . import does_not_raise


@pytest.mark.parametrize("struct", [True, False, None])  # type: ignore
def test_select_key_from_empty(struct: Optional[bool]) -> None:
    c = OmegaConf.create()
    OmegaConf.set_struct(c, struct)
    assert OmegaConf.select(c, "not_there") is None


@pytest.mark.parametrize(  # type: ignore
    "cfg, keys, expected, expectation",
    [
        ({}, "nope", None, does_not_raise()),
        ({}, "not.there", None, does_not_raise()),
        ({}, "still.not.there", None, does_not_raise()),
        ({"c": 1}, "c", 1, does_not_raise()),
        ({"a": {"v": 1}}, "a", {"v": 1}, does_not_raise()),
        ({"a": {"v": 1}}, "a.v", 1, does_not_raise()),
        ({"missing": "???"}, "missing", None, does_not_raise()),
        ([], "0", None, does_not_raise()),
        ([1, "2"], ("0", "1"), (1, "2"), does_not_raise()),
        (
            [1, {"a": 10, "c": ["foo", "bar"]}],
            ("0", "1.a", "1.b", "1.c.0", "1.c.1"),
            (1, 10, None, "foo", "bar"),
            does_not_raise(),
        ),
        ([1, 2, 3], "a", None, raises(TypeError)),
        (
            {"a": {"v": 1}, "b": {"v": 1}},
            "",
            {"a": {"v": 1}, "b": {"v": 1}},
            does_not_raise(),
        ),
        (
            {"dict": {"one": 1}, "foo": "one=${dict.one}"},
            "foo",
            "one=1",
            does_not_raise(),
        ),
        (
            {"dict": {"foo": "one=${one}"}, "one": 1},
            "dict.foo",
            "one=1",
            does_not_raise(),
        ),
        ({"dict": {"foo": "one=${foo:1}"}}, "dict.foo", "one=_1_", does_not_raise()),
    ],
)
def test_select(
    restore_resolvers: Any, cfg: Any, keys: Any, expected: Any, expectation: Any
) -> None:
    if not isinstance(keys, (tuple, list)):
        keys = [keys]
    if not isinstance(expected, (tuple, list)):
        expected = [expected]
    OmegaConf.register_resolver("foo", lambda x: f"_{x}_")

    c = OmegaConf.create(cfg)
    with expectation:
        for idx, key in enumerate(keys):
            assert OmegaConf.select(c, key) == expected[idx]


def test_select_from_dict() -> None:
    c = OmegaConf.create({"missing": "???"})
    with pytest.raises(MissingMandatoryValue):
        OmegaConf.select(c, "missing", throw_on_missing=True)
    assert OmegaConf.select(c, "missing", throw_on_missing=False) is None
    assert OmegaConf.select(c, "missing") is None


def test_select_deprecated() -> None:
    c = OmegaConf.create({"foo": "bar"})
    with pytest.warns(
        expected_warning=UserWarning,
        match=re.escape("select() is deprecated, use OmegaConf.select(). (Since 2.0)"),
    ):
        c.select("foo")
