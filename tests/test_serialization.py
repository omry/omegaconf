# -*- coding: utf-8 -*-
import io
import os
import tempfile

import pytest

from omegaconf import OmegaConf


def save_load_from_file(conf, resolve, expected):
    if expected is None:
        expected = conf
    try:
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as fp:
            OmegaConf.save(conf, fp.file, resolve=resolve)
        with io.open(os.path.abspath(fp.name), "rt") as handle:
            c2 = OmegaConf.load(handle)
        assert c2 == expected
    finally:
        os.unlink(fp.name)


def save_load_from_filename(conf, resolve, expected):
    if expected is None:
        expected = conf
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            OmegaConf.save(conf, fp.name, resolve=resolve)
            c2 = OmegaConf.load(fp.name)
            assert c2 == expected
    finally:
        os.unlink(fp.name)


def test_load_from_invalid():
    with pytest.raises(TypeError):
        OmegaConf.load(3.1415)


@pytest.mark.parametrize(
    "cfg,resolve,expected",
    [
        (dict(a=10), False, None),
        ({"foo": 10, "bar": "${foo}"}, False, None),
        ({"foo": 10, "bar": "${foo}"}, False, {"foo": 10, "bar": 10}),
        ([u"שלום"], False, None),
    ],
)
class TestSaveLoad:
    def test_save_load__from_file(self, cfg, resolve, expected):
        cfg = OmegaConf.create(cfg)
        save_load_from_file(cfg, resolve, expected)

    def test_save_load__from_filename(self, cfg, resolve, expected):
        cfg = OmegaConf.create(cfg)
        save_load_from_filename(cfg, resolve, expected)


def test_save_illegal_type():
    with pytest.raises(TypeError):
        OmegaConf.save(OmegaConf.create(), 1000)


def test_pickle_dict():
    with tempfile.TemporaryFile() as fp:
        import pickle

        c = OmegaConf.create(dict(a="b"))
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1


def test_pickle_list():
    with tempfile.TemporaryFile() as fp:
        import pickle

        c = OmegaConf.create([1, 2, 3])
        pickle.dump(c, fp)
        fp.flush()
        fp.seek(0)
        c1 = pickle.load(fp)
        assert c == c1
