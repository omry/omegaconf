"""Testing for OmegaConf"""
import os
import sys
import tempfile

from omegaconf import OmegaConf


def test_create_value():
    """Test a simple value"""
    s = 'hello'
    c = OmegaConf.create(s)
    assert {'hello': None} == c


def test_create_key_value():
    """Test a simple key:value"""
    s = 'hello: world'
    c = OmegaConf.create(s)
    assert {'hello': 'world'} == c


def test_create_key_map():
    """Test a key to map"""
    s = '{hello: {a : 2}}'
    c = OmegaConf.create(s)
    assert {'hello': {'a': 2}} == c


def test_create_empty_string():
    """Test empty input"""
    s = ''
    c = OmegaConf.create(s)
    assert c == {}


def test_create_tupple_value():
    c = OmegaConf.create((1, 2))
    assert (1, 2) == c


def test_load_file():
    with tempfile.NamedTemporaryFile() as fp:
        s = b'a: b'
        fp.write(s)
        fp.flush()
        fp.seek(0)
        c = OmegaConf.load(fp.file)
        assert {'a': 'b'} == c


def test_load_filename():
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            s = b'a: b'
            fp.write(s)
            fp.flush()
            c = OmegaConf.load(fp.name)
            assert {'a': 'b'} == c
    finally:
        os.unlink(fp.name)


def test_create_from_dict1():
    d = {'a': 2, 'b': 10}
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_dict2():
    d = dict(a=2, b=10)
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_nested_dict():
    d = {'a': 2, 'b': {'c': {'f': 1}, 'd': {}}}
    c = OmegaConf.create(d)
    assert d == c


def test_create_from_cli():
    sys.argv = ['program.py', 'a=1', 'b.c=2']
    c = OmegaConf.from_cli()
    assert {'a': 1, 'b': {'c': 2}} == c
