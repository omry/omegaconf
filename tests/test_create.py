"""Testing for OmegaConf"""
import re
import sys

import pytest

from omegaconf import OmegaConf
from . import IllegalType


@pytest.mark.parametrize(
    "input_,expected",
    [
        # simple value
        ("hello", {"hello": None}),
        # simple key:value"
        ("hello: world", {"hello": "world"}),
        (dict(hello=dict(a=2)), {"hello": {"a": 2}}),
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
    ],
)
def test_create_value(input_, expected):
    assert expected == OmegaConf.create(input_)


def test_create_from_cli():
    sys.argv = ["program.py", "a=1", "b.c=2"]
    c = OmegaConf.from_cli()
    assert {"a": 1, "b": {"c": 2}} == c


def test_cli_passing():
    args_list = ["a=1", "b.c=2"]
    c = OmegaConf.from_cli(args_list)
    assert {"a": 1, "b": {"c": 2}} == c


@pytest.mark.parametrize(
    "input_, expected", [(["a=1", "b.c=2"], dict(a=1, b=dict(c=2)))]
)
def test_dotlist(input_, expected):
    c = OmegaConf.from_dotlist(input_)
    assert c == expected


def test_create_list_with_illegal_value_idx0():
    with pytest.raises(ValueError, match=re.escape("key [0]")):
        OmegaConf.create([IllegalType()])


def test_create_list_with_illegal_value_idx1():
    with pytest.raises(ValueError, match=re.escape("key [1]")):
        OmegaConf.create([1, IllegalType(), 3])


def test_create_dict_with_illegal_value():
    with pytest.raises(ValueError, match=re.escape("key a")):
        OmegaConf.create(dict(a=IllegalType()))


# TODO: improve exception message to contain full key a.b
# https://github.com/omry/omegaconf/issues/14
def test_create_nested_dict_with_illegal_value():
    with pytest.raises(ValueError, match=re.escape("key b")):
        OmegaConf.create(dict(a=dict(b=IllegalType())))


def test_create_empty__deprecated():
    assert OmegaConf.empty() == {}


def test_create_from_string__deprecated():
    s = "hello: world"
    c = OmegaConf.from_string(s)
    assert {"hello": "world"} == c


def test_create_from_dict__deprecated():
    src = dict(a=1, b=2)
    c = OmegaConf.from_dict(src)
    assert c == src


def test_create_from_list__deprecated():
    src = [1, 2, 3, 4]
    c = OmegaConf.from_list(src)
    assert c == src


def test_create_from_oc():
    c = OmegaConf.create(
        {"a": OmegaConf.create([1, 2, 3]), "b": OmegaConf.create({"c": 10})}
    )
    assert c == {"a": [1, 2, 3], "b": {"c": 10}}
