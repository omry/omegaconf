import copy
import re
from typing import Any, Dict, List, Optional, Union

from pytest import mark, param, raises

from omegaconf import (
    MISSING,
    Container,
    DictConfig,
    IntegerNode,
    KeyValidationError,
    ListConfig,
    Node,
    OmegaConf,
    ValidationError,
)
from omegaconf._utils import (
    ValueKind,
    _ensure_container,
    _resolve_optional,
    get_value_kind,
    is_dict_annotation,
    is_list_annotation,
    is_structured_config,
)
from tests import ConcretePlugin, Plugin


def check_node_metadata(
    node: Container,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    value_optional, value_ref_type = _resolve_optional(type_hint)
    assert node._metadata.optional == value_optional
    assert node._metadata.ref_type == value_ref_type
    assert node._metadata.key_type == key_type
    assert node._metadata.element_type == elt_type
    assert node._metadata.object_type == obj_type

    if is_dict_annotation(value_ref_type) or is_structured_config(value_ref_type):
        assert isinstance(node, DictConfig)
    elif is_list_annotation(value_ref_type):
        assert isinstance(node, ListConfig)


def check_subnode(
    cfg: Container,
    key: Any,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    "Validate that `cfg[key] == value` and that subnode `cfg._get_node(key)._metadata` is correct."
    node = cfg._get_node(key)
    assert isinstance(node, (ListConfig, DictConfig))
    vk = get_value_kind(node)

    if vk in (ValueKind.MANDATORY_MISSING, ValueKind.INTERPOLATION):
        if isinstance(value, Node):
            value = value._value()
        assert node._value() == value
    else:
        assert cfg[key] == value

    check_node_metadata(node, type_hint, key_type, elt_type, obj_type)


@mark.parametrize(
    "cfg, type_hint, key_type, elt_type, obj_type",
    [
        param(
            ListConfig([[[456]]], element_type=List[List[int]]),
            List[List[int]],
            int,
            List[int],
            list,
            id="list-list-list",
        ),
        param(
            ListConfig([{"foo": {"bar": 456}}], element_type=Dict[str, Dict[str, int]]),
            Dict[str, Dict[str, int]],
            str,
            Dict[str, int],
            dict,
            id="list-dict-dict",
        ),
        param(
            ListConfig([[123], None], element_type=Optional[List[int]]),
            Optional[List[int]],
            int,
            int,
            list,
            id="list-optional-list",
        ),
        param(
            ListConfig([[123], [None]], element_type=List[Optional[int]]),
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="list-list-optional",
        ),
        param(
            ListConfig([{"bar": 456}, None], element_type=Optional[Dict[str, int]]),
            Optional[Dict[str, int]],
            str,
            int,
            dict,
            id="list-optional-dict",
        ),
        param(
            ListConfig(
                [{"foo": 456}, {"bar": None}], element_type=Dict[str, Optional[int]]
            ),
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="list-dict-optional",
        ),
        param(
            DictConfig({"foo": [[456]]}, element_type=List[List[int]]),
            List[List[int]],
            int,
            List[int],
            list,
            id="dict-list-list",
        ),
        param(
            DictConfig(
                {"foo": {"bar": {"baz": 456}}}, element_type=Dict[str, Dict[str, int]]
            ),
            Dict[str, Dict[str, int]],
            str,
            Dict[str, int],
            dict,
            id="dict-dict-dict",
        ),
        param(
            DictConfig({"foo": [123], "bar": None}, element_type=Optional[List[int]]),
            Optional[List[int]],
            int,
            int,
            list,
            id="dict-optional-list",
        ),
        param(
            DictConfig({"foo": [123], "bar": [None]}, element_type=List[Optional[int]]),
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="dict-list-optional",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": None},
                element_type=Optional[Dict[str, int]],
            ),
            Optional[Dict[str, int]],
            str,
            int,
            dict,
            id="dict-optional-dict",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": {"qux": None}},
                element_type=Dict[str, Optional[int]],
            ),
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="dict-dict-optional",
        ),
        param(
            DictConfig(
                {"foo": {"bar": ConcretePlugin()}}, element_type=Dict[str, Plugin]
            ),
            Dict[str, Plugin],
            str,
            Plugin,
            dict,
            id="dict-of-plugin",
        ),
        param(
            DictConfig({"foo": [ConcretePlugin()]}, element_type=List[Plugin]),
            List[Plugin],
            int,
            Plugin,
            list,
            id="list-of-plugin",
        ),
    ],
)
def test_container_nested_element(
    cfg: Union[DictConfig, ListConfig],
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    """Ensure metadata and contents of container-typed subnode are correct"""
    cfg = copy.deepcopy(cfg)
    keys: Any = range(len(cfg)) if isinstance(cfg, ListConfig) else cfg.keys()
    for key in keys:
        value = cfg[key]
        check_subnode(
            cfg,
            key,
            value,
            type_hint,
            key_type,
            elt_type,
            obj_type if value is not None else None,
        )


@mark.parametrize(
    "cfg, value, type_hint, key_type, elt_type, obj_type",
    [
        param(
            ListConfig([[[456]]], element_type=List[List[int]]),
            [[123]],
            List[List[int]],
            int,
            List[int],
            list,
            id="assign-to-list-element",
        ),
        param(
            ListConfig([{"foo": {"bar": 456}}], element_type=Dict[str, Dict[str, int]]),
            {"baz": {"qux": 123}},
            Dict[str, Dict[str, int]],
            str,
            Dict[str, int],
            dict,
            id="assign-to-dict-element",
        ),
        param(
            ListConfig([[123], None], element_type=Optional[List[int]]),
            [456],
            Optional[List[int]],
            int,
            int,
            list,
            id="assign-list-to-optional-list",
        ),
        param(
            ListConfig([{"foo": 456}, None], element_type=Optional[Dict[str, int]]),
            {"bar": 123},
            Optional[Dict[str, int]],
            str,
            int,
            dict,
            id="assign-dict-to-optional-dict",
        ),
        param(
            ListConfig([[123], [None]], element_type=List[Optional[int]]),
            [456],
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="assign-list-to-list-optional",
        ),
        param(
            ListConfig([[123], [None]], element_type=List[Optional[int]]),
            [None],
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="assign-list-none-to-list-optional",
        ),
        param(
            ListConfig(
                [{"foo": 456}, {"bar": None}], element_type=Dict[str, Optional[int]]
            ),
            {"baz": 123},
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="assign-dict-to-dict-optional",
        ),
        param(
            ListConfig(
                [{"foo": 456}, {"bar": None}], element_type=Dict[str, Optional[int]]
            ),
            {"baz": None},
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="assign-dict-none-to-dict-optional",
        ),
        param(
            ListConfig([{"foo": ConcretePlugin()}], element_type=Dict[str, Plugin]),
            {"bar": ConcretePlugin()},
            Dict[str, Plugin],
            str,
            Plugin,
            dict,
            id="assign-dict-plugin",
        ),
        param(
            ListConfig([[ConcretePlugin()]], element_type=List[Plugin]),
            [ConcretePlugin()],
            List[Plugin],
            int,
            Plugin,
            list,
            id="assign-list-plugin",
        ),
    ],
)
@mark.parametrize(
    "ensure_container",
    [
        param(True, id="container"),
        param(False, id="no_container"),
    ],
)
def test_list_assign_to_container_typed_element(
    cfg: ListConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
    ensure_container: bool,
) -> None:
    cfg = copy.deepcopy(cfg)
    if ensure_container:
        value = _ensure_container(value)

    n = len(cfg)
    for idx in range(n):
        cfg[idx] = value
        check_subnode(cfg, idx, value, type_hint, key_type, elt_type, obj_type)

    cfg.append(value)
    check_subnode(cfg, n, value, type_hint, key_type, elt_type, obj_type)


@mark.parametrize(
    "cfg, type_hint, key_type, elt_type",
    [
        param(
            ListConfig([[123], None], element_type=Optional[List[int]]),
            Optional[List[int]],
            int,
            int,
            id="assign-to-optional-list",
        ),
        param(
            ListConfig([{"bar": 456}, None], element_type=Optional[Dict[str, int]]),
            Optional[Dict[str, int]],
            str,
            int,
            id="assign-to-optional-dict",
        ),
        param(
            ListConfig([[ConcretePlugin()], None], element_type=Optional[List[Plugin]]),
            Optional[List[Plugin]],
            int,
            Plugin,
            id="assign-to-optional-plugin-list",
        ),
        param(
            ListConfig(
                [{"bar": ConcretePlugin()}, None],
                element_type=Optional[Dict[str, Plugin]],
            ),
            Optional[Dict[str, Plugin]],
            str,
            Plugin,
            id="assign-to-optional-plugin-dict",
        ),
    ],
)
@mark.parametrize(
    "value",
    [
        param(None, id="none"),
        param(MISSING, id="missing"),
        param("${interp}", id="interp"),
    ],
)
def test_list_assign_to_container_typed_element_special(
    cfg: ListConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
) -> None:
    cfg = copy.deepcopy(cfg)

    n = len(cfg)
    for idx in range(n):
        cfg[idx] = value
        check_subnode(cfg, idx, value, type_hint, key_type, elt_type, None)

    cfg.append(value)
    check_subnode(cfg, n, value, type_hint, key_type, elt_type, None)


@mark.parametrize(
    "ensure_container",
    [
        param(True, id="container"),
        param(False, id="no_container"),
    ],
)
@mark.parametrize(
    "cfg, value, type_hint, key_type, elt_type, obj_type",
    [
        param(
            DictConfig({"foo": [[456]]}, element_type=List[List[int]]),
            [[123]],
            List[List[int]],
            int,
            List[int],
            list,
            id="assign-to-list-element",
        ),
        param(
            DictConfig(
                {"foo": {"bar": {"baz": 456}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"qux": {"frob": 123}},
            Dict[str, Dict[str, int]],
            str,
            Dict[str, int],
            dict,
            id="assign-to-dict-element",
        ),
        param(
            DictConfig({"foo": [123], "bar": None}, element_type=Optional[List[int]]),
            [456],
            Optional[List[int]],
            int,
            int,
            list,
            id="assign-list-to-optional-list",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": None},
                element_type=Optional[Dict[str, int]],
            ),
            {"qux": 123},
            Optional[Dict[str, int]],
            str,
            int,
            dict,
            id="assign-dict-to-optional-dict",
        ),
        param(
            DictConfig({"foo": [123], "bar": [None]}, element_type=List[Optional[int]]),
            [456],
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="assign-list-to-list-optional",
        ),
        param(
            DictConfig({"foo": [123], "bar": [None]}, element_type=List[Optional[int]]),
            [None],
            List[Optional[int]],
            int,
            Optional[int],
            list,
            id="assign-list-none-to-list-optional",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": {"qux": None}},
                element_type=Dict[str, Optional[int]],
            ),
            {"frob": 123},
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="assign-dict-to-dict-optional",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": {"qux": None}},
                element_type=Dict[str, Optional[int]],
            ),
            {"frob": None},
            Dict[str, Optional[int]],
            str,
            Optional[int],
            dict,
            id="assign-dict-none-to-dict-optional",
        ),
        param(
            DictConfig({"foo": [ConcretePlugin()]}, element_type=List[Plugin]),
            [ConcretePlugin()],
            List[Plugin],
            int,
            Plugin,
            list,
            id="assign-to-list-of-plugins",
        ),
        param(
            DictConfig(
                {"foo": {"bar": ConcretePlugin()}}, element_type=Dict[str, Plugin]
            ),
            {"baz": ConcretePlugin()},
            Dict[str, Plugin],
            str,
            Plugin,
            dict,
            id="assign-to-dict-of-plugins",
        ),
        param(
            DictConfig({"key": []}, element_type=List[int]),
            DictConfig("${interp}"),
            List[int],
            int,
            int,
            None,
            id="coerce-dictconfig-interp-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Dict[str, int]),
            ListConfig("${interp}"),
            Dict[str, int],
            str,
            int,
            None,
            id="coerce-listconfig-interp-to-dictconfig",
        ),
        param(
            DictConfig({"key": []}, element_type=List[int]),
            DictConfig("${interp}", ref_type=Dict[str, int]),
            List[int],
            int,
            int,
            None,
            id="coerce-dictconfig-interp_with_ref-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Dict[str, int]),
            ListConfig("${interp}", ref_type=List[int]),
            Dict[str, int],
            str,
            int,
            None,
            id="coerce-listconfig-interp_with_ref-to-dictconfig",
        ),
        param(
            DictConfig({"key": []}, element_type=List[int]),
            DictConfig(MISSING),
            List[int],
            int,
            int,
            None,
            id="coerce-dictconfig-missing-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Dict[str, int]),
            ListConfig(MISSING),
            Dict[str, int],
            str,
            int,
            None,
            id="coerce-listconfig-missing-to-dictconfig",
        ),
        param(
            DictConfig({"key": []}, element_type=List[int]),
            DictConfig(MISSING, ref_type=Optional[Dict[str, int]]),
            List[int],
            int,
            int,
            None,
            id="coerce-dictconfig-missing_with_ref-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Dict[str, int]),
            ListConfig(MISSING, ref_type=Optional[List[int]]),
            Dict[str, int],
            str,
            int,
            None,
            id="coerce-listconfig-missing_with_ref-to-dictconfig",
        ),
        param(
            DictConfig({"key": []}, element_type=Optional[List[int]]),
            DictConfig(None),
            Optional[List[int]],
            int,
            int,
            None,
            id="coerce-dictconfig-none-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Optional[Dict[str, int]]),
            ListConfig(None),
            Optional[Dict[str, int]],
            str,
            int,
            None,
            id="coerce-listconfig-none-to-dictconfig",
        ),
        param(
            DictConfig({"key": []}, element_type=Optional[List[int]]),
            DictConfig(None, ref_type=Optional[Dict[str, int]]),
            Optional[List[int]],
            int,
            int,
            None,
            id="coerce-dictconfig-none_with_ref-to-listconfig",
        ),
        param(
            DictConfig({"key": {}}, element_type=Optional[Dict[str, int]]),
            ListConfig(None, ref_type=Optional[List[int]]),
            Optional[Dict[str, int]],
            str,
            int,
            None,
            id="coerce-listconfig-none_with_ref-to-dictconfig",
        ),
    ],
)
def test_dict_assign_to_container_typed_element(
    cfg: DictConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
    ensure_container: bool,
) -> None:
    cfg = copy.deepcopy(cfg)
    if ensure_container:
        value = _ensure_container(value)

    for key in cfg:
        cfg[key] = value
        check_subnode(cfg, key, value, type_hint, key_type, elt_type, obj_type)

    cfg["_new_key"] = value
    check_subnode(cfg, "_new_key", value, type_hint, key_type, elt_type, obj_type)


