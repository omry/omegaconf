# -*- coding: utf-8 -*-
import io
import os
import pathlib
import pickle
import tempfile
from pathlib import Path
from textwrap import dedent
from typing import Any, Dict, Type

import pytest

from omegaconf import OmegaConf

from . import PersonA, PersonD


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


def test_pickle_dict() -> None:
    with tempfile.TemporaryFile() as fp:
        c = OmegaConf.create({"a": "b"})
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1


def test_pickle_list() -> None:
    with tempfile.TemporaryFile() as fp:
        c = OmegaConf.create([1, 2, 3])
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1


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
