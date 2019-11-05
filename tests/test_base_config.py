import copy

import pytest

from omegaconf import (
    OmegaConf,
    IntegerNode,
    StringNode,
    ValidationError,
    ListConfig,
    DictConfig,
    ReadonlyConfigError,
    read_write,
    open_dict,
    flag_override,
)
from . import does_not_raise


@pytest.mark.parametrize(
    "input_, key, value, expected",
    [
        # dict
        (dict(), "foo", 10, dict(foo=10)),
        (dict(), "foo", IntegerNode(10), dict(foo=10)),
        (dict(foo=5), "foo", IntegerNode(10), dict(foo=10)),
        # changing type of a node
        (dict(foo=StringNode("str")), "foo", IntegerNode(10), dict(foo=10)),
        # list
        ([0], 0, 10, [10]),
        (["a", "b", "c"], 1, 10, ["a", 10, "c"]),
        ([1, 2], 1, IntegerNode(10), [1, 10]),
        ([1, IntegerNode(2)], 1, IntegerNode(10), [1, 10]),
        # changing type of a node
        ([1, StringNode("str")], 1, IntegerNode(10), [1, 10]),
    ],
)
def test_set_value(input_, key, value, expected):
    c = OmegaConf.create(input_)
    c[key] = value
    assert c == expected


@pytest.mark.parametrize(
    "input_, key, value",
    [
        # dict
        (dict(foo=IntegerNode(10)), "foo", "str"),
        # list
        ([1, IntegerNode(10)], 1, "str"),
    ],
)
def test_set_value_validation_fail(input_, key, value):
    c = OmegaConf.create(input_)
    with pytest.raises(ValidationError):
        c[key] = value


@pytest.mark.parametrize(
    "input_",
    [
        [1, 2, 3],
        [1, 2, dict(a=3)],
        [1, 2, [10, 20]],
        dict(b=dict(b=10)),
        dict(b=[1, 2, 3]),
    ],
)
def test_to_container_returns_primitives(input_):
    def assert_container_with_primitives(container):
        if isinstance(container, list):
            for v in container:
                assert_container_with_primitives(v)
        elif isinstance(container, dict):
            for _k, v in container.items():
                assert_container_with_primitives(v)
        else:
            assert isinstance(container, (int, str, bool))

    c = OmegaConf.create(input_)
    res = c.to_container(resolve=True)
    assert_container_with_primitives(res)


@pytest.mark.parametrize(
    "input_, is_empty", [([], True), ({}, True), ([1, 2], False), (dict(a=10), False)]
)
def test_empty(input_, is_empty):
    c = OmegaConf.create(input_)
    assert c.is_empty() == is_empty


@pytest.mark.parametrize(
    "input_",
    [
        [],
        {},
        [1, 2, 3],
        [1, 2, dict(a=3)],
        [1, 2, [10, 20]],
        dict(b=dict(b=10)),
        dict(b=[1, 2, 3]),
    ],
)
def test_repr(input_):
    c = OmegaConf.create(input_)
    assert repr(input_) == repr(c)


@pytest.mark.parametrize(
    "input_",
    [
        [],
        {},
        [1, 2, 3],
        [1, 2, dict(a=3)],
        [1, 2, [10, 20]],
        dict(b=dict(b=10)),
        dict(b=[1, 2, 3]),
    ],
)
def test_str(input_):
    c = OmegaConf.create(input_)
    assert str(input_) == str(c)


@pytest.mark.parametrize("flag", ["readonly", "struct"])
def test_flag_dict(flag):
    c = OmegaConf.create()
    assert not c._get_flag(flag)
    c._set_flag(flag, True)
    assert c._get_flag(flag)
    c._set_flag(flag, False)
    assert not c._get_flag(flag)
    c._set_flag(flag, None)
    assert not c._get_flag(flag)


@pytest.mark.parametrize("flag", ["readonly", "struct"])
def test_freeze_nested_dict(flag):
    c = OmegaConf.create(dict(a=dict(b=2)))
    assert not c._get_flag(flag)
    assert not c.a._get_flag(flag)
    c._set_flag(flag, True)
    assert c._get_flag(flag)
    assert c.a._get_flag(flag)
    c._set_flag(flag, False)
    assert not c._get_flag(flag)
    assert not c.a._get_flag(flag)
    c._set_flag(flag, None)
    assert not c._get_flag(flag)
    assert not c.a._get_flag(flag)
    c.a._set_flag(flag, True)
    assert not c._get_flag(flag)
    assert c.a._get_flag(flag)


copy_list = [
    [],
    [1, 2, 3],
    dict(),
    dict(a=10),
]


