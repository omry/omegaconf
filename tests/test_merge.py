import pytest
from dataclasses import dataclass, field
from typing import Dict

from omegaconf import OmegaConf, nodes, MISSING


@dataclass
class User:
    name: str = MISSING
    age: int = MISSING


@dataclass
class Users:
    name2user: Dict[str, User] = field(default_factory=lambda: {})


@pytest.mark.parametrize(
    "inputs, expected",
    [
        # dictionaries
        ((dict(), dict(a=1)), dict(a=1)),
        ((dict(a=None), dict(b=None)), dict(a=None, b=None)),
        ((dict(a=1), dict(b=2)), dict(a=1, b=2)),
        ((dict(a=dict(a1=1, a2=2)), dict(a=dict(a1=2))), dict(a=dict(a1=2, a2=2))),
        ((dict(a=1, b=2), dict(b=3)), dict(a=1, b=3)),
        ((dict(a=1, b=2), dict(b=dict(c=3))), dict(a=1, b=dict(c=3))),
        ((dict(b=dict(c=1)), dict(b=1)), dict(b=1)),
        ((dict(list=[1, 2, 3]), dict(list=[4, 5, 6])), dict(list=[4, 5, 6])),
        ((dict(a=1), dict(a=nodes.IntegerNode(10))), dict(a=10)),
        ((dict(a=1), dict(a=nodes.IntegerNode(10))), dict(a=nodes.IntegerNode(10))),
        ((dict(a=nodes.IntegerNode(10)), dict(a=1)), dict(a=1)),
        ((dict(a=nodes.IntegerNode(10)), dict(a=1)), dict(a=nodes.IntegerNode(1))),
        # lists
        (([1, 2, 3], [4, 5, 6]), [4, 5, 6]),
        (([[1, 2, 3]], [[4, 5, 6]]), [[4, 5, 6]]),
        (([1, 2, dict(a=10)], [4, 5, dict(b=20)]), [4, 5, dict(b=20)]),
        # Interpolations
        (
            (dict(data=123, reference="${data}"), dict(data=456)),
            dict(data=456, reference=456),
        ),
        ((dict(missing="${data}"), dict(missing=123)), dict(missing=123)),
        (
            (dict(missing=123), dict(missing="${data}"), dict(missing=456)),
            dict(missing=456),
        ),
        # Structured configs
        (({"user": User}, {}), {"user": User(name=MISSING, age=MISSING)}),
        (({"user": User}, {"user": {}}), {"user": User(name=MISSING, age=MISSING)}),
        (
            ({"user": User}, {"user": {"name": "Joe"}}),
            {"user": User(name="Joe", age=MISSING)},
        ),
        (
            ({"user": User}, {"user": {"name": "Joe", "age": 10}}),
            {"user": User(name="Joe", age=10)},
        ),
        ([{"users": Users}], {"users": {"name2user": {}}}),
        ((Users,), {"name2user": {}}),
        ((Users, {"name2user": {}}), {"name2user": {}}),
        (
            (Users, {"name2user": {"joe": User}}),
            {"name2user": {"joe": {"name": MISSING, "age": MISSING}}},
        ),
        (
            (Users, {"name2user": {"joe": User(name="joe")}}),
            {"name2user": {"joe": {"name": "joe", "age": MISSING}}},
        ),
        (
            (Users, {"name2user": {"joe": {"name": "joe"}}}),
            {"name2user": {"joe": {"name": "joe", "age": MISSING}}},
        ),
    ],
)
def test_merge(inputs, expected):
    configs = [OmegaConf.create(c) for c in inputs]
    merged = OmegaConf.merge(*configs)
    assert merged == expected
    # test input configs are not changed.
    # Note that converting to container without resolving to avoid resolution errors while comparing
    for i in range(len(inputs)):
        input_i = OmegaConf.create(inputs[i])
        orig = OmegaConf.to_container(input_i, resolve=False)
        merged = OmegaConf.to_container(configs[i], resolve=False)
        assert orig == merged


# like above but don't verify merge does not change because even eq does not work no tuples because we convert
# them to a list
@pytest.mark.parametrize("a_, b_, expected", [((1, 2, 3), (4, 5, 6), [4, 5, 6])])
def test_merge_no_eq_verify(a_, b_, expected):
    a = OmegaConf.create(a_)
    b = OmegaConf.create(b_)
    c = OmegaConf.merge(a, b)
    # verify merge result is expected
    assert expected == c


def test_merge_with_1():
    a = OmegaConf.create()
    b = OmegaConf.create(dict(a=1, b=2))
    a.merge_with(b)
    assert a == b


def test_merge_with_2():
    a = OmegaConf.create()
    a.inner = {}
    b = OmegaConf.create(
        """
    a : 1
    b : 2
    """
    )
    a.inner.merge_with(b)
    assert a.inner == b


def test_3way_dict_merge():
    c1 = OmegaConf.create("{a: 1, b: 2}")
    c2 = OmegaConf.create("{b: 3}")
    c3 = OmegaConf.create("{a: 2, c: 3}")
    c4 = OmegaConf.merge(c1, c2, c3)
    assert {"a": 2, "b": 3, "c": 3} == c4


def test_merge_list_list():
    a = OmegaConf.create([1, 2, 3])
    b = OmegaConf.create([4, 5, 6])
    a.merge_with(b)
    assert a == b


@pytest.mark.parametrize(
    "base, merge, exception",
    [
        ({}, [], TypeError),
        ([], {}, TypeError),
        ([1, 2, 3], None, ValueError),
        (dict(a=10), None, ValueError),
    ],
)
def test_merge_error(base, merge, exception):
    base = OmegaConf.create(base)
    merge = None if merge is None else OmegaConf.create(merge)
    with pytest.raises(exception):
        OmegaConf.merge(base, merge)


def test_parent_maintained():
    c1 = OmegaConf.create(dict(a=dict(b=10)))
    c2 = OmegaConf.create(dict(aa=dict(bb=100)))
    c3 = OmegaConf.merge(c1, c2)
    assert id(c1.a.parent) == id(c1)
    assert id(c2.aa.parent) == id(c2)
    assert id(c3.a.parent) == id(c3)