@mark.parametrize(
    "dc,value",
    [
        param(DictConfig({"key": 123}, element_type=int), 456, id="int"),
        param(DictConfig({"key": [123]}, element_type=List[int]), [456], id="list"),
        param(
            DictConfig({"key": {"foo": 123}}, element_type=Dict[str, int]),
            {"baz": 456},
            id="dict",
        ),
    ],
)
@mark.parametrize("overwrite_preexisting_key", [True, False])
def test_setitem_valid_element_type(
    dc: DictConfig, value: Any, overwrite_preexisting_key: bool
) -> None:
    dc = copy.deepcopy(dc)
    if not overwrite_preexisting_key:
        del dc["key"]
    dc["key"] = value
    assert dc["key"] == value


@mark.parametrize(
    "cfg, type_hint, key_type, elt_type",
    [
        param(
            DictConfig({"foo": [123], "bar": None}, element_type=Optional[List[int]]),
            Optional[List[int]],
            int,
            int,
            id="assign-to-optional-list",
        ),
        param(
            DictConfig(
                {"foo": {"bar": 456}, "baz": None},
                element_type=Optional[Dict[str, int]],
            ),
            Optional[Dict[str, int]],
            str,
            int,
            id="assign-to-optional-dict",
        ),
    ],
)
@mark.parametrize(
    "value",
    [
        param(None, id="none"),
        param(MISSING, id="missing"),
        param("${interp}", id="interp"),
    ],
)
def test_dict_assign_to_container_typed_element_special(
    cfg: DictConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
) -> None:
    cfg = copy.deepcopy(cfg)

    for key in cfg:
        cfg[key] = value
        check_subnode(cfg, key, value, type_hint, key_type, elt_type, None)

    cfg["_new_key"] = value
    check_subnode(cfg, "_new_key", value, type_hint, key_type, elt_type, None)