@pytest.mark.parametrize("src", copy_list)
def test_deepcopy(src):
    c1 = OmegaConf.create(src)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        c2.append(1000)
    elif isinstance(c2, DictConfig):
        c2.foo = "bar"
    assert c1 != c2


@pytest.mark.parametrize("src", copy_list)
def test_deepcopy_readonly(src):
    c1 = OmegaConf.create(src)
    OmegaConf.set_readonly(c1, True)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        with pytest.raises(ReadonlyConfigError):
            c2.append(1000)
    elif isinstance(c2, DictConfig):
        with pytest.raises(ReadonlyConfigError):
            c2.foo = "bar"
    assert c1 == c2


@pytest.mark.parametrize("src", copy_list)
def test_deepcopy_struct(src):
    c1 = OmegaConf.create(src)
    OmegaConf.set_struct(c1, True)
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    if isinstance(c2, ListConfig):
        c2.append(1000)
    elif isinstance(c2, DictConfig):
        with pytest.raises(KeyError):
            c2.foo = "bar"


def test_deepcopy_after_del():
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(foo=[1, 2, 3], bar=10))
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    del c1["foo"]
    c3 = copy.deepcopy(c1)
    assert c1 == c3


def test_deepcopy_with_interpolation():
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(a=dict(b="${c}"), c=10))
    assert c1.a.b == 10
    c2 = copy.deepcopy(c1)
    assert c2.a.b == 10


# Yes, there was a bug that was a combination of an interaction between the three
def test_deepcopy_and_merge_and_flags():
    c1 = OmegaConf.create(
        {"dataset": {"name": "imagenet", "path": "/datasets/imagenet"}, "defaults": []}
    )
    OmegaConf.set_struct(c1, True)
    c2 = copy.deepcopy(c1)
    with pytest.raises(KeyError):
        OmegaConf.merge(c2, OmegaConf.from_dotlist(["dataset.bad_key=yes"]))


@pytest.mark.parametrize(
    "src, flag_name, flag_value, func, expectation",
    [
        (
            {},
            "struct",
            False,
            lambda c: c.__setitem__("foo", 1),
            pytest.raises(KeyError),
        ),
        (
            {},
            "readonly",
            False,
            lambda c: c.__setitem__("foo", 1),
            pytest.raises(ReadonlyConfigError),
        ),
    ],
)
def test_flag_override(src, flag_name, flag_value, func, expectation):
    c = OmegaConf.create(src)
    c._set_flag(flag_name, True)
    with expectation:
        func(c)

    with does_not_raise():
        with flag_override(c, flag_name, flag_value):
            func(c)


@pytest.mark.parametrize(
    "src, func, expectation",
    [
        ({}, lambda c: c.__setitem__("foo", 1), pytest.raises(ReadonlyConfigError)),
        ([], lambda c: c.append(1), pytest.raises(ReadonlyConfigError)),
    ],
)
def test_read_write_override(src, func, expectation):
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)

    with expectation:
        func(c)

    with does_not_raise():
        with read_write(c):
            func(c)


@pytest.mark.parametrize(
    "string, tokenized",
    [
        ("dog,cat", ["dog", "cat"]),
        ("dog\,cat\ ", ["dog,cat "]),
        ("dog,\ cat", ["dog", " cat"]),
        ("\ ,cat", [" ", "cat"]),
        ("dog, cat", ["dog", "cat"]),
        ("dog, ca t", ["dog", "ca t"]),
        ("dog, cat", ["dog", "cat"]),
        ("whitespace\ , before comma", ["whitespace ", "before comma"]),
        (None, []),
        ("", []),
        ("no , escape", ["no", "escape"]),
    ],
)
def test_tokenize_with_escapes(string, tokenized):
    assert OmegaConf._tokenize_args(string) == tokenized


@pytest.mark.parametrize(
    "src, func, expectation",
    [({}, lambda c: c.__setattr__("foo", 1), pytest.raises(KeyError))],
)
def test_struct_override(src, func, expectation):
    c = OmegaConf.create(src)
    OmegaConf.set_struct(c, True)

    with expectation:
        func(c)

    with does_not_raise():
        with open_dict(c):
            func(c)


@pytest.mark.parametrize(
    "flag_name,ctx", [("struct", open_dict), ("readonly", read_write)]
)
def test_open_dict_restore(flag_name, ctx):
    """
    Tests that internal flags are restored properly when applying context on a child node
    """
    cfg = OmegaConf.create({"foo": {"bar": 10}})
    cfg._set_flag(flag_name, True)
    assert cfg._get_node_flag(flag_name)
    assert not cfg.foo._get_node_flag(flag_name)
    with ctx(cfg.foo):
        cfg.foo.bar = 20
    assert cfg._get_node_flag(flag_name)
    assert not cfg.foo._get_node_flag(flag_name)
