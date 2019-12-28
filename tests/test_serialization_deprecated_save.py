# -*- coding: utf-8 -*-
import io
import os
import tempfile

from pytest import raises

from omegaconf import OmegaConf


def save_load_file_deprecated(conf):
    try:
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as fp:
            conf.save(fp.file)
        with io.open(os.path.abspath(fp.name), "rt") as handle:
            c2 = OmegaConf.load(handle)
        assert conf == c2
    finally:
        os.unlink(fp.name)


def save_load_filename(conf):
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            conf.save(fp.name)
            c2 = OmegaConf.load(fp.name)
            assert conf == c2
    finally:
        os.unlink(fp.name)


# Test deprecated config.save()


def save_load__from_file_deprecated(conf):
    try:
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as fp:
            conf.save(fp.file)
        with io.open(os.path.abspath(fp.name), "rt") as handle:
            c2 = OmegaConf.load(handle)
        assert conf == c2
    finally:
        os.unlink(fp.name)


def save_load__from_filename_deprecated(conf):
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            conf.save(fp.name)
            c2 = OmegaConf.load(fp.name)
            assert conf == c2
    finally:
        os.unlink(fp.name)


def test_save_load_file_deprecated():
    save_load_file_deprecated(OmegaConf.create(dict(a=10)))


def test_save_load_filename_deprecated():
    save_load_filename(OmegaConf.create(dict(a=10)))


def test_save_load__from_file_deprecated():
    save_load__from_file_deprecated(OmegaConf.create(dict(a=10)))


def test_save_load__from_filename_deprecated():
    save_load__from_filename_deprecated(OmegaConf.create(dict(a=10)))


def test_save_illegal_type_deprecated():
    with raises(TypeError):
        OmegaConf.create().save(1000)


def test_save_load_file():
    save_load_file_deprecated(OmegaConf.create(dict(a=10)))


def test_save_load_filename():
    save_load_filename(OmegaConf.create(dict(a=10)))
