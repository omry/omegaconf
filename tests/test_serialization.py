# -*- coding: utf-8 -*-
import io
import os
import pathlib
import pickle
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

import pytest

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf._utils import get_ref_type
from tests import (
    Color,
    PersonA,
    PersonD,
    SubscriptedDict,
    SubscriptedList,
    UntypedDict,
    UntypedList,
)


def save_load_from_file(conf: Any, resolve: bool, expected: Any) -> None:
    if expected is None:
        expected = conf
    try:
        with tempfile.NamedTemporaryFile(
            mode="wt", delete=False, encoding="utf-8"
        ) as fp:
            OmegaConf.save(conf, fp.file, resolve=resolve)  # type: ignore
        with io.open(os.path.abspath(fp.name), "rt", encoding="utf-8") as handle:
            c2 = OmegaConf.load(handle)
        assert c2 == expected
    finally:
        os.unlink(fp.name)


def save_load_from_filename(
    conf: Any, resolve: bool, expected: Any, file_class: Type[Any]
) -> None:
    if expected is None:
        expected = conf
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            filepath = file_class(fp.name)
            OmegaConf.save(conf, filepath, resolve=resolve)
            c2 = OmegaConf.load(filepath)
            assert c2 == expected
    finally:
        os.unlink(fp.name)


def test_load_from_invalid() -> None:
    with pytest.raises(TypeError):
        OmegaConf.load(3.1415)  # type: ignore


@pytest.mark.parametrize(
    "input_,resolve,expected,file_class",
    [
        ({"a": 10}, False, None, str),
        ({"foo": 10, "bar": "${foo}"}, False, None, str),
        ({"foo": 10, "bar": "${foo}"}, False, None, pathlib.Path),
        ({"foo": 10, "bar": "${foo}"}, False, {"foo": 10, "bar": 10}, str),
        ([u"שלום"], False, None, str),
    ],
)
class TestSaveLoad:
    def test_save_load__from_file(
        self,
        input_: Dict[str, Any],
        resolve: bool,
        expected: Any,
        file_class: Type[Any],
    ) -> None:
        cfg = OmegaConf.create(input_)
        save_load_from_file(cfg, resolve, expected)

    def test_save_load__from_filename(
        self,
        input_: Dict[str, Any],
        resolve: bool,
        expected: Any,
        file_class: Type[Any],
    ) -> None:
        cfg = OmegaConf.create(input_)
        save_load_from_filename(cfg, resolve, expected, file_class)


@pytest.mark.parametrize(
    "input_,resolve,expected,file_class",
    [
        (PersonA, False, {"age": 18, "registered": True}, str),
        (PersonD, False, {"age": 18, "registered": True}, str),
        (PersonA(), False, {"age": 18, "registered": True}, str),
        (PersonD(), False, {"age": 18, "registered": True}, str),
    ],
)
class TestSaveLoadStructured:
    def test_save_load__from_file(
        self,
        input_: Dict[str, Any],
        resolve: bool,
        expected: Any,
        file_class: Type[Any],
    ) -> None:
        save_load_from_file(input_, resolve, expected)

    def test_save_load__from_filename(
        self,
        input_: Dict[str, Any],
        resolve: bool,
        expected: Any,
        file_class: Type[Any],
    ) -> None:
        save_load_from_filename(input_, resolve, expected, file_class)


def test_save_illegal_type() -> None:
    with pytest.raises(TypeError):
        OmegaConf.save(OmegaConf.create(), 1000)  # type: ignore


@pytest.mark.parametrize(
    "obj", [pytest.param({"a": "b"}, id="dict"), pytest.param([1, 2, 3], id="list")]
)
def test_pickle(obj: Any) -> None:
    with tempfile.TemporaryFile() as fp:
        c = OmegaConf.create(obj)
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1
        assert get_ref_type(c1) == Any
        assert c1._metadata.element_type is Any
        assert c1._metadata.optional is True
        if isinstance(c, DictConfig):
            assert c1._metadata.key_type is Any


def test_load_empty_file(tmpdir: str) -> None:
    empty = Path(tmpdir) / "test.yaml"
    empty.touch()

    assert OmegaConf.load(empty) == {}

    with open(empty) as f:
        assert OmegaConf.load(f) == {}


@pytest.mark.parametrize(
    "input_,node,element_type,key_type,optional,ref_type",
    [
        (UntypedList, "list", Any, Any, False, List[Any]),
        (UntypedList, "opt_list", Any, Any, True, Optional[List[Any]]),
        (UntypedDict, "dict", Any, Any, False, Dict[Any, Any]),
        (
            UntypedDict,
            "opt_dict",
            Any,
            Any,
            True,
            Optional[Dict[Any, Any]],
        ),
        (SubscriptedDict, "dict_str", int, str, False, Dict[str, int]),
        (SubscriptedDict, "dict_int", int, int, False, Dict[int, int]),
        (SubscriptedDict, "dict_bool", int, bool, False, Dict[bool, int]),
        (SubscriptedDict, "dict_float", int, float, False, Dict[float, int]),
        (SubscriptedDict, "dict_enum", int, Color, False, Dict[Color, int]),
        (SubscriptedList, "list", int, Any, False, List[int]),
        (
            DictConfig(
                content={"a": "foo"},
                ref_type=Dict[str, str],
                element_type=str,
                key_type=str,
            ),
            None,
            str,
            str,
            True,
            Optional[Dict[str, str]],
        ),
        (
            ListConfig(content=[1, 2], ref_type=List[int], element_type=int),
            None,
            int,
            Any,
            True,
            Optional[List[int]],
        ),
    ],
)
def test_pickle_untyped(
    input_: Any,
    node: str,
    optional: bool,
    element_type: Any,
    key_type: Any,
    ref_type: Any,
) -> None:
    cfg = OmegaConf.structured(input_)
    with tempfile.TemporaryFile() as fp:
        import pickle

        pickle.dump(cfg, fp)
        fp.flush()
        fp.seek(0)
        cfg2 = pickle.load(fp)

        def get_node(cfg: Any, key: str) -> Any:
            if key is None:
                return cfg
            else:
                return cfg._get_node(key)

        assert cfg == cfg2
        assert get_ref_type(get_node(cfg2, node)) == ref_type
        assert get_node(cfg2, node)._metadata.element_type == element_type
        assert get_node(cfg2, node)._metadata.optional == optional
        if isinstance(input_, DictConfig):
            assert get_node(cfg2, node)._metadata.key_type == key_type


def test_pickle_missing() -> None:
    cfg = DictConfig(content=MISSING)
    with tempfile.TemporaryFile() as fp:
        import pickle

        pickle.dump(cfg, fp)
        fp.flush()
        fp.seek(0)
        cfg2 = pickle.load(fp)
        assert cfg == cfg2


def test_pickle_none() -> None:
    cfg = DictConfig(content=None)
    with tempfile.TemporaryFile() as fp:
        import pickle

        pickle.dump(cfg, fp)
        fp.flush()
        fp.seek(0)
        cfg2 = pickle.load(fp)
        assert cfg == cfg2


def test_pickle_flags_consistency() -> None:
    cfg = OmegaConf.create({"a": 0})
    cfg._set_flag("test", True)
    assert cfg._get_node("a")._get_flag("test")  # type: ignore

    cfg2 = pickle.loads(pickle.dumps(cfg))
    cfg2._set_flag("test", None)
    assert cfg2._get_flag("test") is None
    assert cfg2._get_node("a")._get_flag("test") is None
