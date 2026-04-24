"""
Tests for Union[List[...], Dict[...], ...] support (issue #1261).
"""

import copy
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

from pytest import mark, param, raises

from omegaconf import ListMergeMode, OmegaConf, ValidationError
from omegaconf._utils import is_supported_union_annotation

# ---------------------------------------------------------------------------
# Dataclasses for structured-config tests
# ---------------------------------------------------------------------------


@dataclass
class CfgIntOrListStr:
    value: Union[int, List[str]] = 0


@dataclass
class CfgIntOrDictStrInt:
    value: Union[int, Dict[str, int]] = 0


@dataclass
class CfgListIntOrListStr:
    value: Union[List[int], List[str]] = field(default_factory=lambda: [1, 2])


@dataclass
class CfgDictStrIntOrDictStrStr:
    value: Union[Dict[str, int], Dict[str, str]] = field(
        default_factory=lambda: {"x": 1}
    )


@dataclass
class CfgDictOrList:
    value: Union[Dict[str, int], List[int]] = field(default_factory=lambda: [1])


@dataclass
class CfgMissing:
    value: Union[List[int], List[str]] = field(default_factory=lambda: [1])


# ---------------------------------------------------------------------------
# is_supported_union_annotation
# ---------------------------------------------------------------------------


class TestIsSupportedUnionAnnotation:
    @mark.parametrize(
        "annotation, expected",
        [
            param(Union[int, List[str]], True, id="int_list_str"),
            param(Union[int, Dict[str, int]], True, id="int_dict_str_int"),
            param(Union[List[int], List[str]], True, id="list_int_list_str"),
            param(
                Union[Dict[str, int], Dict[str, str]],
                True,
                id="dict_str_int_dict_str_str",
            ),
            param(Union[Dict[str, int], List[int]], True, id="dict_str_int_list_int"),
            param(Optional[Union[int, List[str]]], True, id="optional_int_list_str"),
            # These should still be unsupported (structured configs in unions)
            param(Union[int, str], True, id="int_str_still_ok"),
        ],
    )
    def test_is_supported(self, annotation: Any, expected: bool) -> None:
        assert is_supported_union_annotation(annotation) == expected


# ---------------------------------------------------------------------------
# Structured config creation
# ---------------------------------------------------------------------------


class TestStructuredConfigCreation:
    @mark.parametrize(
        "cls, expected",
        [
            param(CfgIntOrListStr, 0, id="int_or_list_str"),
            param(CfgIntOrDictStrInt, 0, id="int_or_dict_str_int"),
            param(CfgListIntOrListStr, [1, 2], id="list_int_or_list_str"),
            param(
                CfgDictStrIntOrDictStrStr,
                {"x": 1},
                id="dict_str_int_or_dict_str_str",
            ),
            param(CfgDictOrList, [1], id="dict_or_list"),
        ],
    )
    def test_create(self, cls: Any, expected: Any) -> None:
        cfg = OmegaConf.structured(cls)
        assert cfg.value == expected


# ---------------------------------------------------------------------------
# Branch selection
# ---------------------------------------------------------------------------


