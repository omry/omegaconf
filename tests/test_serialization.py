import os
import tempfile
import io
from omegaconf import OmegaConf


def test_save_load_file():
    with tempfile.NamedTemporaryFile(mode="wt") as fp:
        c = OmegaConf.create(dict(a=10))
        c.save(fp.file)
        fp.seek(0)
        with io.open(os.path.abspath(fp.name), 'rt') as handle:
            c2 = OmegaConf.load(handle)
        assert c == c2


def test_save_load_filename():
    # note that delete=False here is a work around windows incompetence.
    try:
        with tempfile.NamedTemporaryFile(delete=False) as fp:
            c = OmegaConf.create(dict(a=10))
            c.save(fp.name)
            c2 = OmegaConf.load(fp.name)
            assert c == c2
    finally:
        os.unlink(fp.name)


def test_pickle_dict():
    with tempfile.TemporaryFile() as fp:
        import pickle
        c = OmegaConf.create(dict(a='b'))
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

# TODO: test save and load of actual unicode characters in strings.
