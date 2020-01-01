# -*- coding: utf-8 -*-
import io
import os
import tempfile

from omegaconf import DictConfig, OmegaConf
from pytest import raises


def save_load_file_deprecated(conf: DictConfig) -> None:
    try:
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as fp:
            conf.save(fp.file)  # type: ignore
        with io.open(os.path.abspath(fp.name), "rt") as handle:
            c2 = OmegaConf.load(handle)
        assert conf == c2
    finally:
        os.unlink(fp.name)


def save_load_filename(conf: DictConfig) -> None:
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            conf.save(fp.name)
            c2 = OmegaConf.load(fp.name)
            assert conf == c2
    finally:
        os.unlink(fp.name)


# Test deprecated config.save()
def save_load__from_file_deprecated(conf: DictConfig) -> None:
    try:
        with tempfile.NamedTemporaryFile(mode="wt", delete=False) as fp:
            conf.save(fp.file)  # type: ignore
        with io.open(os.path.abspath(fp.name), "rt") as handle:
            c2 = OmegaConf.load(handle)
        assert conf == c2
    finally:
        os.unlink(fp.name)


def save_load__from_filename_deprecated(conf: DictConfig) -> None:
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            conf.save(fp.name)
            c2 = OmegaConf.load(fp.name)
            assert conf == c2
    finally:
        os.unlink(fp.name)


def test_save_load_file_deprecated() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load_file_deprecated(cfg)


def test_save_load_filename_deprecated() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load_filename(cfg)


def test_save_load__from_file_deprecated() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load__from_file_deprecated(cfg)


def test_save_load__from_filename_deprecated() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load__from_filename_deprecated(cfg)


def test_save_illegal_type_deprecated() -> None:
    with raises(TypeError):
        OmegaConf.create().save(1000)  # type: ignore


def test_save_load_file() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load_file_deprecated(cfg)


def test_save_load_filename() -> None:
    cfg = OmegaConf.create(dict(a=10))
    assert isinstance(cfg, DictConfig)
    save_load_filename(cfg)
