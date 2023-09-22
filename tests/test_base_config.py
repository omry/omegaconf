import copy
from contextlib import nullcontext
from typing import Any, Dict, List, Optional, Union

from pytest import mark, param, raises

from omegaconf import (
    AnyNode,
    Container,
    DictConfig,
    DictKeyType,
    IntegerNode,
    ListConfig,
    OmegaConf,
    ReadonlyConfigError,
    StringNode,
    UnionNode,
    ValidationError,
    flag_override,
    open_dict,
    read_write,
)
from omegaconf._utils import _ensure_container
from omegaconf.errors import ConfigAttributeError, ConfigKeyError, MissingMandatoryValue
from tests import (
    ConcretePlugin,
    Group,
    OptionalUsers,
    StructuredWithMissing,
    SubscriptedDict,
    SubscriptedDictOpt,
    SubscriptedList,
    SubscriptedListOpt,
    User,
    Users,
)


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize("func", [str, repr])
@mark.parametrize(
    "input_, expected",
    [
        param([], "[]", id="list"),
        param({}, "{}", id="dict"),
        param([1, 2, 3], "[1, 2, 3]", id="list"),
        param([1, 2, {"a": 3}], "[1, 2, {'a': 3}]", id="dict_in_list"),
        param([1, 2, [10, 20]], "[1, 2, [10, 20]]", id="list_in_list"),
        param({"b": {"b": 10}}, "{'b': {'b': 10}}", id="dict"),
        param({"b": [1, 2, 3]}, "{'b': [1, 2, 3]}", id="list_in_dict"),
        param(
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


@mark.parametrize("flag", ["readonly", "struct"])
def test_flag_dict(flag: str) -> None:
    c = OmegaConf.create()
    assert c._get_flag(flag) is None
    c._set_flag(flag, True)
    assert c._get_flag(flag) is True
    c._set_flag(flag, False)
    assert not c._get_flag(flag) is True
    c._set_flag(flag, None)
    assert c._get_flag(flag) is None


@mark.parametrize("flag", ["readonly", "struct"])
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

    with raises(ValueError):
        c._set_flag(["readonly", "struct"], [True, False, False])


@mark.parametrize("no_deepcopy_set_nodes", [True, False])
@mark.parametrize("node", [20, {"b": 10}, [1, 2]])
def test_get_flag_after_dict_assignment(no_deepcopy_set_nodes: bool, node: Any) -> None:
    cfg = OmegaConf.create({"c": node})
    cfg._set_flag("foo", True)
    nc: Any = cfg._get_node("c")
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


@mark.parametrize("src", [[], [1, 2, 3], dict(), dict(a=10), StructuredWithMissing])
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


@mark.parametrize(
    "cfg", [ListConfig(element_type=int, content=[]), DictConfig(content={})]
)
def test_deepcopy_preserves_container_type(cfg: Container) -> None:
    cp: Container = copy.deepcopy(cfg)
    assert cp._metadata.element_type == cfg._metadata.element_type


@mark.parametrize(
    "src, flag_name, func, expectation",
    [
        param(
            {},
            "struct",
            lambda c: c.__setitem__("foo", 1),
            raises(KeyError),
            id="struct_setiitem",
        ),
        param(
            {},
            "struct",
            lambda c: c.__setattr__("foo", 1),
            raises(AttributeError),
            id="struct_setattr",
        ),
        param(
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

    with nullcontext():
        with flag_override(c, flag_name, False):
            func(c)


def test_nested_flag_override() -> None:
    c = OmegaConf.create({"a": {"b": 1}})
    with flag_override(c, "test", True):
        assert c._get_flag("test") is True
        with flag_override(c.a, "test", False):
            assert c.a._get_flag("test") is False
    assert c.a._get_flag("test") is None


def test_multiple_flags_override() -> None:
    c = OmegaConf.create({"foo": "bar"})
    with flag_override(c, ["readonly"], True):
        with raises(ReadonlyConfigError):
            c.foo = 10

    with flag_override(c, ["struct"], True):
        with raises(ConfigAttributeError):
            c.x = 10

    with flag_override(c, ["struct", "readonly"], True):
        with raises(ConfigAttributeError):
            c.x = 10

        with raises(ReadonlyConfigError):
            c.foo = 20


@mark.parametrize(
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

    with nullcontext():
        with read_write(c):
            func(c)


@mark.parametrize(
    "src, func, expectation",
    [({}, lambda c: c.__setattr__("foo", 1), raises(AttributeError))],
)
def test_struct_override(src: Any, func: Any, expectation: Any) -> None:
    c = OmegaConf.create(src)
    OmegaConf.set_struct(c, True)

    with expectation:
        func(c)

    with nullcontext():
        with open_dict(c):
            func(c)


@mark.parametrize("flag_name,ctx", [("struct", open_dict), ("readonly", read_write)])
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


@mark.parametrize(
    "copy_method",
    [
        param(lambda x: copy.copy(x), id="copy.copy"),
        param(lambda x: x.copy(), id="obj.copy"),
    ],
)
class TestCopy:
    @mark.parametrize(
        "src",
        [
            # lists
            param(OmegaConf.create([]), id="list_empty"),
            param(OmegaConf.create([1, 2]), id="list"),
            param(OmegaConf.create(["a", "b", "c"]), id="list"),
            param(ListConfig(content=None), id="list_none"),
            param(ListConfig(content="???"), id="list_missing"),
            # dicts
            param(OmegaConf.create({}), id="dict_empty"),
            param(OmegaConf.create({"a": "b"}), id="dict"),
            param(OmegaConf.create({"a": {"b": []}}), id="dict"),
            param(DictConfig(content=None), id="dict_none"),
        ],
    )
    def test_copy(self, copy_method: Any, src: Any) -> None:
        cp = copy_method(src)
        assert src is not cp
        assert src == cp

    @mark.parametrize(
        "src",
        [
            param(
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

    @mark.parametrize(
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


@mark.parametrize("copy_func", [copy.copy, copy.deepcopy])
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

    def test_union_copy(self, copy_func: Any) -> None:
        cfg = OmegaConf.create({"a": UnionNode(10.0, Union[float, bool])})
        nc = copy_func(cfg._get_node("a"))
        assert nc._get_parent() is cfg
        assert nc._value()._get_parent() is nc


def test_omegaconf_init_not_implemented() -> None:
    with raises(NotImplementedError):
        OmegaConf()


@mark.parametrize(
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
        cfg._maybe_resolve_interpolation(
            parent=None,
            key=None,
            value=AnyNode(value=query),
            throw_on_resolution_failure=True,
        )
        == result
    )


def test_omegaconf_create() -> None:
    assert OmegaConf.create([]) == []
    assert OmegaConf.create({}) == {}
    with raises(ValidationError):
        assert OmegaConf.create(10)  # type: ignore


@mark.parametrize(
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


@mark.parametrize(
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


@mark.parametrize(
    "cfg, key",
    [
        # dict
        param({"foo": "???"}, "foo", id="dict"),
        # list
        param([10, "???", 30], 1, id="list_int"),
        param([10, "???", 30], slice(1, 2), id="list_slice"),
    ],
)
def test_string_interpolation_with_readonly_parent(cfg: Any, key: Any) -> None:
    cfg = OmegaConf.create(cfg)
    with raises(MissingMandatoryValue, match="Missing mandatory value"):
        cfg._get_node(key, throw_on_missing_value=True)


def test_flags_root() -> None:
    cfg = OmegaConf.create({"a": {"b": 10}})
    cfg._set_flag("flag", True)
    assert cfg.a._get_flag_no_cache("flag") is True

    cfg.a._set_flags_root(True)
    assert cfg.a._get_flag_no_cache("flag") is None


@mark.parametrize(
    "cls,key,assignment,error",
    [
        param(SubscriptedList, "list", [None], True, id="list_elt"),
        param(SubscriptedList, "list", [0, 1, None], True, id="list_elt_partial"),
        param(SubscriptedDict, "dict_str", {"key": None}, True, id="dict_elt"),
        param(
            SubscriptedDict,
            "dict_str",
            {"key_valid": 123, "key_invalid": None},
            True,
            id="dict_elt_partial",
        ),
        param(SubscriptedList, "list", None, True, id="list"),
        param(SubscriptedDict, "dict_str", None, True, id="dict"),
        param(SubscriptedListOpt, "opt_list", [None], True, id="opt_list_elt"),
        param(SubscriptedDictOpt, "opt_dict", {"key": None}, True, id="opt_dict_elt"),
        param(SubscriptedListOpt, "opt_list", None, False, id="opt_list"),
        param(SubscriptedDictOpt, "opt_dict", None, False, id="opt_dict"),
        param(SubscriptedListOpt, "list_opt", [None], False, id="list_opt_elt"),
        param(SubscriptedDictOpt, "dict_opt", {"key": None}, False, id="dict_opt_elt"),
        param(SubscriptedListOpt, "list_opt", None, True, id="list_opt"),
        param(SubscriptedDictOpt, "dict_opt", None, True, id="dict_opt"),
        param(
            ListConfig([None], element_type=Optional[User]),
            0,
            User("Bond", 7),
            False,
            id="set_optional_user",
        ),
        param(
            ListConfig([User], element_type=User),
            0,
            None,
            True,
            id="illegal_set_user_to_none",
        ),
    ],
)
def test_optional_assign(cls: Any, key: str, assignment: Any, error: bool) -> None:
    cfg = OmegaConf.structured(cls)
    if error:
        with raises(ValidationError):
            cfg[key] = assignment
    else:
        cfg[key] = assignment
        assert cfg[key] == assignment


@mark.parametrize(
    "src,keys,ref_type,is_optional",
    [
        param(Group, ["admin"], User, True, id="opt_user"),
        param(
            ConcretePlugin,
            ["params"],
            ConcretePlugin.FoobarParams,
            False,
            id="nested_structured_conf",
        ),
        param(
            OmegaConf.structured(Users({"user007": User("Bond", 7)})).name2user,
            ["user007"],
            User,
            False,
            id="structured_dict_of_user",
        ),
        param(
            DictConfig({"a": 123}, element_type=int), ["a"], int, False, id="dict_int"
        ),
        param(
            DictConfig({"a": 123}, element_type=Optional[int]),
            ["a"],
            int,
            True,
            id="dict_opt_int",
        ),
        param(DictConfig({"a": 123}), ["a"], Any, True, id="dict_any"),
        param(
            OmegaConf.merge(Users, {"name2user": {"joe": User("joe")}}),
            ["name2user", "joe"],
            User,
            False,
            id="dict:merge_into_new_user_node",
        ),
        param(
            OmegaConf.merge(OptionalUsers, {"name2user": {"joe": User("joe")}}),
            ["name2user", "joe"],
            User,
            True,
            id="dict:merge_into_new_optional_user_node",
        ),
        param(
            OmegaConf.merge(ListConfig([], element_type=User), [User(name="joe")]),
            [0],
            User,
            False,
            id="list:merge_into_new_user_node",
        ),
        param(
            OmegaConf.merge(
                ListConfig([], element_type=Optional[User]), [User(name="joe")]
            ),
            [0],
            User,
            True,
            id="list:merge_into_new_optional_user_node",
        ),
        param(SubscriptedDictOpt, ["opt_dict"], Dict[str, int], True, id="opt_dict"),
        param(SubscriptedListOpt, ["opt_list"], List[int], True, id="opt_list"),
        param(
            SubscriptedDictOpt,
            ["dict_opt"],
            Dict[str, Optional[int]],
            False,
            id="opt_dict",
        ),
        param(
            SubscriptedListOpt, ["list_opt"], List[Optional[int]], False, id="opt_dict"
        ),
    ],
)
def test_assignment_optional_behavior(
    src: Any, keys: List[DictKeyType], ref_type: Any, is_optional: bool
) -> None:
    cfg = _ensure_container(src)
    for k in keys:
        cfg = cfg._get_node(k)
    assert cfg._is_optional() == is_optional
    assert cfg._metadata.ref_type == ref_type
