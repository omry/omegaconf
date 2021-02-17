import re
from enum import Enum
from typing import Any

import pytest

from omegaconf import DictConfig, ListConfig, OmegaConf
from tests import Color, User


@pytest.mark.parametrize(
    "input_",
    [
        pytest.param([1, 2, 3], id="list"),
        pytest.param([1, 2, {"a": 3}], id="dict_in_list"),
        pytest.param([1, 2, [10, 20]], id="list_in_list"),
        pytest.param({"b": {"b": 10}}, id="dict_in_dict"),
        pytest.param({"b": [False, 1, "2", 3.0, Color.RED]}, id="list_in_dict"),
        pytest.param({"b": DictConfig(content=None)}, id="none_dictconfig"),
        pytest.param({"b": ListConfig(content=None)}, id="none_listconfig"),
        pytest.param({"b": DictConfig(content="???")}, id="missing_dictconfig"),
        pytest.param({"b": ListConfig(content="???")}, id="missing_listconfig"),
    ],
)
def test_to_container_returns_primitives(input_: Any) -> None:
    def assert_container_with_primitives(item: Any) -> None:
        if isinstance(item, list):
            for v in item:
                assert_container_with_primitives(v)
        elif isinstance(item, dict):
            for _k, v in item.items():
                assert_container_with_primitives(v)
        else:
            assert isinstance(item, (int, float, str, bool, type(None), Enum))

    c = OmegaConf.create(input_)
    res = OmegaConf.to_container(c, resolve=True)
    assert_container_with_primitives(res)


@pytest.mark.parametrize(
    "cfg,ex_false,ex_true",
    [
        pytest.param(
            {"user": User(age=7, name="Bond")},
            {"user": {"name": "Bond", "age": 7}},
            {"user": User(age=7, name="Bond")},
        ),
        pytest.param(
            [1, User(age=7, name="Bond")],
            [1, {"name": "Bond", "age": 7}],
            [1, User(age=7, name="Bond")],
        ),
        pytest.param(
            {"users": [User(age=1, name="a"), User(age=2, name="b")]},
            {"users": [{"age": 1, "name": "a"}, {"age": 2, "name": "b"}]},
            {"users": [User(age=1, name="a"), User(age=2, name="b")]},
        ),
    ],
)
def test_exclude_structured_configs(cfg: Any, ex_false: Any, ex_true: Any) -> None:
    cfg = OmegaConf.create(cfg)
    ret1 = OmegaConf.to_container(cfg, exclude_structured_configs=False)
    assert ret1 == ex_false

    ret1 = OmegaConf.to_container(cfg, exclude_structured_configs=True)
    assert ret1 == ex_true


