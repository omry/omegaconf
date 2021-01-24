import copy
from enum import Enum
from typing import Any, Dict, List, Union

import pytest
from pytest import raises

from omegaconf import (
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
from omegaconf.errors import ConfigAttributeError, ConfigKeyError

from . import Color, StructuredWithMissing, User, does_not_raise


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
def test_set_value(
    input_: Any, key: Union[str, int], value: Any, expected: Any
) -> None:
    c = OmegaConf.create(input_)
    c[key] = value
    assert c == expected


@pytest.mark.parametrize(
    "input_, key, value",
    [
        # dict
        ({"foo": IntegerNode(10)}, "foo", "str"),
        # list
        ([1, IntegerNode(10)], 1, "str"),
    ],
)
def test_set_value_validation_fail(input_: Any, key: Any, value: Any) -> None:
    c = OmegaConf.create(input_)
    with raises(ValidationError):
        c[key] = value


@pytest.mark.parametrize(
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
    assert c[key] == value._value()


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


@pytest.mark.parametrize(
    "input_, is_empty",
    [
        ([], True),
        ({}, True),
        ([1, 2], False),
        (dict(a=10), False),
    ],
)
def test_empty(input_: Any, is_empty: bool) -> None:
    c = OmegaConf.create(input_)
    assert c.is_empty() == is_empty


@pytest.mark.parametrize("func", [str, repr])
@pytest.mark.parametrize(
    "input_, expected",
    [
        pytest.param([], "[]", id="list"),
        pytest.param({}, "{}", id="dict"),
        pytest.param([1, 2, 3], "[1, 2, 3]", id="list"),
        pytest.param([1, 2, {"a": 3}], "[1, 2, {'a': 3}]", id="dict_in_list"),
        pytest.param([1, 2, [10, 20]], "[1, 2, [10, 20]]", id="list_in_list"),
        pytest.param({"b": {"b": 10}}, "{'b': {'b': 10}}", id="dict"),
        pytest.param({"b": [1, 2, 3]}, "{'b': [1, 2, 3]}", id="list_in_dict"),
        pytest.param(
            StructuredWithMissing,
            (
                "{'num': '???', 'opt_num': '???', 'dict': '???', 'opt_dict': '???', 'list': "
                "'???', 'opt_list': '???', 'user': '???', 'opt_user': '???', 'inter_num': "
                "'${num}', 'inter_user': '${user}', 'inter_opt_user': '${opt_user}'}"
            ),
            id="structured_with_missing",
        ),
    ],
)
def test_str(func: Any, input_: Any, expected: str) -> None:
    c = OmegaConf.create(input_)
    string = func(c)
    assert string == expected


@pytest.mark.parametrize("flag", ["readonly", "struct"])
def test_flag_dict(flag: str) -> None:
    c = OmegaConf.create()
    assert c._get_flag(flag) is None
    c._set_flag(flag, True)
    assert c._get_flag(flag) is True
    c._set_flag(flag, False)
    assert not c._get_flag(flag) is True
    c._set_flag(flag, None)
    assert c._get_flag(flag) is None


@pytest.mark.parametrize("flag", ["readonly", "struct"])
def test_freeze_nested_dict(flag: str) -> None:
    c = OmegaConf.create({"a": {"b": 2}})
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


def test_set_flags() -> None:
    c = OmegaConf.create({"a": {"b": 2}})
    assert not c._get_flag("readonly")
    assert not c._get_flag("struct")
    c._set_flag(["readonly", "struct"], True)
    assert c._get_flag("readonly")
    assert c._get_flag("struct")

    c._set_flag(["readonly", "struct"], [False, True])
    assert not c._get_flag("readonly")
    assert c._get_flag("struct")

    with pytest.raises(ValueError):
        c._set_flag(["readonly", "struct"], [True, False, False])


@pytest.mark.parametrize("no_deepcopy_set_nodes", [True, False])
@pytest.mark.parametrize("node", [20, {"b": 10}, [1, 2]])
def test_get_flag_after_dict_assignment(no_deepcopy_set_nodes: bool, node: Any) -> None:
    cfg = OmegaConf.create({"c": node})
    cfg._set_flag("foo", True)
    nc = cfg._get_node("c")
    assert nc is not None
    assert nc._flags_cache is None
    assert nc._get_flag("foo") is True
    assert nc._flags_cache == {"foo": True}

    cfg2 = OmegaConf.create(flags={"no_deepcopy_set_nodes": no_deepcopy_set_nodes})
    cfg2._set_flag("foo", False)
    cfg2.c = cfg._get_node("c")
    nc = cfg2._get_node("c")
    assert nc is not None
    assert nc._get_flag("foo") is False


@pytest.mark.parametrize(
    "src", [[], [1, 2, 3], dict(), dict(a=10), StructuredWithMissing]
)
class TestDeepCopy:
    def test_deepcopy(self, src: Any) -> None:
        c1 = OmegaConf.create(src)
        c2 = copy.deepcopy(c1)
        assert c1 == c2

        assert c1.__dict__.keys() == c2.__dict__.keys()
        for k in c1.__dict__.keys():
            assert c1.__dict__[k] == c2.__dict__[k]

        assert id(c1) != id(c2)

        if isinstance(c2, ListConfig):
            c2.append(1000)
        elif isinstance(c2, DictConfig):
            c2.num = 42
        assert c1 != c2

    def test_deepcopy_readonly(self, src: Any) -> None:
        c1 = OmegaConf.create(src)
        OmegaConf.set_readonly(c1, True)
        c2 = copy.deepcopy(c1)
        assert c1 == c2
        if isinstance(c2, ListConfig):
            with raises(ReadonlyConfigError):
                c2.append(1000)
        elif isinstance(c2, DictConfig):
            with raises(ReadonlyConfigError):
                c2.num = 42
        assert c1 == c2

    def test_deepcopy_struct(self, src: Any) -> None:
        c1 = OmegaConf.create(src)
        OmegaConf.set_struct(c1, True)
        c2 = copy.deepcopy(c1)
        assert c1 == c2
        if isinstance(c2, ListConfig):
            c2.append(1000)
        elif isinstance(c2, DictConfig):
            with raises(AttributeError):
                c2.foo = 42


def test_deepcopy_after_del() -> None:
    # make sure that deepcopy does not resurrect deleted fields (as it once did, believe it or not).
    c1 = OmegaConf.create(dict(foo=[1, 2, 3], bar=10))
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    del c1["foo"]
    c3 = copy.deepcopy(c1)
    assert c1 == c3


def test_deepcopy_after_pop() -> None:
    c1 = OmegaConf.create(dict(foo=[1, 2, 3], bar=10))
    c2 = copy.deepcopy(c1)
    assert c1 == c2
    c2.pop("foo")
    assert "foo" not in c2
    assert "foo" in c1
    c3 = copy.deepcopy(c1)
    assert "foo" in c3


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
    with raises(ConfigKeyError):
        OmegaConf.merge(c2, OmegaConf.from_dotlist(["dataset.bad_key=yes"]))


@pytest.mark.parametrize(
    "cfg", [ListConfig(element_type=int, content=[]), DictConfig(content={})]
)
def test_deepcopy_preserves_container_type(cfg: Container) -> None:
    cp: Container = copy.deepcopy(cfg)
    assert cp._metadata.element_type == cfg._metadata.element_type


@pytest.mark.parametrize(
    "src, flag_name, func, expectation",
    [
        pytest.param(
            {},
            "struct",
            lambda c: c.__setitem__("foo", 1),
            raises(KeyError),
            id="struct_setiitem",
        ),
        pytest.param(
            {},
            "struct",
            lambda c: c.__setattr__("foo", 1),
            raises(AttributeError),
            id="struct_setattr",
        ),
        pytest.param(
            {},
            "readonly",
            lambda c: c.__setitem__("foo", 1),
            raises(ReadonlyConfigError),
            id="readonly",
        ),
    ],
)
def test_flag_override(
    src: Dict[str, Any], flag_name: str, func: Any, expectation: Any
) -> None:
    c = OmegaConf.create(src)
    c._set_flag(flag_name, True)
    with expectation:
        func(c)

    with does_not_raise():
        with flag_override(c, flag_name, False):
            func(c)


def test_multiple_flags_override() -> None:
    c = OmegaConf.create({"foo": "bar"})
    with flag_override(c, ["readonly"], True):
        with pytest.raises(ReadonlyConfigError):
            c.foo = 10

    with flag_override(c, ["struct"], True):
        with pytest.raises(ConfigAttributeError):
            c.x = 10

    with flag_override(c, ["struct", "readonly"], True):
        with pytest.raises(ConfigAttributeError):
            c.x = 10

        with pytest.raises(ReadonlyConfigError):
            c.foo = 20


@pytest.mark.parametrize(
    "src, func, expectation",
    [
        ({}, lambda c: c.__setitem__("foo", 1), raises(ReadonlyConfigError)),
        ([], lambda c: c.append(1), raises(ReadonlyConfigError)),
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


@pytest.mark.parametrize(
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


@pytest.mark.parametrize(
    "src, func, expectation",
    [({}, lambda c: c.__setattr__("foo", 1), raises(AttributeError))],
)
def test_struct_override(src: Any, func: Any, expectation: Any) -> None:
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


@pytest.mark.parametrize(
    "copy_method",
    [
        pytest.param(lambda x: copy.copy(x), id="copy.copy"),
        pytest.param(lambda x: x.copy(), id="obj.copy"),
    ],
)
class TestCopy:
    @pytest.mark.parametrize(
        "src",
        [
            # lists
            pytest.param(OmegaConf.create([]), id="list_empty"),
            pytest.param(OmegaConf.create([1, 2]), id="list"),
            pytest.param(OmegaConf.create(["a", "b", "c"]), id="list"),
            pytest.param(ListConfig(content=None), id="list_none"),
            pytest.param(ListConfig(content="???"), id="list_missing"),
            # dicts
            pytest.param(OmegaConf.create({}), id="dict_empty"),
            pytest.param(OmegaConf.create({"a": "b"}), id="dict"),
            pytest.param(OmegaConf.create({"a": {"b": []}}), id="dict"),
            pytest.param(DictConfig(content=None), id="dict_none"),
        ],
    )
    def test_copy(self, copy_method: Any, src: Any) -> None:
        cp = copy_method(src)
        assert src is not cp
        assert src == cp

    @pytest.mark.parametrize(
        "src",
        [
            pytest.param(
                DictConfig(content={"a": {"c": 10}, "b": DictConfig(content="${a}")}),
                id="dict_inter",
            )
        ],
    )
    def test_copy_dict_inter(self, copy_method: Any, src: Any) -> None:
        # test direct copying of the b node (without de-referencing by accessing)
        cp = copy_method(src._get_node("b"))
        assert src.b is not cp
        assert OmegaConf.is_interpolation(src, "b")
        assert OmegaConf.is_interpolation(cp)
        assert src._get_node("b")._value() == cp._value()

        # test copy of src and ensure interpolation is copied as interpolation
        cp2 = copy_method(src)
        assert OmegaConf.is_interpolation(cp2, "b")

    @pytest.mark.parametrize(
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

    def test_list_shallow_copy_is_deepcopy(self, copy_method: Any) -> None:
        cfg = OmegaConf.create([[10, 20]])
        cp = copy_method(cfg)
        assert cfg is not cp
        assert cfg[0] is not cp[0]


@pytest.mark.parametrize("copy_func", [copy.copy, copy.deepcopy])
class TestParentAfterCopy:
    def test_dict_copy(self, copy_func: Any) -> None:
        cfg = OmegaConf.create({"a": {"b": 10}})
        nc = copy_func(cfg._get_node("a"))
        assert nc._get_parent() is cfg
        assert nc._get_node("b")._get_parent() is nc

    def test_node_copy(self, copy_func: Any) -> None:
        cfg = OmegaConf.create({"a": {"b": 10}})
        nc = copy_func(cfg.a._get_node("b"))
        assert nc._get_parent() is cfg.a

    def test_list_copy(self, copy_func: Any) -> None:
        cfg = OmegaConf.create({"a": [10]})
        nc = copy_func(cfg._get_node("a"))
        assert nc._get_parent() is cfg
        assert nc._get_node(0)._get_parent() is nc


def test_omegaconf_init_not_implemented() -> None:
    with raises(NotImplementedError):
        OmegaConf()


@pytest.mark.parametrize(
    "query, result",
    [
        ("a", "a"),
        ("${foo}", 10),
        ("${bar}", 10),
        ("foo_${foo}", "foo_10"),
        ("foo_${bar}", "foo_10"),
    ],
)
def test_resolve_str_interpolation(query: str, result: Any) -> None:
    cfg = OmegaConf.create({"foo": 10, "bar": "${foo}"})
    assert (
        cfg._resolve_interpolation(
            key=None,
            value=StringNode(value=query),
            throw_on_missing=False,
            throw_on_resolution_failure=True,
        )
        == result
    )


def test_omegaconf_create() -> None:
    assert OmegaConf.create([]) == []
    assert OmegaConf.create({}) == {}
    with raises(ValidationError):
        assert OmegaConf.create(10)  # type: ignore


@pytest.mark.parametrize(
    "parent, key, value, expected",
    [
        ([10, 11], 0, ["a", "b"], [["a", "b"], 11]),
        ([None], 0, {"foo": "bar"}, [{"foo": "bar"}]),
        ([None], 0, OmegaConf.create({"foo": "bar"}), [{"foo": "bar"}]),
        ({}, "foo", ["a", "b"], {"foo": ["a", "b"]}),
        ({}, "foo", ("a", "b"), {"foo": ["a", "b"]}),
        ({}, "foo", OmegaConf.create({"foo": "bar"}), {"foo": {"foo": "bar"}}),
    ],
)
def test_assign(parent: Any, key: Union[str, int], value: Any, expected: Any) -> None:
    c = OmegaConf.create(parent)
    c[key] = value
    assert c == expected


@pytest.mark.parametrize(
    "cfg, key, expected",
    [
        # dict
        (OmegaConf.create({"foo": "bar"}), "foo", "bar"),
        (OmegaConf.create({"foo": None}), "foo", None),
        (OmegaConf.create({"foo": "???"}), "foo", "???"),
        # list
        (OmegaConf.create([10, 20, 30]), 1, 20),
        (OmegaConf.create([10, None, 30]), 1, None),
        (OmegaConf.create([10, "???", 30]), 1, "???"),
    ],
)
def test_get_node(cfg: Any, key: Any, expected: Any) -> None:
    assert cfg._get_node(key) == expected