class TestBranchSelection:
    """Assignment should pick the right union branch based on value content."""

    @mark.parametrize(
        "cls, value, expected",
        [
            param(CfgIntOrListStr, ["a", "b"], ["a", "b"], id="int_or_list_list"),
            param(CfgIntOrListStr, 42, 42, id="int_or_list_int"),
            param(CfgIntOrDictStrInt, {"x": 1}, {"x": 1}, id="int_or_dict_dict"),
            param(CfgListIntOrListStr, [1, 2, 3], [1, 2, 3], id="list_int"),
            param(CfgListIntOrListStr, ["a", "b"], ["a", "b"], id="list_str"),
            param(CfgDictStrIntOrDictStrStr, {"x": 1}, {"x": 1}, id="dict_int"),
            param(
                CfgDictStrIntOrDictStrStr,
                {"x": "hello"},
                {"x": "hello"},
                id="dict_str",
            ),
            param(CfgDictOrList, [10, 20], [10, 20], id="dict_or_list_list"),
            param(CfgDictOrList, {"a": 1}, {"a": 1}, id="dict_or_list_dict"),
        ],
    )
    def test_value_selects_branch(self, cls: Any, value: Any, expected: Any) -> None:
        cfg = OmegaConf.structured(cls)
        cfg.value = value
        assert cfg.value == expected

    def test_mismatched_list_raises(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        with raises(ValidationError):
            cfg.value = [1, "a"]  # mixed — matches neither List[int] nor List[str]

    def test_wrong_type_raises(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrListStr)
        with raises(ValidationError):
            cfg.value = {"x": 1}  # dict when only int or List[str] allowed


# ---------------------------------------------------------------------------
# Ambiguity errors for empty containers
# ---------------------------------------------------------------------------


class TestAmbiguity:
    @mark.parametrize(
        "cls, value",
        [
            param(CfgListIntOrListStr, [], id="empty_list"),
            param(CfgDictStrIntOrDictStrStr, {}, id="empty_dict"),
            param(CfgListIntOrListStr, (), id="empty_tuple"),
        ],
    )
    def test_empty_container_is_ambiguous(self, cls: Any, value: Any) -> None:
        cfg = OmegaConf.structured(cls)
        with raises(ValidationError, match="[Aa]mbig"):
            cfg.value = value

    @mark.parametrize(
        "cls, value, expected",
        [
            param(CfgIntOrDictStrInt, {}, {}, id="single_dict_branch"),
            param(CfgIntOrListStr, [], [], id="single_list_branch"),
        ],
    )
    def test_empty_container_with_one_branch_is_not_ambiguous(
        self, cls: Any, value: Any, expected: Any
    ) -> None:
        cfg = OmegaConf.structured(cls)
        cfg.value = value
        assert cfg.value == expected

    def test_nonempty_tuple_selects_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrListStr)
        cfg.value = ("a", "b")
        assert cfg.value == ["a", "b"]


# ---------------------------------------------------------------------------
# OmegaConf.typed_list / typed_dict — explicit disambiguation
# ---------------------------------------------------------------------------


