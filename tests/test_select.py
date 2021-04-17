from typing import Any, Optional

from _pytest.python_api import RaisesContext
from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, MissingMandatoryValue, OmegaConf
from omegaconf._impl import select_value
from omegaconf._utils import _ensure_container
from omegaconf.errors import InterpolationKeyError


@mark.parametrize(
    "struct",
    [param(False, id="not_struct"), param(True, id="struct")],
)
class TestSelect:
    @mark.parametrize(
        "cfg, key, expected",
        [
            # None returned
            param({}, "nope", None, id="dict:none"),
            param({}, "not.there", None, id="dict:none"),
            param({}, "still.not.there", None, id="dict:none"),
            param({"a": 10}, "a.b", None, id="dict:nesting_into_value"),
            param({"a": None}, "a.b", None, id="dict:nesting_into_none"),
            param({"a": DictConfig(None)}, "a.b", None, id="dict:nesting_into_none"),
            param({"a": ListConfig(None)}, "a.b", None, id="dict:nesting_into_none"),
            # value returned
            param({"c": 1}, "c", 1, id="dict:int"),
            param({"a": {"v": 1}}, "a.v", 1, id="dict:int"),
            param({"a": {"v": 1}}, "a", {"v": 1}, id="dict:dict"),
            param({"missing": "???"}, "missing", None, id="dict:missing"),
            param([], "0", None, id="list:oob"),
            param([1, "2"], "0", 1, id="list:int"),
            param([1, "2"], "1", "2", id="list:str"),
            param(["???"], "0", None, id="list:missing"),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "0", 1),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1.a", 10),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1.b", None),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1.c.0", "foo"),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1.c.1", "bar"),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1[c].0", "foo"),
            param([1, {"a": 10, "c": ["foo", "bar"]}], "1[c][1]", "bar"),
            param([1, 2, 3], "a", raises(TypeError)),
            param({"a": {"v": 1}}, "", {"a": {"v": 1}}, id="select_root"),
            param({"a": {"b": 1}, "c": "one=${a.b}"}, "c", "one=1", id="inter"),
            param({"a": {"b": "one=${n}"}, "n": 1}, "a.b", "one=1", id="inter"),
            # relative selection
            param({"a": {"b": {"c": 10}}}, ".a", {"b": {"c": 10}}, id="relative"),
            param({"a": {"b": {"c": 10}}}, ".a.b", {"c": 10}, id="relative"),
        ],
    )
    def test_select(
        self,
        restore_resolvers: Any,
        cfg: Any,
        key: Any,
        expected: Any,
        struct: Optional[bool],
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        if isinstance(expected, RaisesContext):
            with expected:
                OmegaConf.select(cfg, key)
        else:
            assert OmegaConf.select(cfg, key) == expected

    @mark.parametrize(
        "register_func",
        [OmegaConf.legacy_register_resolver, OmegaConf.register_new_resolver],
    )
    @mark.parametrize(
        "cfg, key, expected",
        [
            param({"a": {"b": "one=${func:1}"}}, "a.b", "one=_1_", id="resolver"),
        ],
    )
    def test_select_resolver(
        self,
        restore_resolvers: Any,
        cfg: Any,
        key: Any,
        expected: Any,
        register_func: Any,
        struct: Optional[bool],
    ) -> None:
        register_func("func", lambda x: f"_{x}_")
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        if isinstance(expected, RaisesContext):
            with expected:
                OmegaConf.select(cfg, key)
        else:
            assert OmegaConf.select(cfg, key) == expected

    @mark.parametrize("default", [10, None])
    @mark.parametrize(
        ("cfg", "key"),
        [
            param({}, "not_found", id="empty"),
            param({"missing": "???"}, "missing", id="missing"),
            param({"int": 0}, "int.y", id="non_container"),
        ],
    )
    def test_select_default_returned(
        self,
        cfg: Any,
        struct: Optional[bool],
        key: Any,
        default: Any,
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        assert OmegaConf.select(cfg, key, default=default) == default

    @mark.parametrize("default", [10, None])
    @mark.parametrize(
        ("cfg", "key", "expected"),
        [
            param({"x": None}, "x", None, id="none"),
            param({"x": DictConfig(None)}, "x", None, id="DictConfig(none)"),
            param({"x": None}, "", DictConfig({"x": None}), id="root"),
        ],
    )
    def test_select_default_not_used(
        self,
        cfg: Any,
        struct: Optional[bool],
        key: Any,
        default: Any,
        expected: Any,
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        selected = OmegaConf.select(cfg, key, default=default)
        assert selected == expected
        assert type(selected) is type(expected)

    @mark.parametrize("default", [10, None])
    @mark.parametrize(
        ("cfg", "key", "expected"),
        [
            param({"x": {"y": None}}, "y", None, id="none"),
            param({"x": {"y": 99}}, "y", 99, id="value"),
            param({"x": {"y": None}}, "..", {"x": {"y": None}}, id="root"),
        ],
    )
    def test_nested_select_default_not_used(
        self,
        cfg: Any,
        struct: Optional[bool],
        key: Any,
        default: Any,
        expected: Any,
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        assert OmegaConf.select(cfg.x, key, default=default) == expected

    @mark.parametrize("default", [10, None])
    @mark.parametrize(
        "cfg, key",
        [
            param({"missing": "???"}, "missing", id="missing_dict"),
            param(["???"], "0", id="missing_list"),
        ],
    )
    def test_select_default_throw_on_missing(
        self,
        cfg: Any,
        struct: Optional[bool],
        key: Any,
        default: Any,
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)

        # throw on missing still throws if default is provided
        with raises(MissingMandatoryValue):
            OmegaConf.select(cfg, key, default=default, throw_on_missing=True)

    @mark.parametrize(
        ("cfg", "key"),
        [
            param({"inter": "${bad_key}"}, "inter", id="inter_bad_key"),
        ],
    )
    def test_select_default_throw_on_resolution_failure(
        self, cfg: Any, key: Any, struct: Optional[bool]
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)

        # throw on resolution failure still throws if default is provided
        with raises(InterpolationKeyError):
            OmegaConf.select(cfg, key, default=123, throw_on_resolution_failure=True)

    @mark.parametrize(
        ("cfg", "node_key", "expected"),
        [
            param({"foo": "${bar}", "bar": 10}, "foo", 10, id="simple"),
            param({"foo": "${bar}"}, "foo", None, id="no_key"),
            param({"foo": "${bar}", "bar": "???"}, "foo", None, id="key_missing"),
            param(
                {"foo": "${bar}", "bar": "${zoo}", "zoo": "???"},
                "foo",
                None,
                id="key_missing_indirect",
            ),
        ],
    )
    def test_select_invalid_interpolation(
        self, cfg: Any, node_key: str, expected: Any, struct: Optional[bool]
    ) -> None:
        cfg = _ensure_container(cfg)
        OmegaConf.set_struct(cfg, struct)
        resolved = OmegaConf.select(
            cfg,
            node_key,
            throw_on_missing=False,
            throw_on_resolution_failure=False,
        )
        assert resolved == expected

    def test_select_from_dict(self, struct: Optional[bool]) -> None:
        cfg = OmegaConf.create({"missing": "???"})
        OmegaConf.set_struct(cfg, struct)
        with raises(MissingMandatoryValue):
            OmegaConf.select(cfg, "missing", throw_on_missing=True)
        assert OmegaConf.select(cfg, "missing", throw_on_missing=False) is None
        assert OmegaConf.select(cfg, "missing") is None


@mark.parametrize(
    "cfg,key,expected",
    [
        param({"a": "${b}", "b": 10}, "a", 10, id="simple"),
        param(
            {"a": "${x}"},
            "a",
            raises(InterpolationKeyError),
            id="not_found",
        ),
        param(
            {"a": "${x.y}"},
            "a",
            raises(InterpolationKeyError),
            id="not_found",
        ),
        param({"a": "foo_${b}", "b": "bar"}, "a", "foo_bar", id="str_inter"),
        param(
            {"a": "${x}_${y}", "x": "foo", "y": "bar"},
            "a",
            "foo_bar",
            id="multi_str_inter",
        ),
        param({"a": "foo_${b.c}", "b": {"c": 10}}, "a", "foo_10", id="str_deep_inter"),
        param({"a": 10, "b": [1, "${a}"]}, "b.1", 10, id="from_list"),
        param({"a": "${b}", "b": {"c": 10}}, "a", {"c": 10}, id="dict_val"),
        param({"a": "${b}", "b": [1, 2]}, "a", [1, 2], id="list_val"),
        param({"a": "${b.1}", "b": [1, 2]}, "a", 2, id="list_index"),
        param({"a": "X_${b}", "b": [1, 2]}, "a", "X_[1, 2]", id="liststr"),
        param({"a": "X_${b}", "b": {"c": 1}}, "a", "X_{'c': 1}", id="dict_str"),
        param({"a": "${b}", "b": "${c}", "c": 10}, "a", 10, id="two_steps"),
        param({"bar": 10, "foo": ["${bar}"]}, "foo.0", 10, id="inter_in_list"),
        param({"foo": None, "bar": "${foo}"}, "bar", None, id="none"),
        param({"list": ["bar"], "foo": "${list.0}"}, "foo", "bar", id="list"),
        param(
            {"user@domain": 10, "foo": "${user@domain}"}, "foo", 10, id="user@domain"
        ),
        # relative interpolations
        param({"a": "${.b}", "b": 10}, "a", 10, id="relative"),
        param({"a": {"z": "${.b}", "b": 10}}, "a.z", 10, id="relative"),
        param({"a": {"z": "${..b}"}, "b": 10}, "a.z", 10, id="relative"),
        param({"a": {"z": "${..a.b}", "b": 10}}, "a.z", 10, id="relative"),
        param(
            {"a": "${..b}", "b": 10},
            "a",
            raises(InterpolationKeyError),
            id="relative",
        ),
    ],
)
def test_select_resolves_interpolation(cfg: Any, key: str, expected: Any) -> None:
    cfg = _ensure_container(cfg)
    if isinstance(expected, RaisesContext):
        with expected:
            OmegaConf.select(cfg, key)
    else:
        assert OmegaConf.select(cfg, key) == expected


inp: Any = {"a": {"b": {"c": 10}}, "z": 10}


class TestSelectFromNestedNode:
    @mark.parametrize(
        ("key", "expected"),
        [
            # all selects are performed on cfg.a:
            # relative keys
            (".", inp["a"]),
            (".b", inp["a"]["b"]),
            (".b.c", inp["a"]["b"]["c"]),
            ("..", inp),
            ("..a", inp["a"]),
            ("..a.b", inp["a"]["b"]),
            ("..z", inp["z"]),
        ],
    )
    def test_select_from_nested_node_with_a_relative_key(
        self, key: str, expected: Any
    ) -> None:
        cfg = OmegaConf.create(inp)
        # select returns the same result when a key is relative independent of absolute_key flag.
        assert select_value(cfg.a, key, absolute_key=False) == expected
        assert select_value(cfg.a, key, absolute_key=True) == expected

    @mark.parametrize(
        ("key", "expected"),
        [
            # all selects are performed on cfg.a:
            # absolute keys are relative to the calling node
            ("", inp["a"]),
            ("b", inp["a"]["b"]),
            ("b.c", inp["a"]["b"]["c"]),
        ],
    )
    def test_select_from_nested_node_relative_key_interpretation(
        self, key: str, expected: Any
    ) -> None:
        cfg = OmegaConf.create(inp)
        assert select_value(cfg.a, key, absolute_key=False) == expected

    @mark.parametrize(
        ("key", "expected"),
        [
            # all selects are performed on cfg.a:
            # absolute keys are relative to the config root
            ("", inp),
            ("a", inp["a"]),
            ("a.b", inp["a"]["b"]),
            ("a.b.c", inp["a"]["b"]["c"]),
            ("z", inp["z"]),
        ],
    )
    def test_select_from_nested_node_absolute_key_interpretation(
        self, key: str, expected: Any
    ) -> None:
        cfg = OmegaConf.create(inp)
        assert select_value(cfg.a, key, absolute_key=True) == expected
