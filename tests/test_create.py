"""Testing for OmegaConf"""
import platform
import re
import sys
from collections.abc import Sequence
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional

import yaml
from pytest import mark, param, raises

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf.errors import UnsupportedValueType, ValidationError
from tests import (
    ConcretePlugin,
    DictOfAny,
    DictSubclass,
    IllegalType,
    ListOfAny,
    ListSubclass,
    NonCopyableIllegalType,
    Plugin,
    Shape,
)


@mark.parametrize(
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
        (OmegaConf.create([OmegaConf.create({})]), [{}]),
        (OmegaConf.create({"foo": Path("bar")}), {"foo": Path("bar")}),
    ],
)
def test_create_value(input_: Any, expected: Any) -> None:
    assert OmegaConf.create(input_) == expected


@mark.parametrize(
    "input_",
    [
        # top level dict
        {"x": IllegalType()},
        {"x": {"y": IllegalType()}},
        {"x": [IllegalType()]},
        # top level list
        [IllegalType()],
        [[IllegalType()]],
        [{"x": IllegalType()}],
        [{"x": [IllegalType()]}],
    ],
)
def test_create_allow_objects(input_: Any) -> None:
    # test creating from a primitive container
    cfg = OmegaConf.create(input_, flags={"allow_objects": True})
    assert cfg == input_

    # test creating from an OmegaConf object, inheriting the allow_objects flag
    cfg = OmegaConf.create(cfg)
    assert cfg == input_

    # test creating from an OmegaConf object
    cfg = OmegaConf.create(cfg, flags={"allow_objects": True})
    assert cfg == input_


@mark.parametrize(
    "input_",
    [
        # top level dict
        {"x": NonCopyableIllegalType()},
        {"x": {"y": NonCopyableIllegalType()}},
        {"x": [NonCopyableIllegalType()]},
        # top level list
        [NonCopyableIllegalType()],
        [[NonCopyableIllegalType()]],
        [{"x": NonCopyableIllegalType()}],
        [{"x": [NonCopyableIllegalType()]}],
    ],
)
def test_create_allow_objects_non_copyable(input_: Any) -> None:
    # test creating from a primitive container
    cfg = OmegaConf.create(input_, flags={"allow_objects": True})
    assert cfg == input_

    # test creating from an OmegaConf object, inheriting the allow_objects flag
    cfg = OmegaConf.create(cfg)
    assert cfg == input_

    # test creating from an OmegaConf object
    cfg = OmegaConf.create(cfg, flags={"allow_objects": True})
    assert cfg == input_


@mark.parametrize(
    "input_",
    [
        param(Shape(10, 2, 3), id="shape"),
        param(ListSubclass((1, 2, 3)), id="list_subclass"),
        param(DictSubclass({"key": "value"}), id="dict_subclass"),
    ],
)
class TestCreationWithCustomClass:
    def test_top_level(self, input_: Any) -> None:
        if isinstance(input_, Sequence):
            cfg = OmegaConf.create(input_)  # type: ignore
            assert isinstance(cfg, ListConfig)
        else:
            with raises(ValidationError):
                OmegaConf.create(input_)

    def test_nested(self, input_: Any) -> None:
        with raises(UnsupportedValueType):
            OmegaConf.create({"foo": input_})

    def test_nested_allow_objects(self, input_: Any) -> None:
        cfg = OmegaConf.create({"foo": input_}, flags={"allow_objects": True})
        assert isinstance(cfg.foo, type(input_))

    def test_structured_conf(self, input_: Any) -> None:
        if isinstance(input_, Sequence):
            cfg = OmegaConf.structured(ListOfAny(input_))  # type: ignore
            assert isinstance(cfg.list, ListConfig)
        else:
            cfg = OmegaConf.structured(DictOfAny(input_))
            assert isinstance(cfg.dict, DictConfig)

    def test_direct_creation_of_listconfig_or_dictconfig(self, input_: Any) -> None:
        if isinstance(input_, Sequence):
            cfg = ListConfig(input_)  # type: ignore
            assert isinstance(cfg, ListConfig)
        else:
            cfg = DictConfig(input_)  # type: ignore
            assert isinstance(cfg, DictConfig)


