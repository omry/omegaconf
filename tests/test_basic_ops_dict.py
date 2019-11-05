import re
import tempfile

import pytest

from omegaconf import OmegaConf, MissingMandatoryValue, DictConfig, UntypedNode, Config
from . import IllegalType


def test_setattr_deep_value():
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    c.a.b = 9
    assert {"a": {"b": 9}} == c


def test_setattr_deep_from_empty():
    c = OmegaConf.create()
    # Unfortunately we can't just do c.a.b = 9 here.
    # The reason is that if c.a is being resolved first and it does not exist, so there
    # is nothing to call .b = 9 on.
    # The alternative is to auto-create fields as they are being accessed, but this is opening
    # a whole new can of worms, and is also breaking map semantics.
    c.a = {}
    c.a.b = 9
    assert {"a": {"b": 9}} == c


def test_setattr_deep_map():
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    c.a.b = {"z": 10}
    assert {"a": {"b": {"z": 10}}} == c


def test_getattr():
    c = OmegaConf.create("a: b")
    assert "b" == c.a


def test_getattr_dict():
    c = OmegaConf.create("a: {b: 1}")
    assert {"b": 1} == c.a


def test_mandatory_value():
    c = OmegaConf.create(dict(a="???"))
    with pytest.raises(MissingMandatoryValue, match="a"):
        c.a


def test_nested_dict_mandatory_value():
    c = OmegaConf.create(dict(a=dict(b="???")))
    with pytest.raises(MissingMandatoryValue):
        c.a.b


def test_mandatory_with_default():
    c = OmegaConf.create(dict(name="???"))
    assert c.get("name", "default value") == "default value"


def test_subscript_get():
    c = OmegaConf.create("a: b")
    assert "b" == c["a"]


def test_subscript_set():
    c = OmegaConf.create()
    c["a"] = "b"
    assert {"a": "b"} == c


def test_pretty_dict():
    c = OmegaConf.create(dict(hello="world", list=[1, 2]))
    expected = """hello: world
list:
- 1
- 2
"""
    assert expected == c.pretty()
    assert OmegaConf.create(c.pretty()) == c


def test_default_value():
    c = OmegaConf.create()
    assert c.missing_key or "a default value" == "a default value"


def test_get_default_value():
    c = OmegaConf.create()
    assert c.get("missing_key", "a default value") == "a default value"


def test_scientific_notation_float():
    c = OmegaConf.create("a: 10e-3")
    assert 10e-3 == c.a


def test_dict_get_with_default():
    s = "{hello: {a : 2}}"
    c = OmegaConf.create(s)
    assert c.get("missing", 4) == 4
    assert c.hello.get("missing", 5) == 5


def test_map_expansion():
    c = OmegaConf.create("{a: 2, b: 10}")

    def foo(a, b):
        return a + b

    assert 12 == foo(**c)


def test_items():
    c = OmegaConf.create(dict(a=2, b=10))
    assert sorted([("a", 2), ("b", 10)]) == sorted(list(c.items()))


def test_items2():
    c = OmegaConf.create(dict(a=dict(v=1), b=dict(v=1)))
    for k, v in c.items():
        v.v = 2

    assert c.a.v == 2
    assert c.b.v == 2


def test_items_with_interpolation():
    c = OmegaConf.create(dict(a=2, b="${a}"))
    r = {}
    for k, v in c.items():
        r[k] = v
    assert r["a"] == 2
    assert r["b"] == 2


def test_dict_keys():
    c = OmegaConf.create("{a: 2, b: 10}")
    assert {"a": 2, "b": 10}.keys() == c.keys()


def test_pickle_get_root():
    # Test that get_root() is reconstructed correctly for pickle loaded files.
    with tempfile.TemporaryFile() as fp:
        c1 = OmegaConf.create(dict(a=dict(a1=1, a2=2,),))

        c2 = OmegaConf.create(dict(b=dict(b1="???", b2=4, bb=dict(bb1=3, bb2=4,),),))
        c3 = OmegaConf.merge(c1, c2)

        import pickle

        pickle.dump(c3, fp)
        fp.flush()
        fp.seek(0)
        loaded_c3 = pickle.load(fp)

        def test(conf):
            assert conf._get_root() == conf
            assert conf.a._get_root() == conf
            assert conf.b._get_root() == conf
            assert conf.b.bb._get_root() == conf

        assert c3 == loaded_c3
        test(c3)
        test(loaded_c3)


def test_iterate_dictionary():
    c = OmegaConf.create(dict(a=1, b=2))
    m2 = {}
    for key in c:
        m2[key] = c[key]
    assert m2 == c


def test_dict_pop():
    c = OmegaConf.create(dict(a=1, b=2))
    assert c.pop("a") == 1
    assert c.pop("not_found", "default") == "default"
    assert c == {"b": 2}
    with pytest.raises(KeyError):
        c.pop("not_found")


@pytest.mark.parametrize(
    "conf,key,expected",
    [
        ({"a": 1, "b": {}}, "a", True),
        ({"a": 1, "b": {}}, "b", True),
        ({"a": 1, "b": {}}, "c", False),
        ({"a": 1, "b": "${a}"}, "b", True),
        ({"a": 1, "b": "???"}, "b", False),
        ({"a": 1, "b": "???", "c": "${b}"}, "c", False),
        ({"a": 1, "b": "${not_found}"}, "b", False),
    ],
)
def test_in_dict(conf, key, expected):
    conf = OmegaConf.create(conf)
    ret = key in conf
    assert ret == expected


def test_get_root():
    c = OmegaConf.create(dict(a=123, b=dict(bb=456, cc=7,),))
    assert c._get_root() == c
    assert c.b._get_root() == c