@mark.parametrize(
    "ensure_container",
    [
        param(True, id="container"),
        param(False, id="no_container"),
    ],
)
@mark.parametrize(
    "overwrite_preexisting_key",
    [
        param(True, id="overwrite"),
        param(False, id="no_overwrite"),
    ],
)
@mark.parametrize(
    "dc,value,err_msg",
    [
        param(
            DictConfig({"key": 123}, element_type=int),
            "foo",
            re.escape("Value 'foo' of type 'str' could not be converted to Integer"),
            id="assign-str-to-int",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            "foo",
            re.escape("Invalid value assigned: str is not a ListConfig, list or tuple"),
            id="assign-str-to-list[int]",
        ),
        param(
            DictConfig({"key": {"foo": 123}}, element_type=Dict[str, int]),
            "bar",
            re.escape("Cannot assign str to Dict[str, int]"),
            id="assign-str-to-list[int]",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            None,
            re.escape("field 'key' is not Optional"),
            id="assign-none-to-list[int]",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            456,
            re.escape("Invalid value assigned: int is not a ListConfig, list or tuple"),
            id="assign-int-to-list[int]",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            ["foo"],
            r"(Value 'foo' of type 'str' could not be converted to Integer)"
            + r"|(Value 'foo' \(str\) is incompatible with type hint 'int')",
            id="assign-list[str]-to-list[int]",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            [None],
            r"(Invalid type assigned: NoneType is not a subclass of int)"
            + r"|(Incompatible value 'None' for field of type 'int')",
            id="assign-list[none]-to-list[int]",
        ),
        param(
            DictConfig({"key": [123]}, element_type=List[int]),
            {"baz": 456},
            r"(Invalid value assigned: dict is not a ListConfig, list or tuple)"
            + r"|(Invalid value assigned: DictConfig is not a ListConfig, list or tuple)"
            + r"|(Invalid value assigned: dict does not match type hint typing\.List\[int\])"
            + r"|('DictConfig' is incompatible with type hint 'typing\.List\[int\]')",
            id="assign-dict[str-int]-to-list[int]]",
        ),
        param(
            DictConfig({"key": {"key2": 123}}, element_type=Dict[str, int]),
            {"key2": "foo"},
            r"(Value 'foo' \(str\) is incompatible with type hint 'int')"
            + r"|(Value 'foo' of type 'str' could not be converted to Integer)",
            id="assign_dict[str_str]_to_dict[str_int]",
        ),
        param(
            DictConfig({"key": {"key2": 123}}, element_type=Dict[str, int]),
            [],
            r"(Invalid type assigned: list is not a subclass of Dict\[str, int\]\. value: \[\])"
            + r"|('ListConfig' is incompatible with type hint 'typing.Dict\[str, int\]')",
            id="assign_list_to_dict[str_int]",
        ),
        param(
            DictConfig({"key": [[123]]}, element_type=List[List[int]]),
            [[456.789]],
            r"(Value 456\.789 \(float\) is incompatible with type hint 'int')"
            + r"|(Value '456\.789' of type 'float' could not be converted to Integer)",
            id="assign-list[list[float]]-to-list[list[int]]",
        ),
        param(
            DictConfig({"key": [[123]]}, element_type=List[List[int]]),
            [[None]],
            r"(Invalid type assigned: NoneType is not a subclass of int)"
            + r"|(Incompatible value 'None' for field of type 'int')",
            id="assign-list[list[none]]-to-list[list[int]]",
        ),
        param(
            DictConfig({"key": [[123]]}, element_type=List[List[int]]),
            [[IntegerNode(None)]],
            r"(Value None \(NoneType\) is incompatible with type hint 'int')"
            + r"|(Incompatible value 'None' for field of type 'int')",
            id="assign-list[list[typed-none]]-to-list[list[int]]",
        ),
        param(
            DictConfig({"key": [[123.456]]}, element_type=List[List[float]]),
            [[IntegerNode(789)]],
            re.escape("Value 789 (int) is incompatible with type hint 'float'"),
            id="assign-list[list[typed-int]]-to-list[list[float]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"foo": {"bar": 456.789}},
            r"(Value 456\.789 \(float\) is incompatible with type hint 'int')"
            + r"|(Value '456\.789' of type 'float' could not be converted to Integer)",
            id="assign-dict[str-[dict[str-float]]]-to-dict[str[dict[str-int]]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"foo": {"bar2": 456.789}},
            r"(Value 456\.789 \(float\) is incompatible with type hint 'int')"
            + r"|(Value '456\.789' of type 'float' could not be converted to Integer)",
            id="assign-dict[str-[dict[str-float]]]-to-dict[str[dict[str-int]]]-2",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"foo": {123: 456}},
            r"(Key 123 \(int\) is incompatible with \(str\))"
            + r"|(Key 123 \(int\) is incompatible with key type hint 'str')",
            id="assign-dict[str_[dict[int_int]]]-to-dict[str[dict[str_int]]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"foo": {456: 789}},
            r"(Key 456 \(int\) is incompatible with \(str\))"
            + r"|(Key 456 \(int\) is incompatible with key type hint 'str')",
            id="assign-dict[str_[dict[int-int]]]-to-dict[str[dict[str_int]]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123}}}, element_type=Dict[str, Dict[str, int]]
            ),
            {"foo": {456: IntegerNode(None)}},
            r"(Key 456 \(int\) is incompatible with \(str\))"
            + r"|(Key 456 \(int\) is incompatible with key type hint 'str')",
            id="assign-dict[str_[dict[int-typed_none]]]-to-dict[str[dict[str_int]]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123.456}}},
                element_type=Dict[str, Dict[str, float]],
            ),
            {"foo": {"bar": IntegerNode(789)}},
            re.escape("Value 789 (int) is incompatible with type hint 'float'"),
            id="assign-dict[str-[dict[int_typed-int]]]-to-dict[str[dict[str-float]]]",
        ),
        param(
            DictConfig(
                {"key": {"foo": {"bar": 123.456}}},
                element_type=Dict[str, Dict[str, float]],
            ),
            {"foo": {"bar2": IntegerNode(789)}},
            re.escape("Value 789 (int) is incompatible with type hint 'float'"),
            id="assign-dict[str-[dict[int_typed-int]]]-to-dict[str[dict[str_float]]]-2",
        ),
    ],
)
def test_dict_setitem_invalid_element_type(
    dc: DictConfig,
    value: Any,
    err_msg: str,
    ensure_container: bool,
    overwrite_preexisting_key: bool,
) -> None:
    dc_orig = dc
    dc = copy.deepcopy(dc)

    if ensure_container:
        if isinstance(value, (dict, list)):
            value = _ensure_container(value)
        else:
            return  # skip

    if overwrite_preexisting_key:
        with raises((ValidationError, KeyValidationError), match=err_msg):
            dc["key"] = value
        assert dc == dc_orig
    else:
        del dc["key"]
        with raises((ValidationError, KeyValidationError), match=err_msg):
            dc["key"] = value
        assert dc == {}