@pytest.mark.parametrize(
    "src, expected, expected_with_resolve",
    [
        pytest.param([], None, None, id="empty_list"),
        pytest.param([1, 2, 3], None, None, id="list"),
        pytest.param([None], None, None, id="list_with_none"),
        pytest.param([1, "${0}", 3], None, [1, 1, 3], id="list_with_inter"),
        pytest.param({}, None, None, id="empty_dict"),
        pytest.param({"foo": "bar"}, None, None, id="dict"),
        pytest.param(
            {"foo": "${bar}", "bar": "zonk"},
            None,
            {"foo": "zonk", "bar": "zonk"},
            id="dict_with_inter",
        ),
        pytest.param({"foo": None}, None, None, id="dict_with_none"),
        pytest.param({"foo": "???"}, None, None, id="dict_missing_value"),
        pytest.param({"foo": None}, None, None, id="dict_none_value"),
        # containers
        pytest.param(
            {"foo": DictConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_dictconfig",
        ),
        pytest.param(
            {"foo": DictConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_dictconfig",
        ),
        pytest.param(
            {"foo": DictConfig(content="${bar}"), "bar": 10},
            {"foo": "${bar}", "bar": 10},
            {"foo": 10, "bar": 10},
            id="dict_inter_dictconfig",
        ),
        pytest.param(
            {"foo": ListConfig(content="???")},
            {"foo": "???"},
            None,
            id="dict_missing_listconfig",
        ),
        pytest.param(
            {"foo": ListConfig(is_optional=True, content=None)},
            {"foo": None},
            None,
            id="dict_none_listconfig",
        ),
        pytest.param(
            {"foo": ListConfig(content="${bar}"), "bar": 10},
            {"foo": "${bar}", "bar": 10},
            {"foo": 10, "bar": 10},
            id="dict_inter_listconfig",
        ),
    ],
)
def test_to_container(src: Any, expected: Any, expected_with_resolve: Any) -> None:
    if expected is None:
        expected = src
    if expected_with_resolve is None:
        expected_with_resolve = expected
    cfg = OmegaConf.create(src)
    container = OmegaConf.to_container(cfg)
    assert container == expected
    container = OmegaConf.to_container(cfg, resolve=True)
    assert container == expected_with_resolve


def test_to_container_invalid_input() -> None:
    with pytest.raises(
        ValueError,
        match=re.escape("Input cfg is not an OmegaConf config object (dict)"),
    ):
        OmegaConf.to_container({})


def test_string_interpolation_with_readonly_parent() -> None:
    cfg = OmegaConf.create({"a": 10, "b": {"c": "hello_${a}"}})
    OmegaConf.set_readonly(cfg, True)
    assert OmegaConf.to_container(cfg, resolve=True) == {
        "a": 10,
        "b": {"c": "hello_10"},
    }


@pytest.mark.parametrize(
    "src,expected",
    [
        pytest.param(DictConfig(content="${bar}"), "${bar}", id="DictConfig"),
        pytest.param(
            OmegaConf.create({"foo": DictConfig(content="${bar}")}),
            {"foo": "${bar}"},
            id="nested_DictConfig",
        ),
    ],
)
def test_to_container_missing_inter_no_resolve(src: Any, expected: Any) -> None:
    res = OmegaConf.to_container(src, resolve=False)
    assert res == expected


class TestEnumToStr:
    """Test the `enum_to_str` argument to the `OmegaConf.to_container function`"""

    @pytest.mark.parametrize(
        "src,enum_to_str,expected",
        [
            pytest.param(
                DictConfig(content={Color.RED: "enum key"}),
                True,
                "RED",
                id="enum_key:convert",
            ),
            pytest.param(
                DictConfig(content={Color.RED: "enum key"}),
                False,
                Color.RED,
                id="enum_key:dont-convert",
            ),
            pytest.param(
                DictConfig(content={123: "int key"}),
                True,
                123,
                id="int_key:T-unaffected",
            ),
            pytest.param(
                DictConfig(content={123: "int key"}),
                False,
                123,
                id="int_key:F-unaffected",
            ),
        ],
    )
    def test_enum_to_str_for_keys(
        self, src: DictConfig, enum_to_str: bool, expected: Any
    ) -> None:
        """Test the enum_to_str argument to the OmegaConf.to_container method."""
        container = OmegaConf.to_container(src, enum_to_str=enum_to_str)
        assert isinstance(container, dict)
        key = list(container.keys())[0]
        assert key == expected
        assert type(key) == type(expected)

    @pytest.mark.parametrize(
        "src,enum_to_str,expected",
        [
            pytest.param(
                DictConfig(content={"enum value": Color.RED}),
                True,
                "RED",
                id="enum_value:convert",
            ),
            pytest.param(
                DictConfig(content={"enum value": Color.RED}),
                False,
                Color.RED,
                id="enum_value:dont-convert",
            ),
            pytest.param(
                DictConfig(content={"int value": 123}),
                True,
                123,
                id="int_value:T-unaffected",
            ),
            pytest.param(
                DictConfig(content={"int value": 123}),
                False,
                123,
                id="int_value:F-unaffected",
            ),
        ],
    )
    def test_enum_to_str_for_values(
        self, src: DictConfig, enum_to_str: bool, expected: Any
    ) -> None:
        """Test the enum_to_str argument to the OmegaConf.to_container method."""
        container = OmegaConf.to_container(src, enum_to_str=enum_to_str)
        assert isinstance(container, dict)
        value = list(container.values())[0]
        assert value == expected
        assert type(value) == type(expected)

    @pytest.mark.parametrize(
        "src,enum_to_str,expected",
        [
            pytest.param(
                ListConfig(content=[Color.RED]),
                True,
                "RED",
                id="List[Enum]:convert",
            ),
            pytest.param(
                ListConfig(content=[Color.RED]),
                False,
                Color.RED,
                id="List[Enum]:dont-convert",
            ),
            pytest.param(
                ListConfig(content=[123]),
                True,
                123,
                id="List[int]:T-unaffected",
            ),
            pytest.param(
                ListConfig(content=[123]),
                False,
                123,
                id="List[int]:F-unaffected",
            ),
        ],
    )
    def test_enum_to_str_for_list(
        self, src: ListConfig, enum_to_str: bool, expected: Any
    ) -> None:
        """Test the enum_to_str argument to the OmegaConf.to_container method."""
        container = OmegaConf.to_container(src, enum_to_str=enum_to_str)
        assert isinstance(container, list)
        value = container[0]
        assert value == expected
        assert type(value) == type(expected)
