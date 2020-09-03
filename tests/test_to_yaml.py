import re
from textwrap import dedent
from typing import Any

import pytest

from omegaconf import DictConfig, EnumNode, ListConfig, OmegaConf, _utils

from . import Enum1, User


@pytest.mark.parametrize(  # type: ignore
    "input_, expected",
    [
        (["item1", "item2", {"key3": "value3"}], "- item1\n- item2\n- key3: value3\n"),
        ({"hello": "world", "list": [1, 2]}, "hello: world\nlist:\n- 1\n- 2\n"),
    ],
)
def test_to_yaml(input_: Any, expected: str) -> None:
    c = OmegaConf.create(input_)
    assert expected == OmegaConf.to_yaml(c)
    assert OmegaConf.create(OmegaConf.to_yaml(c)) == c


@pytest.mark.parametrize(  # type: ignore
    "input_, expected",
    [
        (["item一", "item二", dict(key三="value三")], "- item一\n- item二\n- key三: value三\n"),
        (dict(你好="世界", list=[1, 2]), "你好: 世界\nlist:\n- 1\n- 2\n"),
    ],
)
def test_to_yaml_unicode(input_: Any, expected: str) -> None:
    c = OmegaConf.create(input_)
    assert expected == OmegaConf.to_yaml(c)
    assert OmegaConf.create(OmegaConf.to_yaml(c)) == c


@pytest.mark.parametrize(  # type: ignore
    "input_, expected, type_",
    [
        (["1", 1], "- '1'\n- 1\n", int),
        (["10e2", "1.0", 1.0], "- '10e2'\n- '1.0'\n- 1.0\n", float),
        (_utils.YAML_BOOL_TYPES, None, bool),
    ],
)
def test_to_yaml_string_primitive_types_list(
    input_: Any, expected: str, type_: type
) -> None:
    if type_ == bool:
        for t in input_:
            c = OmegaConf.create([t, 1])
            expected = "- '%s'\n- 1\n" % t
            assert OmegaConf.to_yaml(c) == expected

    else:
        c = OmegaConf.create(input_)
        assert OmegaConf.to_yaml(c) == expected


@pytest.mark.parametrize(  # type: ignore
    "input_, expected, type_",
    [
        ({"b": "1", "a": 1}, "b: '1'\na: 1\n", int),
        ({"b": "10e2", "a": "1.0", "c": 1.0}, "b: '10e2'\na: '1.0'\nc: 1.0\n", float),
        (_utils.YAML_BOOL_TYPES, None, bool),
    ],
)
def test_to_yaml_string_primitive_types_dict(
    input_: Any, expected: str, type_: type
) -> None:
    if type_ == bool:
        for t in input_:
            c = OmegaConf.create({"b": t, "a": 1})
            assert OmegaConf.to_yaml(c) == "b: '%s'\na: 1\n" % t
    else:
        c = OmegaConf.create(input_)
        assert OmegaConf.to_yaml(c) == expected


@pytest.mark.parametrize(  # type: ignore
    "input_, resolve, expected",
    [
        (dict(a1="${ref}", ref="bar"), True, "bar"),
        (dict(a1="${ref}", ref="bar"), False, "changed"),
        ([100, "${0}"], True, 100),
        ([100, "${0}"], False, 1000),
    ],
)
def test_to_yaml_resolve(input_: Any, resolve: bool, expected: int) -> None:
    c = OmegaConf.create(input_)
    # without resolve, references are preserved
    yaml_str = OmegaConf.to_yaml(c, resolve=resolve)
    c2 = OmegaConf.create(yaml_str)
    assert isinstance(c2, ListConfig) or isinstance(c2, DictConfig)
    if isinstance(c2, DictConfig):
        assert c2.a1 == "bar"
        c2.ref = "changed"
        assert c2.a1 == expected
    else:
        c2[0] = 1000
        assert c2[1] == expected


def test_to_yaml_sort_keys() -> None:
    c = OmegaConf.create({"b": 2, "a": 1})
    # keys are not sorted by default
    assert OmegaConf.to_yaml(c) == "b: 2\na: 1\n"
    c = OmegaConf.create({"b": 2, "a": 1})
    assert OmegaConf.to_yaml(c, sort_keys=True) == "a: 1\nb: 2\n"


def test_to_yaml_with_enum() -> None:
    cfg = OmegaConf.create()
    assert isinstance(cfg, DictConfig)
    cfg.foo = EnumNode(Enum1)
    cfg.foo = Enum1.FOO

    expected = """foo: FOO
"""
    s = OmegaConf.to_yaml(cfg)
    assert s == expected
    assert (
        OmegaConf.merge({"foo": EnumNode(Enum1, value="???")}, OmegaConf.create(s))
        == cfg
    )


def test_pretty_deprecated() -> None:
    c = OmegaConf.create({"foo": "bar"})
    with pytest.warns(
        expected_warning=UserWarning,
        match=re.escape(
            dedent(
                """\
            cfg.pretty() is deprecated and will be removed in a future version.
            Use OmegaConf.to_yaml(cfg)
            """,
            )
        ),
    ):
        assert c.pretty() == "foo: bar\n"


@pytest.mark.parametrize(  # type: ignore
    "user",
    [
        User(name="Bond", age=7),
        OmegaConf.structured(User(name="Bond", age=7)),
        {"name": "Bond", "age": 7},
    ],
)
def test_structured_configs(user: User) -> None:
    expected = dedent(
        """\
                name: Bond
                age: 7
                """
    )
    assert OmegaConf.to_yaml(user) == expected