@mark.parametrize(
    "lc,index,value,err_msg",
    [
        param(
            ListConfig([123], element_type=int),
            0,
            "foo",
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="assign_str_to_int",
        ),
        param(
            ListConfig([123], element_type=int),
            0,
            None,
            re.escape("[0] is not optional and cannot be assigned None"),
            id="assign_none_to_int",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            "foo",
            "Invalid value assigned: str is not a ListConfig, list or tuple",
            id="assign_str_to_list[int]",
        ),
        param(
            ListConfig([{"key": 123}], element_type=Dict[str, int]),
            0,
            "foo",
            re.escape("Cannot assign str to Dict[str, int]"),
            id="assign_str_to_dict[str, int]",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            None,
            re.escape("[0] is not optional and cannot be assigned None"),
            id="assign_none_to_list[int]",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            456,
            "Invalid value assigned: int is not a ListConfig, list or tuple",
            id="assign_int_to_list[int]",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            ["foo"],
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="assign_list[str]_to_list[int]",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            [None],
            re.escape("Invalid type assigned: NoneType is not a subclass of int"),
            id="assign_list[none]_to_list[int]",
        ),
        param(
            ListConfig([[123]], element_type=List[int]),
            0,
            {"baz": 456},
            "Invalid value assigned: dict",
            id="assign_dict[str,int]_to_list[int]]",
        ),
        param(
            ListConfig([{"key": 123}], element_type=Dict[str, int]),
            0,
            {"key2": "foo"},
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="assign_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([{"key2": 123}], element_type=Dict[str, int]),
            0,
            {"key2": "foo"},
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="assign_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([], element_type=int),
            None,
            "foo",
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="append_str_to_int",
        ),
        param(
            ListConfig([], element_type=int),
            None,
            None,
            "Invalid type assigned: NoneType is not a subclass of int",
            id="append_none_to_int",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            "foo",
            "Invalid value assigned: str is not a ListConfig, list or tuple",
            id="append_str_to_list[int]",
        ),
        param(
            ListConfig([], element_type=Dict[str, int]),
            None,
            "foo",
            re.escape("Cannot assign str to Dict[str, int]"),
            id="append_str_to_dict[str, int]",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            None,
            re.escape("Invalid type assigned: NoneType is not a subclass of List[int]"),
            id="append_none_to_list[int]",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            456,
            "Invalid value assigned: int is not a ListConfig, list or tuple",
            id="append_int_to_list[int]",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            ["foo"],
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="append_list[str]_to_list[int]",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            [None],
            re.escape("Invalid type assigned: NoneType is not a subclass of int"),
            id="append_list[none]_to_list[int]",
        ),
        param(
            ListConfig([], element_type=List[int]),
            None,
            {"baz": 456},
            "Invalid value assigned: dict",
            id="append_dict[str,int]_to_list[int]]",
        ),
        param(
            ListConfig([], element_type=Dict[str, int]),
            None,
            {"key2": "foo"},
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([], element_type=Dict[str, int]),
            None,
            {"key2": "foo"},
            "Value 'foo' of type 'str' could not be converted to Integer",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig(
                [{"key2": ConcretePlugin()}], element_type=Dict[str, ConcretePlugin]
            ),
            0,
            {"key": Plugin()},
            "Invalid type assigned: Plugin is not a subclass of ConcretePlugin",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([[ConcretePlugin()]], element_type=List[ConcretePlugin]),
            0,
            [Plugin()],
            "Invalid type assigned: Plugin is not a subclass of ConcretePlugin",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([], element_type=Dict[str, ConcretePlugin]),
            None,
            {"key": Plugin()},
            "Invalid type assigned: Plugin is not a subclass of ConcretePlugin",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
        param(
            ListConfig([], element_type=List[ConcretePlugin]),
            None,
            [Plugin()],
            "Invalid type assigned: Plugin is not a subclass of ConcretePlugin",
            id="append_dict[str,str]_to_dict[str,int]",
        ),
    ],
)
def test_list_setitem_invalid_element_type(
    lc: ListConfig,
    index: Optional[int],
    value: Any,
    err_msg: str,
) -> None:
    lc_orig = lc
    lc = copy.deepcopy(lc)
    with raises(ValidationError, match=err_msg):
        if index is None:
            lc.append(value)
        else:
            lc[index] = value
    assert lc == lc_orig


@mark.parametrize(
    "dc1, dc2, value, type_hint, key_type, elt_type, obj_type",
    [
        param(
            DictConfig({"key": {"key2": Plugin()}}, element_type=Dict[str, Plugin]),
            DictConfig({"key": {"key2": ConcretePlugin()}}, element_type=Any),
            ConcretePlugin(),
            Plugin,
            Any,
            Any,
            ConcretePlugin,
            id="any-plugin-into-typed-plugin",
        ),
        param(
            DictConfig({"key": {"key2": Plugin()}}, element_type=Any),
            DictConfig(
                {"key": {"key2": ConcretePlugin()}}, element_type=Dict[str, Plugin]
            ),
            ConcretePlugin(),
            Plugin,
            Any,
            Any,
            ConcretePlugin,
            id="typed-plugin-into-any-plugin",
        ),
        param(
            DictConfig({"key": {"key2": Plugin()}}, element_type=Dict[str, Plugin]),
            DictConfig(
                {"key": {"key2": ConcretePlugin()}},
                element_type=Dict[str, ConcretePlugin],
            ),
            ConcretePlugin(),
            Plugin,
            Any,
            Any,
            ConcretePlugin,
            id="typed-concrete-plugin-into-typed-plugin",
        ),
        param(
            DictConfig({"key": {"key2": {}}}),
            DictConfig({"key": {"key2": Plugin()}}, element_type=Dict[str, Plugin]),
            Plugin(),
            Plugin,
            Any,
            Any,
            Plugin,
            id="typed-plugin-into-any",
        ),
    ],
)
def test_merge_nested_dict_promotion(
    dc1: DictConfig,
    dc2: DictConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    cfg = OmegaConf.merge(dc1, dc2)
    check_subnode(
        cfg.key,
        key="key2",
        value=value,
        type_hint=type_hint,
        key_type=key_type,
        elt_type=elt_type,
        obj_type=obj_type,
    )


@mark.parametrize(
    "configs, keys, value, type_hint, key_type, elt_type, obj_type",
    [
        param(
            [
                DictConfig({}, element_type=Dict[str, List[int]]),
                DictConfig({"foo": {"bar": "${interp}"}}, element_type=Dict[str, Any]),
            ],
            ["foo", "bar"],
            "${interp}",
            List[int],
            int,
            int,
            None,
            id="merge-interp-into-list",
        ),
        param(
            [
                DictConfig({}, element_type=Dict[str, Optional[List[int]]]),
                DictConfig({"foo": {"bar": None}}, element_type=Dict[str, Any]),
            ],
            ["foo", "bar"],
            None,
            Optional[List[int]],
            int,
            int,
            None,
            id="merge-none-into-list",
        ),
        param(
            [
                DictConfig({}, element_type=Dict[str, Dict[str, int]]),
                DictConfig({"foo": {"bar": "${interp}"}}, element_type=Dict[str, Any]),
            ],
            ["foo", "bar"],
            "${interp}",
            Dict[str, int],
            str,
            int,
            None,
            id="merge-interp-into-dict",
        ),
        param(
            [
                DictConfig({}, element_type=Dict[str, Optional[Dict[str, int]]]),
                DictConfig({"foo": {"bar": None}}, element_type=Dict[str, Any]),
            ],
            ["foo", "bar"],
            None,
            Optional[Dict[str, int]],
            str,
            int,
            None,
            id="merge-none-into-dict",
        ),
    ],
)
def test_merge_nested(
    configs: List[Any],
    keys: List[Any],
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    """Ensure metadata and contents of container-typed subnode are correct"""
    cfg = OmegaConf.merge(*configs)
    for key in keys[:-1]:
        cfg = cfg._get_node(key)  # type: ignore
    key = keys[-1]
    check_subnode(
        cfg,
        key,
        value,
        type_hint,
        key_type,
        elt_type,
        obj_type,
    )


@mark.parametrize(
    "dc1, dc2, value, type_hint, key_type, elt_type, obj_type",
    [
        param(
            DictConfig({"key": {}}),
            DictConfig({"key": "${interp}"}, element_type=Dict[str, int]),
            "${interp}",
            Dict[str, int],
            str,
            int,
            None,
            id="dict-interp-into-any",
        ),
        param(
            DictConfig({"key": {}}),
            DictConfig({"key": None}, element_type=Optional[Dict[str, int]]),
            None,
            Optional[Dict[str, int]],
            str,
            int,
            None,
            id="none-interp-into-any",
        ),
        param(
            DictConfig({"key": {"foo": 123}}, element_type=Dict[str, Any]),
            DictConfig({"key": {"bar": 456.789}}, element_type=Dict[str, float]),
            {"foo": 123, "bar": 456.789},
            Dict[str, Any],
            str,
            Any,
            dict,
            id="dict[str,float]-into-dict[str,any]",
        ),
        param(
            DictConfig({"key": {}}, element_type=Dict[str, int]),
            DictConfig({"key": "${interp}"}),
            "${interp}",
            Dict[str, int],
            str,
            int,
            None,
            id="interp-into-dict",
        ),
        param(
            DictConfig({"key": []}),
            DictConfig({"key": "${interp}"}, element_type=List[int]),
            "${interp}",
            Any,
            int,
            Any,
            None,
            id="list-interp-into-any",
        ),
        param(
            DictConfig({"key": []}, element_type=List[int]),
            DictConfig({"key": "${interp}"}),
            "${interp}",
            List[int],
            int,
            int,
            None,
            id="any-interp-into-list-int",
        ),
        param(
            DictConfig({"key": []}, element_type=List[float]),
            DictConfig({"key": ["${interp}"]}, element_type=List[int]),
            ["${interp}"],
            List[float],
            int,
            float,
            list,
            id="any-interp_list-into-list-list-int",
        ),
    ],
)
def test_merge_interpolation_with_container_type(
    dc1: DictConfig,
    dc2: DictConfig,
    value: Any,
    type_hint: Any,
    key_type: Any,
    elt_type: Any,
    obj_type: Any,
) -> None:
    cfg = OmegaConf.merge(dc1, dc2)
    check_subnode(
        cfg,
        key="key",
        value=value,
        type_hint=type_hint,
        key_type=key_type,
        elt_type=elt_type,
        obj_type=obj_type,
    )


def test_merge_nested_list_promotion() -> None:
    dc1 = DictConfig({"key": [Plugin]}, element_type=List[Plugin])
    dc2 = DictConfig({"key": [ConcretePlugin]})
    cfg = OmegaConf.merge(dc1, dc2)
    check_subnode(
        cfg.key,
        key=0,
        value=ConcretePlugin(),
        type_hint=Plugin,
        key_type=Any,
        elt_type=Any,
        obj_type=ConcretePlugin,
    )


@mark.parametrize(
    "configs, err_msg",
    [
        param(
            [DictConfig({}, element_type=int), {"foo": "abc"}],
            "Value 'abc' of type 'str' could not be converted to Integer",
        ),
        param(
            [DictConfig({}, element_type=Dict[str, int]), {"foo": 123}],
            "Value 123 (int) is incompatible with type hint 'typing.Dict[str, int]'",
            id="merge-int-into-dict",
        ),
        param(
            [
                DictConfig({}, element_type=Dict[str, Dict[str, int]]),
                DictConfig(
                    {"foo": {"bar": None}}, element_type=Dict[str, Optional[int]]
                ),
            ],
            "field 'foo.bar' is not Optional",
            id="merge-none_typed-into-int",
        ),
    ],
)
def test_merge_bad_element_type(configs: Any, err_msg: Any) -> None:
    with raises(
        ValidationError,
        match=re.escape(err_msg),
    ):
        OmegaConf.merge(*configs)
