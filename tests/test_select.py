from omegaconf import OmegaConf


def test_select_key_from_empty():
    c = OmegaConf.create()
    assert c.select("not_there") is None


def test_select_dotkey_from_empty():
    c = OmegaConf.create()
    assert c.select("not.there") is None
    assert c.select("still.not.there") is None


def test_select_from_dict():
    c = OmegaConf.create(dict(
        a=dict(
            v=1
        ),
        b=dict(
            v=1
        ),
    ))

    assert c.select('a') == {'v': 1}
    assert c.select('a.v') == 1
    assert c.select('b.v') == 1
    assert c.select('nope') is None


def test_select_from_empty_list():
    c = OmegaConf.create([])
    assert c.select("0") is None


def test_select_from_primitive_list():
    c = OmegaConf.create([1, 2, 3, "4"])
    assert c.select("0") == 1
    assert c.select("1") == 2
    assert c.select("2") == 3
    assert c.select("3") == "4"


def test_select_from_dict_in_list():
    c = OmegaConf.create([1, dict(a=10, c=['foo', 'bar'])])
    assert c.select("0") == 1
    assert c.select("1.a") == 10
    assert c.select("1.b") is None
    assert c.select("1.c.0") == 'foo'
    assert c.select("1.c.1") == 'bar'
