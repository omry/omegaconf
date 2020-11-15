# -*- coding: utf-8 -*-
import io
import os
import pathlib
import pickle
import tempfile
from enum import Enum
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, List, Optional, Type, Union

import pytest

from omegaconf import DictConfig, ListConfig, OmegaConf
from omegaconf._utils import get_ref_type

from . import (
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


@pytest.mark.parametrize(  # type: ignore
    "obj,ref_type",
    [
        ({"a": "b"}, Dict[Union[str, Enum], Any]),
        ([1, 2, 3], List[Any]),
    ],
)
def test_pickle(obj: Any, ref_type: Any) -> None:
    with tempfile.TemporaryFile() as fp:
        c = OmegaConf.create(obj)
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1
        assert get_ref_type(c1) == Optional[ref_type]
        assert c1._metadata.element_type is Any
        assert c1._metadata.optional is True
        if isinstance(c, DictConfig):
            assert c1._metadata.key_type is Any


def test_load_duplicate_keys_top() -> None:
    from yaml.constructor import ConstructorError

    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            content = dedent(
                """\
                a:
                  b: 1
                a:
                  b: 2
                """
            )
            fp.write(content.encode("utf-8"))
        with pytest.raises(ConstructorError):
            OmegaConf.load(fp.name)
    finally:
        os.unlink(fp.name)


def test_load_duplicate_keys_sub() -> None:
    from yaml.constructor import ConstructorError

    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            content = dedent(
                """\
                a:
                  b: 1
                  c: 2
                  b: 3
                """
            )
            fp.write(content.encode("utf-8"))
        with pytest.raises(ConstructorError):
            OmegaConf.load(fp.name)
    finally:
        os.unlink(fp.name)


def test_load_empty_file(tmpdir: str) -> None:
    empty = Path(tmpdir) / "test.yaml"
    empty.touch()

    assert OmegaConf.load(empty) == {}

    with open(empty) as f:
        assert OmegaConf.load(f) == {}


@pytest.mark.parametrize(  # type: ignore
    "input_,node,element_type,key_type,optional,ref_type",
    [
        (UntypedList, "list", Any, Any, False, List[Any]),
        (UntypedList, "opt_list", Any, Any, True, Optional[List[Any]]),
        (UntypedDict, "dict", Any, Any, False, Dict[Union[str, Enum], Any]),
        (
            UntypedDict,
            "opt_dict",
            Any,
            Any,
            True,
            Optional[Dict[Union[str, Enum], Any]],
        ),
        (SubscriptedDict, "dict", int, str, False, Dict[str, int]),
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
