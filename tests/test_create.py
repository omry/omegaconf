"""Testing for OmegaConf"""
import re
import sys
from typing import Any, Dict, List

import pytest
import yaml

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import UnsupportedValueType

from . import ConcretePlugin, IllegalType, Plugin


@pytest.mark.parametrize(  # type: ignore
    "input_,expected",
    [
        # No content
        (None, None),
        # empty
        ({}, {}),
        # simple value
        ("hello", {"hello": None}),
        # simple key:value"
        ("hello: world", {"hello": "world"}),
        ({"hello": {"a": 2}}, {"hello": {"a": 2}}),
        # empty input
        ("", {}),
        # list value
        ([1, 2], [1, 2]),
        # For simplicity, tuples are converted to lists.
        ((1, 2), [1, 2]),
        # dict 1
        ({"a": 2, "b": 10}, {"a": 2, "b": 10}),
        # dict 2
        (dict(a=2, b=10), dict(a=2, b=10)),
        # nested dict
        (
            {"a": 2, "b": {"c": {"f": 1}, "d": {}}},
            {"a": 2, "b": {"c": {"f": 1}, "d": {}}},
        ),
        ({"a": None}, {"a": None}),
        ({"foo": "${missing}"}, {"foo": "${missing}"}),
        (OmegaConf.create({"foo": "${missing}"}), {"foo": "${missing}"}),
        (OmegaConf.create(), {}),
        (OmegaConf.create({}), {}),
        (OmegaConf.create([]), []),
        (OmegaConf.create({"foo": OmegaConf.create([])}), {"foo": []}),
        (OmegaConf.create([OmegaConf.create({})]), [{}]),  # type: ignore
    ],
)
def test_create_value(input_: Any, expected: Any) -> None:
    assert OmegaConf.create(input_) == expected


def test_create_from_cli() -> None:
    sys.argv = ["program.py", "a=1", "b.c=2"]
    c = OmegaConf.from_cli()
    assert {"a": 1, "b": {"c": 2}} == c


def test_cli_passing() -> None:
    args_list = ["a=1", "b.c=2"]
    c = OmegaConf.from_cli(args_list)
    assert {"a": 1, "b": {"c": 2}} == c


@pytest.mark.parametrize(  # type: ignore
    "input_,expected",
    [
        # simple
        (["a=1", "b.c=2"], dict(a=1, b=dict(c=2))),
        # string
        (["a=hello", "b=world"], dict(a="hello", b="world")),
        # date-formatted string
        (["my_date=2019-12-11"], dict(my_date="2019-12-11")),
    ],
)
def test_dotlist(input_: List[str], expected: Dict[str, Any]) -> None:
    c = OmegaConf.from_dotlist(input_)
    assert c == expected


def test_create_list_with_illegal_value_idx0() -> None:
    with pytest.raises(UnsupportedValueType, match=re.escape("key: [0]")):
        OmegaConf.create([IllegalType()])


def test_create_list_with_illegal_value_idx1() -> None:
    lst = [1, IllegalType(), 3]
    with pytest.raises(UnsupportedValueType, match=re.escape("key: [1]")):
        OmegaConf.create(lst)


def test_create_dict_with_illegal_value() -> None:
    with pytest.raises(UnsupportedValueType, match=re.escape("key: a")):
        OmegaConf.create({"a": IllegalType()})


def test_create_nested_dict_with_illegal_value() -> None:
    with pytest.raises(ValueError, match=re.escape("key: a.b")):
        OmegaConf.create({"a": {"b": IllegalType()}})


def test_create_from_oc() -> None:
    c = OmegaConf.create(
        {"a": OmegaConf.create([1, 2, 3]), "b": OmegaConf.create({"c": 10})}
    )
    assert c == {"a": [1, 2, 3], "b": {"c": 10}}


def test_create_from_oc_with_flags() -> None:
    c1 = OmegaConf.create({"foo": "bar"})
    OmegaConf.set_struct(c1, True)
    c2 = OmegaConf.create(c1)
    assert c1 == c2
    assert c1._metadata.flags == c2._metadata.flags


def test_create_from_dictconfig_preserves_metadata() -> None:
    cfg1 = DictConfig(ref_type=Plugin, is_optional=False, content=ConcretePlugin)
    OmegaConf.set_struct(cfg1, True)
    OmegaConf.set_readonly(cfg1, True)
    cfg2 = OmegaConf.create(cfg1)
    assert cfg1 == cfg2
    assert cfg1._metadata == cfg2._metadata


def test_create_from_listconfig_preserves_metadata() -> None:
    cfg1 = ListConfig(element_type=int, is_optional=False, content=[1, 2, 3])
    OmegaConf.set_struct(cfg1, True)
    OmegaConf.set_readonly(cfg1, True)
    cfg2 = OmegaConf.create(cfg1)
    assert cfg1 == cfg2
    assert cfg1._metadata == cfg2._metadata


@pytest.mark.parametrize("node", [({"bar": 10}), ([1, 2, 3])])  # type: ignore
def test_create_node_parent_retained_on_create(node: Any) -> None:
    cfg1 = OmegaConf.create({"foo": node})
    cfg2 = OmegaConf.create({"zonk": cfg1.foo})
    assert cfg2 == {"zonk": node}
    assert cfg1.foo._get_parent() == cfg1


def test_create_unmodified_loader() -> None:
    cfg = OmegaConf.create("gitrev: 100e100")
    yaml_cfg = yaml.load("gitrev: 100e100", Loader=yaml.loader.SafeLoader)
    assert cfg.gitrev == 1e102
    assert yaml_cfg["gitrev"] == "100e100"