class TestTypedContainers:
    def test_typed_list_str_disambiguates(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        typed = OmegaConf.typed_list([], element_type=str)
        cfg.value = typed
        assert cfg.value == []
        cfg.value.append("hello")
        assert cfg.value == ["hello"]

    def test_typed_list_int_disambiguates(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        typed = OmegaConf.typed_list([], element_type=int)
        cfg.value = typed
        assert cfg.value == []
        cfg.value.append(42)
        assert cfg.value == [42]

    def test_typed_dict_int_disambiguates(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        typed = OmegaConf.typed_dict({}, key_type=str, element_type=int)
        cfg.value = typed
        assert cfg.value == {}
        cfg.value["x"] = 10
        assert cfg.value == {"x": 10}

    def test_typed_dict_str_disambiguates(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        typed = OmegaConf.typed_dict({}, key_type=str, element_type=str)
        cfg.value = typed
        assert cfg.value == {}
        cfg.value["x"] = "hello"
        assert cfg.value == {"x": "hello"}

    def test_typed_list_standalone(self) -> None:
        lst = OmegaConf.typed_list([1, 2, 3], element_type=int)
        assert list(lst) == [1, 2, 3]

    def test_typed_dict_standalone(self) -> None:
        d = OmegaConf.typed_dict({"a": 1}, key_type=str, element_type=int)
        assert dict(d) == {"a": 1}

    def test_typed_list_wrong_element_raises(self) -> None:
        lst = OmegaConf.typed_list(element_type=int)
        lst.append(1)
        with raises(ValidationError):
            lst.append("bad")

    def test_typed_dict_wrong_value_raises(self) -> None:
        d = OmegaConf.typed_dict(key_type=str, element_type=int)
        d["x"] = 1
        with raises(ValidationError):
            d["y"] = "bad"


# ---------------------------------------------------------------------------
# Validation after branch selection
# ---------------------------------------------------------------------------


class TestValidationAfterSelection:
    def test_list_int_rejects_str_append(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        cfg.value = [1, 2]
        with raises(ValidationError):
            cfg.value.append("x")  # type: ignore

    def test_list_str_rejects_int_append(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        cfg.value = ["a", "b"]
        with raises(ValidationError):
            cfg.value.append(99)  # type: ignore

    def test_dict_str_int_rejects_str_value(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        cfg.value = {"x": 1}
        with raises(ValidationError):
            cfg.value["y"] = "bad"  # type: ignore

    def test_dict_str_str_rejects_int_value(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        cfg.value = {"x": "hello"}
        with raises(ValidationError):
            cfg.value["y"] = 999  # type: ignore


# ---------------------------------------------------------------------------
# to_container / to_object
# ---------------------------------------------------------------------------


class TestToContainer:
    def test_to_container_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrListStr)
        cfg.value = ["a", "b"]
        plain = OmegaConf.to_container(cfg)
        assert plain == {"value": ["a", "b"]}

    def test_to_container_dict_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrDictStrInt)
        cfg.value = {"x": 1}
        plain = OmegaConf.to_container(cfg)
        assert plain == {"value": {"x": 1}}

    def test_to_object_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrListStr)
        cfg.value = ["a", "b"]
        obj = OmegaConf.to_object(cfg)
        assert obj.value == ["a", "b"]  # type: ignore
        assert type(obj.value) is list  # type: ignore


# ---------------------------------------------------------------------------
# Deepcopy and pickle
# ---------------------------------------------------------------------------


class TestDeepCopyAndPickle:
    def test_deepcopy_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        cfg.value = [1, 2, 3]
        cfg2 = copy.deepcopy(cfg)
        assert cfg2.value == [1, 2, 3]
        cfg2.value.append(4)
        assert cfg.value == [1, 2, 3]  # original unchanged

    def test_deepcopy_dict_branch(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        cfg.value = {"x": 1}
        cfg2 = copy.deepcopy(cfg)
        assert cfg2.value == {"x": 1}

    def test_pickle_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        cfg.value = [1, 2, 3]
        data = pickle.dumps(cfg)
        cfg2 = pickle.loads(data)
        assert cfg2.value == [1, 2, 3]

    def test_pickle_dict_branch(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        cfg.value = {"x": "hello"}
        data = pickle.dumps(cfg)
        cfg2 = pickle.loads(data)
        assert cfg2.value == {"x": "hello"}


# ---------------------------------------------------------------------------
# Merge behavior
# ---------------------------------------------------------------------------


class TestMerge:
    def test_merge_list_branch(self) -> None:
        cfg1 = OmegaConf.structured(CfgListIntOrListStr)
        cfg1.value = [1, 2]
        cfg2 = OmegaConf.structured(CfgListIntOrListStr)
        cfg2.value = [3, 4]
        merged = OmegaConf.merge(cfg1, cfg2)
        assert merged.value == [3, 4]

    def test_merge_structured_config_changes_branch(self) -> None:
        cfg1 = OmegaConf.structured(CfgListIntOrListStr)
        cfg1.value = [1, 2]
        cfg2 = OmegaConf.structured(CfgListIntOrListStr)
        cfg2.value = ["a", "b"]
        merged = OmegaConf.merge(cfg1, cfg2)
        assert merged.value == ["a", "b"]

    def test_merge_into_int_or_list_selects_list_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrListStr)
        merged = OmegaConf.merge(cfg, {"value": ["x", "y"]})
        assert merged.value == ["x", "y"]

    def test_merge_into_int_or_dict_selects_dict_branch(self) -> None:
        cfg = OmegaConf.structured(CfgIntOrDictStrInt)
        merged = OmegaConf.merge(cfg, {"value": {"a": 1}})
        assert merged.value == {"a": 1}

    @mark.parametrize(
        "merge",
        [
            param(OmegaConf.merge, id="merge"),
            param(OmegaConf.unsafe_merge, id="unsafe_merge"),
        ],
    )
    def test_merge_plain_list_selects_branch(self, merge: Any) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        merged = merge(cfg, {"value": ["a", "b"]})
        assert merged.value == ["a", "b"]

    @mark.parametrize(
        "merge",
        [
            param(OmegaConf.merge, id="merge"),
            param(OmegaConf.unsafe_merge, id="unsafe_merge"),
        ],
    )
    def test_merge_plain_dict_selects_dict_branch(self, merge: Any) -> None:
        cfg = OmegaConf.structured(CfgDictOrList)
        merged = merge(cfg, {"value": {"a": 1}})
        assert merged.value == {"a": 1}

    def test_merge_with_plain_dict_selects_dict_branch(self) -> None:
        cfg = OmegaConf.structured(CfgDictOrList)
        cfg.merge_with({"value": {"a": 1}})
        assert cfg.value == {"a": 1}

    @mark.parametrize(
        "merge",
        [
            param(OmegaConf.merge, id="merge"),
            param(OmegaConf.unsafe_merge, id="unsafe_merge"),
        ],
    )
    def test_merge_empty_list_is_ambiguous(self, merge: Any) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        with raises(ValidationError, match="[Aa]mbig"):
            merge(cfg, {"value": []})

    def test_merge_with_empty_list_is_ambiguous(self) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        with raises(ValidationError, match="[Aa]mbig"):
            cfg.merge_with({"value": []})

    @mark.parametrize(
        "merge",
        [
            param(OmegaConf.merge, id="merge"),
            param(OmegaConf.unsafe_merge, id="unsafe_merge"),
        ],
    )
    def test_merge_empty_dict_is_ambiguous(self, merge: Any) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        with raises(ValidationError, match="[Aa]mbig"):
            merge(cfg, {"value": {}})

    def test_merge_with_empty_dict_is_ambiguous(self) -> None:
        cfg = OmegaConf.structured(CfgDictStrIntOrDictStrStr)
        with raises(ValidationError, match="[Aa]mbig"):
            cfg.merge_with({"value": {}})

    @mark.parametrize(
        "list_merge_mode",
        [
            param(ListMergeMode.REPLACE, id="replace"),
            param(ListMergeMode.EXTEND, id="extend"),
            param(ListMergeMode.EXTEND_UNIQUE, id="extend_unique"),
        ],
    )
    def test_list_merge_mode_replaces_union_branch(
        self, list_merge_mode: ListMergeMode
    ) -> None:
        cfg = OmegaConf.structured(CfgListIntOrListStr)
        merged = OmegaConf.merge(
            cfg,
            {"value": [2, 3]},
            list_merge_mode=list_merge_mode,
        )
        assert merged.value == [2, 3]


# ---------------------------------------------------------------------------
# Interpolation into container union
# ---------------------------------------------------------------------------


class TestInterpolation:
    def test_interpolation_resolves_to_list(self) -> None:
        @dataclass
        class Cfg:
            items: List[int] = field(default_factory=lambda: [1, 2, 3])
            value: Union[int, List[int]] = 0

        cfg = OmegaConf.structured(Cfg)
        cfg.value = "${items}"
        assert cfg.value == [1, 2, 3]

    def test_missing_is_accepted(self) -> None:
        @dataclass
        class Cfg:
            value: Union[List[int], List[str]] = field(default_factory=lambda: [1])

        cfg = OmegaConf.structured(Cfg)
        cfg.value = "???"
        from omegaconf import MissingMandatoryValue

        with raises(MissingMandatoryValue):
            _ = cfg.value
