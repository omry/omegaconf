from omegaconf import OmegaConf


# 1
def test_get_full_key__dict():
    c = OmegaConf.create(dict(a=1))
    assert c.get_full_key("a") == "a"


def test_get_full_key__list():
    c = OmegaConf.create([1, 2, 3])
    assert c.get_full_key("2") == "[2]"


# 2
def test_get_full_key__dd():
    c = OmegaConf.create(dict(a=1, b=dict(c=1)))
    assert c.b.get_full_key("c") == "b.c"


def test_get_full_key__dl():
    c = OmegaConf.create(dict(a=[1, 2, 3]))
    assert c.a.get_full_key(1) == "a[1]"


def test_get_full_key__ll():
    c = OmegaConf.create([[1, 2, 3]])
    assert c[0].get_full_key("2") == "[0][2]"


def test_get_full_key__ld():
    c = OmegaConf.create([1, 2, dict(a=1)])
    assert c[2].get_full_key("a") == "[2].a"


# 3
def test_get_full_key__ddd():
    c = OmegaConf.create(dict(a=dict(b=dict(c=1))))
    assert c.a.b.get_full_key("c") == "a.b.c"


def test_get_full_key__ddl():
    c = OmegaConf.create(dict(a=dict(b=[0, 1])))
    assert c.a.b.get_full_key(0) == "a.b[0]"


def test_get_full_key__dll():
    c = OmegaConf.create(dict(a=[1, [2]]))
    assert c.a[1].get_full_key(0) == "a[1][0]"


def test_get_full_key__dld():
    c = OmegaConf.create(dict(a=[dict(b=2)]))
    assert c.a[0].get_full_key("b") == "a[0].b"


def test_get_full_key__ldd():
    c = OmegaConf.create([dict(a=dict(b=1))])
    assert c[0].a.get_full_key("b") == "[0].a.b"


def test_get_full_key__ldl():
    c = OmegaConf.create([dict(a=[0])])
    assert c[0].a.get_full_key(0) == "[0].a[0]"


def test_get_full_key__lll():
    c = OmegaConf.create([[[0]]])
    assert c[0][0].get_full_key(0) == "[0][0][0]"


def test_get_full_key__lld():
    c = OmegaConf.create([[dict(a=1)]])
    assert c[0][0].get_full_key("a") == "[0][0].a"


def test_get_full_key__lldddl():
    c = OmegaConf.create([[dict(a=dict(a=[0]))]])
    assert c[0][0].a.a.get_full_key(0) == "[0][0].a.a[0]"
