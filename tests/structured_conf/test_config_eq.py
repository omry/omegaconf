from typing import Any, List

import pytest

from omegaconf import AnyNode, OmegaConf
from omegaconf.basecontainer import BaseContainer


@pytest.mark.parametrize(  # type: ignore
    "l1,l2",
    [
        # === LISTS ===
        # empty list
        ([], []),
        # simple list
        (["a", 12, "15"], ["a", 12, "15"]),
        # raw vs any
        ([1, 2, 12], [1, 2, AnyNode(12)]),
        # nested empty dict
        ([12, dict()], [12, dict()]),
        # nested dict
        ([12, dict(c=10)], [12, dict(c=10)]),
        # nested list
        ([1, 2, 3, [10, 20, 30]], [1, 2, 3, [10, 20, 30]]),
        # nested list with any
        ([1, 2, 3, [1, 2, AnyNode(3)]], [1, 2, 3, [1, 2, AnyNode(3)]]),
        # === DICTS ==
        # empty
        (dict(), dict()),
        # simple
        (dict(a=12), dict(a=12)),
        # any vs raw
        (dict(a=12), dict(a=AnyNode(12))),
        # nested dict empty
        (dict(a=12, b=dict()), dict(a=12, b=dict())),
        # nested dict
        (dict(a=12, b=dict(c=10)), dict(a=12, b=dict(c=10))),
        # nested list
        (dict(a=12, b=[1, 2, 3]), dict(a=12, b=[1, 2, 3])),
        # nested list with any
        (dict(a=12, b=[1, 2, AnyNode(3)]), dict(a=12, b=[1, 2, AnyNode(3)])),
        # In python 3.6 insert order changes iteration order. this ensures that equality is preserved.
        (dict(a=1, b=2, c=3, d=4, e=5), dict(e=5, b=2, c=3, d=4, a=1)),
        # With interpolations
        ([10, "${0}"], [10, 10]),
        (dict(a=12, b="${a}"), dict(a=12, b=12)),
        # With missing interpolation
        ([10, "${0}"], [10, 10]),
        (dict(a="${missing}"), dict(a="${missing}")),
    ],
)
def test_list_eq(l1: List[Any], l2: List[Any]) -> None:
    c1 = OmegaConf.create(l1)
    c2 = OmegaConf.create(l2)

    def eq(a: Any, b: Any) -> None:
        assert a == b
        assert b == a
        assert not a != b
        assert not b != a

    eq(c1, c2)
    eq(c1, l1)
    eq(c2, l2)


@pytest.mark.parametrize(  # type: ignore
    "input1, input2",
    [
        # Dicts
        (dict(), dict(a=10)),
        ({}, []),
        (dict(a=12), dict(a=13)),
        (dict(a=0), dict(b=0)),
        (dict(a=12), dict(a=AnyNode(13))),
        (dict(a=12, b=dict()), dict(a=13, b=dict())),
        (dict(a=12, b=dict(c=10)), dict(a=13, b=dict(c=10))),
        (dict(a=12, b=[1, 2, 3]), dict(a=12, b=[10, 2, 3])),
        (dict(a=12, b=[1, 2, AnyNode(3)]), dict(a=12, b=[1, 2, AnyNode(30)])),
        # Lists
        ([], [10]),
        ([10], [11]),
        ([12], [AnyNode(13)]),
        ([12, dict()], [13, dict()]),
        ([12, dict(c=10)], [13, dict(c=10)]),
        ([12, [1, 2, 3]], [12, [10, 2, 3]]),
        ([12, [1, 2, AnyNode(3)]], [12, [1, 2, AnyNode(30)]]),
    ],
)
def test_not_eq(input1: Any, input2: Any) -> None:
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def neq(a: Any, b: Any) -> None:
        assert a != b
        assert b != a
        assert not a == b
        assert not b == a

    neq(c1, c2)


# ---
def test_config_eq_mismatch_types() -> None:
    c1 = OmegaConf.create({})
    c2 = OmegaConf.create([])
    assert not BaseContainer._config_eq(c1, c2)
    assert not BaseContainer._config_eq(c2, c1)


def test_dict_not_eq_with_another_class() -> None:
    assert OmegaConf.create({}) != "string"
    assert OmegaConf.create([]) != "string"