@mark.parametrize(
    "input_",
    [
        param({"foo": "bar"}, id="dict"),
        param([1, 2, 3], id="list"),
    ],
)
def test_create_flags_overriding(input_: Any) -> Any:
    cfg = OmegaConf.create(input_)
    OmegaConf.set_struct(cfg, True)

    # by default flags are inherited
    cfg2 = OmegaConf.create(cfg)
    assert OmegaConf.is_struct(cfg2)
    assert not OmegaConf.is_readonly(cfg2)

    # but specified flags are replacing all of the flags (even those that are not specified)
    cfg2 = OmegaConf.create(cfg, flags={"readonly": True})
    assert not OmegaConf.is_struct(cfg2)
    assert OmegaConf.is_readonly(cfg2)


def test_create_from_cli() -> None:
    sys.argv = ["program.py", "a=1", "b.c=2"]
    c = OmegaConf.from_cli()
    assert {"a": 1, "b": {"c": 2}} == c


def test_cli_passing() -> None:
    args_list = ["a=1", "b.c=2"]
    c = OmegaConf.from_cli(args_list)
    assert {"a": 1, "b": {"c": 2}} == c


@mark.parametrize(
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
    with raises(UnsupportedValueType, match=re.escape("key: [0]")):
        OmegaConf.create([IllegalType()])


def test_create_list_with_illegal_value_idx1() -> None:
    lst = [1, IllegalType(), 3]
    with raises(UnsupportedValueType, match=re.escape("key: [1]")):
        OmegaConf.create(lst)


def test_create_dict_with_illegal_value() -> None:
    with raises(UnsupportedValueType, match=re.escape("key: a")):
        OmegaConf.create({"a": IllegalType()})


def test_create_nested_dict_with_illegal_value() -> None:
    with raises(ValueError, match=re.escape("key: a.b")):
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


@mark.parametrize("node", [({"bar": 10}), ([1, 2, 3])])
def test_create_node_parent_retained_on_create(node: Any) -> None:
    cfg1 = OmegaConf.create({"foo": node})
    cfg2 = OmegaConf.create({"zonk": cfg1.foo})
    assert cfg2 == {"zonk": node}
    assert cfg1.foo._get_parent() == cfg1
    assert cfg1.foo._get_parent() is cfg1


@mark.parametrize("node", [({"bar": 10}), ([1, 2, 3])])
def test_create_node_parent_retained_on_assign(node: Any) -> None:
    cfg1 = OmegaConf.create({"foo": node})
    cfg2 = OmegaConf.create()
    cfg2.zonk = cfg1.foo
    assert cfg1.foo._get_parent() is cfg1
    assert cfg2.zonk._get_parent() is cfg2


@mark.parametrize(
    "node",
    [
        {"a": 0},
        DictConfig({"a": 0}),
    ],
)
def test_dict_assignment_deepcopy_semantics(node: Any) -> None:
    cfg = OmegaConf.create()
    cfg.foo = node
    node["a"] = 1
    assert cfg.foo.a == 0


@mark.parametrize(
    "node",
    [
        [1, 2],
        ListConfig([1, 2]),
    ],
)
def test_list_assignment_deepcopy_semantics(node: Any) -> None:
    cfg = OmegaConf.create()
    cfg.foo = node
    node[1] = 10
    assert cfg.foo[1] == 2


@mark.parametrize("d", [{"a": {"b": 10}}, {"a": {"b": {"c": 10}}}])
def test_assign_does_not_modify_src_config(d: Any) -> None:
    cfg1 = OmegaConf.create(d)
    cfg2 = OmegaConf.create({})
    cfg2.a = cfg1.a
    assert cfg1 == d
    assert cfg2 == d

    assert cfg1.a._get_parent() is cfg1
    assert cfg1.a._get_node("b")._get_parent() is cfg1.a

    assert cfg2.a._get_parent() is cfg2
    assert cfg2.a._get_node("b")._get_parent() is cfg2.a


def test_create_unmodified_loader() -> None:
    cfg = OmegaConf.create("gitrev: 100e100")
    yaml_cfg = yaml.load("gitrev: 100e100", Loader=yaml.loader.SafeLoader)
    assert cfg.gitrev == 1e102
    assert yaml_cfg["gitrev"] == "100e100"


def test_create_float_yaml() -> None:
    # Note there are some discrepencies with the antrl parser.
    # The following follow the yaml more closely,
    # but arguably the antlr interpretation is better (which also
    # more closely matches python. Specifically:
    #   c_s not parsed as float. antlr does parse as float
    #   e_s and f_s not parsed. antlr does parse as float
    #   h_f and i_f parsed as float. antlr does not parse as float
    cfg = OmegaConf.create(
        dedent(
            """\
            a_s: 0_e0
            b_i: 0_0
            c_s: 1_0e1_0
            d_f: .5
            e_s: +.9
            f_s: -.9
            g_f: 1_1_2.1
            h_f: 1__2.1
            i_f: 1.2_
            """
        )
    )
    assert cfg == {
        "a_s": "0_e0",
        "b_i": 0,
        "c_s": "1_0e1_0",
        "d_f": 0.5,
        "e_s": "+.9",
        "f_s": "-.9",
        "g_f": 112.1,
        "h_f": 12.1,
        "i_f": 1.2,
    }


def test_create_untyped_list() -> None:
    from omegaconf._utils import get_type_hint

    cfg = ListConfig(ref_type=List, content=[])
    assert get_type_hint(cfg) == Optional[List]


def test_create_untyped_dict() -> None:
    from omegaconf._utils import get_type_hint

    cfg = DictConfig(ref_type=Dict, content={})
    assert get_type_hint(cfg) == Optional[Dict]


@mark.parametrize(
    "input_",
    [
        dedent(
            """\
            a:
              b: 1
              c: 2
              b: 3
            """
        ),
        dedent(
            """\
            a:
              b: 1
            a:
              b: 2
            """
        ),
    ],
)
def test_yaml_duplicate_keys(input_: str) -> None:
    with raises(yaml.constructor.ConstructorError):
        OmegaConf.create(input_)


def test_yaml_merge() -> None:
    cfg = OmegaConf.create(
        dedent(
            """\
            a: &A
                x: 1
            b: &B
                y: 2
            c:
                <<: *A
                <<: *B
                x: 3
                z: 1
            """
        )
    )
    assert cfg == {"a": {"x": 1}, "b": {"y": 2}, "c": {"x": 3, "y": 2, "z": 1}}


@mark.parametrize(
    "path_type",
    [
        param("Path", id="path"),
        param(
            "PosixPath",
            marks=mark.skipif(
                platform.system() == "Windows", reason="requires posix path support"
            ),
            id="posixpath",
        ),
        param(
            "WindowsPath",
            marks=mark.skipif(
                platform.system() != "Windows", reason="requires windows"
            ),
            id="windowspath",
        ),
    ],
)
def test_create_path(path_type: str) -> None:
    yaml_document = dedent(
        """\
        foo: !!python/object/apply:pathlib.{}
          - hello.txt
        """
    )
    yaml_document = yaml_document.format(path_type)
    assert OmegaConf.create(yaml_document) == yaml.unsafe_load(yaml_document)


@mark.parametrize(
    "data",
    [
        param("", id="empty"),
        param("hello", id="name_only"),
        param("a: b", id="dictconfig"),
        param("- a", id="listconfig"),
    ],
)
def test_create_from_str_check_parent(data: str) -> None:
    parent = OmegaConf.create({})
    cfg = OmegaConf.create(data, parent=parent)
    assert cfg._get_parent() is parent
