# -*- coding: utf-8 -*-
import io
import os
import pathlib
import pickle
import re
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Type

from pytest import mark, param, raises

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf
from omegaconf._utils import get_type_hint
from omegaconf.errors import OmegaConfBaseException
from tests import (
    Color,
    NestedContainers,
    PersonA,
    PersonD,
    SubscriptedDict,
    SubscriptedDictOpt,
    SubscriptedList,
    SubscriptedListOpt,
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
            OmegaConf.save(conf, fp.file, resolve=resolve)
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
    with raises(TypeError):
        OmegaConf.load(3.1415)  # type: ignore


@mark.parametrize(
    "input_,resolve,expected,file_class",
    [
        ({"a": 10}, False, None, str),
        ({"foo": 10, "bar": "${foo}"}, False, None, str),
        ({"foo": 10, "bar": "${foo}"}, False, None, pathlib.Path),
        ({"foo": 10, "bar": "${foo}"}, False, {"foo": 10, "bar": 10}, str),
        (["שלום"], False, None, str),
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


@mark.parametrize(
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
    with raises(TypeError):
        OmegaConf.save(OmegaConf.create(), 1000)  # type: ignore


@mark.parametrize("obj", [param({"a": "b"}, id="dict"), param([1, 2, 3], id="list")])
def test_pickle(obj: Any) -> None:
    with tempfile.TemporaryFile() as fp:
        c = OmegaConf.create(obj)
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1
        assert get_type_hint(c1) == Any
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


@mark.parametrize(
    "input_,node,element_type,key_type,optional,ref_type",
    [
        param(UntypedList, "list", Any, Any, False, List[Any], id="list_untyped"),
        param(
            UntypedList,
            "opt_list",
            Any,
            Any,
            True,
            Optional[List[Any]],
            id="opt_list_untyped",
        ),
        param(UntypedDict, "dict", Any, Any, False, Dict[Any, Any], id="dict_untyped"),
        param(
            UntypedDict,
            "opt_dict",
            Any,
            Any,
            True,
            Optional[Dict[Any, Any]],
            id="opt_dict_untyped",
        ),
        param(
            SubscriptedDict, "dict_str", int, str, False, Dict[str, int], id="dict_str"
        ),
        param(
            SubscriptedDict,
            "dict_bytes",
            int,
            bytes,
            False,
            Dict[bytes, int],
            id="dict_bytes",
        ),
        param(
            SubscriptedDict, "dict_int", int, int, False, Dict[int, int], id="dict_int"
        ),
        param(
            SubscriptedDict,
            "dict_bool",
            int,
            bool,
            False,
            Dict[bool, int],
            id="dict_bool",
        ),
        param(
            SubscriptedDict,
            "dict_float",
            int,
            float,
            False,
            Dict[float, int],
            id="dict_float",
        ),
        param(
            SubscriptedDict,
            "dict_enum",
            int,
            Color,
            False,
            Dict[Color, int],
            id="dict_enum",
        ),
        param(SubscriptedList, "list", int, Any, False, List[int], id="list_int"),
        param(
            SubscriptedDictOpt,
            "opt_dict",
            int,
            str,
            True,
            Optional[Dict[str, int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="opt_dict",
        ),
        param(
            SubscriptedDictOpt,
            "dict_opt",
            Optional[int],
            str,
            False,
            Dict[str, Optional[int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="dict_opt",
        ),
        param(
            SubscriptedListOpt,
            "opt_list",
            int,
            str,
            True,
            Optional[List[int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="opt_list",
        ),
        param(
            SubscriptedListOpt,
            "list_opt",
            Optional[int],
            str,
            False,
            List[Optional[int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="list_opt",
        ),
        param(
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
        param(
            NestedContainers,
            "dict_of_dict",
            Dict[str, int],
            str,
            False,
            Dict[str, Dict[str, int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="dict-of-dict",
        ),
        param(
            NestedContainers,
            "list_of_list",
            List[int],
            int,
            False,
            List[List[int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="list-of-list",
        ),
        param(
            NestedContainers,
            "dict_of_list",
            List[int],
            str,
            False,
            Dict[str, List[int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="dict-of-list",
        ),
        param(
            NestedContainers,
            "list_of_dict",
            Dict[str, int],
            int,
            False,
            List[Dict[str, int]],
            marks=mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7"),
            id="list-of-dict",
        ),
    ],
)
def test_pickle_untyped(
    input_: Any,
    node: Optional[str],
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

        def get_node(cfg: Any, key: Optional[str]) -> Any:
            if key is None:
                return cfg
            else:
                return cfg._get_node(key)

        assert cfg == cfg2
        assert get_type_hint(get_node(cfg2, node)) == ref_type
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


@mark.parametrize(
    "version",
    [
        "2.0.6",
        "2.1.0.rc1",
    ],
)
def test_pickle_backward_compatibility(version: str) -> None:
    path = Path(__file__).parent / "data" / f"{version}.pickle"
    with open(path, mode="rb") as fp:
        cfg = pickle.load(fp)
        assert cfg == OmegaConf.create({"a": [{"b": 10}]})


@mark.skipif(sys.version_info >= (3, 7), reason="requires python3.6")
def test_python36_pickle_optional() -> None:
    cfg = OmegaConf.structured(SubscriptedDictOpt)
    with raises(
        OmegaConfBaseException,
        match=re.escape(
            "Serializing structured configs with `Union` element type requires python >= 3.7"
        ),
    ):
        pickle.dumps(cfg)