def test_get_root_of_merged():
    c1 = OmegaConf.create(dict(a=dict(a1=1, a2=2,),))

    c2 = OmegaConf.create(dict(b=dict(b1="???", b2=4, bb=dict(bb1=3, bb2=4,),),))
    c3 = OmegaConf.merge(c1, c2)

    assert c3._get_root() == c3
    assert c3.a._get_root() == c3
    assert c3.b._get_root() == c3
    assert c3.b.bb._get_root() == c3


def test_dict_config():
    c = OmegaConf.create(dict())
    assert isinstance(c, DictConfig)


def test_dict_delitem():
    c = OmegaConf.create(dict(a=10, b=11))
    assert c == dict(a=10, b=11)
    del c["a"]
    assert c == dict(b=11)
    with pytest.raises(KeyError):
        del c["not_found"]


def test_dict_len():
    c = OmegaConf.create(dict(a=10, b=11))
    assert len(c) == 2


def test_dict_assign_illegal_value():
    with pytest.raises(ValueError, match=re.escape("key a")):
        c = OmegaConf.create(dict())
        c.a = IllegalType()


def test_dict_assign_illegal_value_nested():
    with pytest.raises(ValueError, match=re.escape("key a.b")):
        c = OmegaConf.create(dict(a=dict()))
        c.a.b = IllegalType()


def test_assign_dict_in_dict():
    c = OmegaConf.create(dict())
    c.foo = dict(foo="bar")
    assert c.foo == dict(foo="bar")
    assert isinstance(c.foo, DictConfig)


def test_to_container():
    src = dict(a=1, b=2, c=dict(aa=10))
    c = OmegaConf.create(src)
    result = c.to_container()
    assert type(result) == type(src)
    assert result == src


def test_pretty_without_resolve():
    c = OmegaConf.create(dict(a1="${ref}", ref="bar",))
    # without resolve, references are preserved
    c2 = OmegaConf.create(c.pretty(resolve=False))
    assert c2.a1 == "bar"
    c2.ref = "changed"
    assert c2.a1 == "changed"


def test_pretty_with_resolve():
    c = OmegaConf.create(dict(a1="${ref}", ref="bar",))
    c2 = OmegaConf.create(c.pretty(resolve=True))
    assert c2.a1 == "bar"
    c2.ref = "changed"
    assert c2.a1 == "bar"


def test_instantiate_config_fails():
    with pytest.raises(NotImplementedError):
        Config()


def test_dir():
    c = OmegaConf.create(dict(a=1, b=2, c=3))
    assert ["a", "b", "c"] == dir(c)


@pytest.mark.parametrize(
    "input1, input2",
    [
        # empty
        (dict(), dict()),
        # simple
        (dict(a=12), dict(a=12)),
        # any vs raw
        (dict(a=12), dict(a=UntypedNode(12))),
        # nested dict empty
        (dict(a=12, b=dict()), dict(a=12, b=dict())),
        # nested dict
        (dict(a=12, b=dict(c=10)), dict(a=12, b=dict(c=10))),
        # nested list
        (dict(a=12, b=[1, 2, 3]), dict(a=12, b=[1, 2, 3])),
        # nested list with any
        (dict(a=12, b=[1, 2, UntypedNode(3)]), dict(a=12, b=[1, 2, UntypedNode(3)]),),
        # In python 3.6 insert order changes iteration order. this ensures that equality is preserved.
        (dict(a=1, b=2, c=3, d=4, e=5), dict(e=5, b=2, c=3, d=4, a=1)),
    ],
)
def test_dict_eq(input1, input2):
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def eq(a, b):
        assert a == b
        assert b == a
        assert not a != b
        assert not b != a

    eq(c1, c2)
    eq(c1, input1)
    eq(c2, input2)


@pytest.mark.parametrize("input1, input2", [(dict(a=12, b="${a}"), dict(a=12, b=12))])
def test_dict_eq_with_interpolation(input1, input2):
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def eq(a, b):
        assert a == b
        assert b == a
        assert not a != b
        assert not b != a

    eq(c1, c2)


@pytest.mark.parametrize(
    "input1, input2",
    [
        (dict(), dict(a=10)),
        ({}, []),
        (dict(a=12), dict(a=13)),
        (dict(a=0), dict(b=0)),
        (dict(a=12), dict(a=UntypedNode(13))),
        (dict(a=12, b=dict()), dict(a=13, b=dict())),
        (dict(a=12, b=dict(c=10)), dict(a=13, b=dict(c=10))),
        (dict(a=12, b=[1, 2, 3]), dict(a=12, b=[10, 2, 3])),
        (dict(a=12, b=[1, 2, UntypedNode(3)]), dict(a=12, b=[1, 2, UntypedNode(30)]),),
    ],
)
def test_dict_not_eq(input1, input2):
    c1 = OmegaConf.create(input1)
    c2 = OmegaConf.create(input2)

    def neq(a, b):
        assert a != b
        assert b != a
        assert not a == b
        assert not b == a

    neq(c1, c2)


def test_config_eq_mismatch_types():
    c1 = OmegaConf.create({})
    c2 = OmegaConf.create([])
    assert not Config._config_eq(c1, c2)


def test_dict_not_eq_with_another_class():
    assert OmegaConf.create() != "string"


def test_hash():
    c1 = OmegaConf.create(dict(a=10))
    c2 = OmegaConf.create(dict(a=10))
    assert hash(c1) == hash(c2)
    c2.a = 20
    assert hash(c1) != hash(c2)


def test_get_with_default_from_struct_not_throwing():
    c = OmegaConf.create(dict(a=10, b=20))
    OmegaConf.set_struct(c, True)
    assert c.get("z", "default") == "default"
