import copy
from typing import Any, Dict, List, Union

import pytest

from omegaconf import (
    MISSING,
    Container,
    DictConfig,
    IntegerNode,
    ListConfig,
    OmegaConf,
    ReadonlyConfigError,
    StringNode,
    ValidationError,
    flag_override,
    open_dict,
    read_write,
)

from . import does_not_raise


@pytest.mark.parametrize(  # type: ignore
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
def test_set_value(
    input_: Any, key: Union[str, int], value: Any, expected: Any
) -> None:
    c = OmegaConf.create(input_)
    c[key] = value
    assert c == expected


@pytest.mark.parametrize(  # type: ignore
    "input_, key, value",
    [
        # dict
        (dict(foo=IntegerNode(10)), "foo", "str"),
        # list
        ([1, IntegerNode(10)], 1, "str"),
    ],
)
def test_set_value_validation_fail(input_: Any, key: Any, value: Any) -> None:
    c = OmegaConf.create(input_)
    with pytest.raises(ValidationError):
        c[key] = value


@pytest.mark.parametrize(  # type: ignore
    "input_, key, value",
    [
        # dict
        (dict(foo=IntegerNode(10)), "foo", StringNode("str")),
        # list
        ([1, IntegerNode(10)], 1, StringNode("str")),
    ],
)
def test_replace_value_node_type_with_another(
    input_: Any, key: Any, value: Any
) -> None:
    c = OmegaConf.create(input_)
    c[key] = value
    assert c[key] == value
    assert c[key] == value.value()


@pytest.mark.parametrize(  # type: ignore
    "input_",
    [
        [1, 2, 3],
        [1, 2, dict(a=3)],
        [1, 2, [10, 20]],
        dict(b=dict(b=10)),
        dict(b=[1, 2, 3]),
    ],
)
def test_to_container_returns_primitives(input_: Any) -> None:
    def assert_container_with_primitives(container: Any) -> None:
        if isinstance(container, list):
            for v in container:
                assert_container_with_primitives(v)
        elif isinstance(container, dict):
            for _k, v in container.items():
                assert_container_with_primitives(v)
        else:
            assert isinstance(container, (int, str, bool))

    c = OmegaConf.create(input_)
    res = OmegaConf.to_container(c, resolve=True)
    assert_container_with_primitives(res)

    # Test deprecated API
    res = c.to_container(resolve=True)
    assert_container_with_primitives(res)


@pytest.mark.parametrize(  # type: ignore
    "input_, is_empty", [([], True), ({}, True), ([1, 2], False), (dict(a=10), False)]
)
def test_empty(input_: Any, is_empty: bool) -> None:
    c = OmegaConf.create(input_)
    assert c.is_empty() == is_empty


@pytest.mark.parametrize(  # type: ignore
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
def test_repr(input_: Any) -> None:
    c = OmegaConf.create(input_)
    assert repr(input_) == repr(c)


@pytest.mark.parametrize(  # type: ignore
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
def test_str(input_: Any) -> None:
    c = OmegaConf.create(input_)
    assert str(input_) == str(c)


@pytest.mark.parametrize("flag", ["readonly", "struct"])  # type: ignore
def test_flag_dict(flag: str) -> None:
    c = OmegaConf.create()
    assert c._get_flag(flag) is None
    c._set_flag(flag, True)
    assert c._get_flag(flag) is True
    c._set_flag(flag, False)
    assert not c._get_flag(flag) is True
    c._set_flag(flag, None)
    assert c._get_flag(flag) is None


@pytest.mark.parametrize("flag", ["readonly", "struct"])  # type: ignore
def test_freeze_nested_dict(flag: str) -> None:
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


@pytest.mark.parametrize("src", [[], [1, 2, 3], dict(), dict(a=10)])
class TestDeepCopy:
    def test_deepcopy(self, src: Any) -> None:
        c1 = OmegaConf.create(src)
        c2 = copy.deepcopy(c1)
        assert c1 == c2
        if isinstance(c2, ListConfig):
            c2.append(1000)
        elif isinstance(c2, DictConfig):
            c2.foo = "bar"
        assert c1 != c2

    def test_deepcopy_readonly(self, src: Any) -> None:
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

    def test_deepcopy_struct(self, src: Any) -> None:
        c1 = OmegaConf.create(src)
        OmegaConf.set_struct(c1, True)
        c2 = copy.deepcopy(c1)
        assert c1 == c2
        if isinstance(c2, ListConfig):
            c2.append(1000)
        elif isinstance(c2, DictConfig):
            with pytest.raises(AttributeError):
                c2.foo = "bar"


def test_deepcopy_after_del() -> None:
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(foo=[1, 2, 3], bar=10))
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    del c1["foo"]
    c3 = copy.deepcopy(c1)
    assert c1 == c3


def test_deepcopy_with_interpolation() -> None:
    c1 = OmegaConf.create(dict(a=dict(b="${c}"), c=10))
    assert c1.a.b == 10
    c2 = copy.deepcopy(c1)
    assert c2.a.b == 10


# Yes, there was a bug that was a combination of an interaction between the three
def test_deepcopy_and_merge_and_flags() -> None:
    c1 = OmegaConf.create(
        {"dataset": {"name": "imagenet", "path": "/datasets/imagenet"}, "defaults": []}
    )
    OmegaConf.set_struct(c1, True)
    c2 = copy.deepcopy(c1)
    with pytest.raises(AttributeError):
        OmegaConf.merge(c2, OmegaConf.from_dotlist(["dataset.bad_key=yes"]))


@pytest.mark.parametrize(  # type: ignore
    "cfg",
    [
        ListConfig(content=[], element_type=int),
        DictConfig(content={}, element_type=int),
    ],
)
def test_deepcopy_preserves_container_type(cfg: Container) -> None:
    cp = copy.deepcopy(cfg)
    assert cp.__dict__["_element_type"] == cfg.__dict__["_element_type"]


@pytest.mark.parametrize(  # type: ignore
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
            "struct",
            False,
            lambda c: c.__setattr__("foo", 1),
            pytest.raises(AttributeError),
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
def test_flag_override(
    src: Dict[str, Any], flag_name: str, flag_value: bool, func: Any, expectation: Any
) -> None:
    c = OmegaConf.create(src)
    c._set_flag(flag_name, True)
    with expectation:
        func(c)

    with does_not_raise():
        with flag_override(c, flag_name, flag_value):
            func(c)


@pytest.mark.parametrize(  # type: ignore
    "src, func, expectation",
    [
        ({}, lambda c: c.__setitem__("foo", 1), pytest.raises(ReadonlyConfigError)),
        ([], lambda c: c.append(1), pytest.raises(ReadonlyConfigError)),
    ],
)
def test_read_write_override(src: Any, func: Any, expectation: Any) -> None:
    c = OmegaConf.create(src)
    OmegaConf.set_readonly(c, True)

    with expectation:
        func(c)

    with does_not_raise():
        with read_write(c):
            func(c)


@pytest.mark.parametrize(  # type: ignore
    "string, tokenized",
    [
        ("dog,cat", ["dog", "cat"]),
        ("dog\\,cat\\ ", ["dog,cat "]),
        ("dog,\\ cat", ["dog", " cat"]),
        ("\\ ,cat", [" ", "cat"]),
        ("dog, cat", ["dog", "cat"]),
        ("dog, ca t", ["dog", "ca t"]),
        ("dog, cat", ["dog", "cat"]),
        ("whitespace\\ , before comma", ["whitespace ", "before comma"]),
        (None, []),
        ("", []),
        ("no , escape", ["no", "escape"]),
    ],
)
def test_tokenize_with_escapes(string: str, tokenized: List[str]) -> None:
    assert OmegaConf._tokenize_args(string) == tokenized


@pytest.mark.parametrize(  # type: ignore
    "src, func, expectation",
    [({}, lambda c: c.__setattr__("foo", 1), pytest.raises(AttributeError))],
)
def test_struct_override(src: Any, func: Any, expectation: Any) -> None:
    c = OmegaConf.create(src)
    OmegaConf.set_struct(c, True)

    with expectation:
        func(c)

    with does_not_raise():
        with open_dict(c):
            func(c)


@pytest.mark.parametrize(  # type: ignore
    "flag_name,ctx", [("struct", open_dict), ("readonly", read_write)]
)
def test_open_dict_restore(flag_name: str, ctx: Any) -> None:
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


@pytest.mark.parametrize("copy_method", [lambda x: copy.copy(x), lambda x: x.copy()])
class TestCopy:
    @pytest.mark.parametrize(  # type: ignore
        "src", [[], [1, 2], ["a", "b", "c"], {}, {"a": "b"}, {"a": {"b": []}}]
    )
    def test_copy(self, copy_method: Any, src: Any) -> None:
        src = OmegaConf.create(src)
        cp = copy_method(src)
        assert id(src) != id(cp)
        assert src == cp

    @pytest.mark.parametrize(  # type: ignore
        "src,interpolating_key,interpolated_key",
        [([1, 2, "${0}"], 2, 0), ({"a": 10, "b": "${a}"}, "b", "a")],
    )
    def test_copy_with_interpolation(
        self, copy_method: Any, src: Any, interpolating_key: str, interpolated_key: str
    ) -> None:
        cfg = OmegaConf.create(src)
        assert cfg[interpolated_key] == cfg[interpolating_key]
        cp = copy_method(cfg)
        assert id(cfg) != id(cp)
        assert cp[interpolated_key] == cp[interpolating_key]
        assert cfg[interpolated_key] == cp[interpolating_key]

        # Interpolation is preserved in original
        cfg[interpolated_key] = "XXX"
        assert cfg[interpolated_key] == cfg[interpolating_key]

        # Test interpolation is preserved in copy
        cp[interpolated_key] = "XXX"
        assert cp[interpolated_key] == cp[interpolating_key]

    def test_list_copy_is_shallow(self, copy_method: Any) -> None:
        cfg = OmegaConf.create([[10, 20]])
        cp = copy_method(cfg)
        assert id(cfg) != id(cp)
        assert id(cfg[0]) == id(cp[0])


def test_not_implemented() -> None:
    with pytest.raises(NotImplementedError):
        OmegaConf()


@pytest.mark.parametrize("query, result", [("a", "a"), ("${foo}", 10), ("${bar}", 10)])  # type: ignore
def test_resolve_single(query: str, result: Any) -> None:
    cfg = OmegaConf.create({"foo": 10, "bar": "${foo}"})
    assert cfg._resolve_single(value=query) == result


def test_omegaconf_create() -> None:
    assert OmegaConf.create([]) == []
    assert OmegaConf.create({}) == {}
    with pytest.raises(ValidationError):
        assert OmegaConf.create(10)  # type: ignore


@pytest.mark.parametrize(  # type: ignore
    "cfg, key, expected",
    [
        ({}, "foo", False),
        ({"foo": True}, "foo", False),
        ({"foo": MISSING}, "foo", True),
        ({"foo": "${bar}", "bar": MISSING}, "foo", True),
    ],
)
def test_is_missing(cfg: Any, key: str, expected: Any) -> None:
    cfg = OmegaConf.create(cfg)
    assert OmegaConf.is_missing(cfg, key) == expected


@pytest.mark.parametrize(  # type: ignore
    "cfg, is_conf, is_list, is_dict",
    [
        (None, False, False, False),
        ({}, False, False, False),
        ("aa", False, False, False),
        (10, False, False, False),
        (True, False, False, False),
        (bool, False, False, False),
        (StringNode("foo"), False, False, False),
        (OmegaConf.create({}), True, False, True),
        (OmegaConf.create([]), True, True, False),
    ],
)
def test_is_config(cfg: Any, is_conf: bool, is_list: bool, is_dict: bool) -> None:
    assert OmegaConf.is_config(cfg) == is_conf
    assert OmegaConf.is_list(cfg) == is_list
    assert OmegaConf.is_dict(cfg) == is_dict


@pytest.mark.parametrize(  # type: ignore
    "parent, index, value, expected",
    [
        ([10, 11], 0, ["a", "b"], [["a", "b"], 11]),
        ([None], 0, {"foo": "bar"}, [{"foo": "bar"}]),
        ([None], 0, OmegaConf.create({"foo": "bar"}), [{"foo": "bar"}]),
        ({}, "foo", ["a", "b"], {"foo": ["a", "b"]}),
        ({}, "foo", ("a", "b"), {"foo": ["a", "b"]}),
        ({}, "foo", OmegaConf.create({"foo": "bar"}), {"foo": {"foo": "bar"}}),
    ],
)
def test_assign(parent: Any, index: Union[str, int], value: Any, expected: Any) -> None:
    c = OmegaConf.create(parent)
    c[index] = value
    assert c == expected
