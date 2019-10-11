import os
import random

import pytest

from omegaconf import OmegaConf


def test_str_interpolation_dict_1():
    # Simplest str_interpolation
    c = OmegaConf.create(dict(
        a='${referenced}',
        referenced='bar',
    ))
    assert c.referenced == 'bar'
    assert c.a == 'bar'


def test_str_interpolation_key_error_1():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(
        a='${not_found}',
    ))

    with pytest.raises(KeyError):
        _ = c.a


def test_str_interpolation_key_error_2():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(
        a='${not.found}',
    ))

    with pytest.raises(KeyError):
        c.a


def test_str_interpolation_3():
    # Test that str_interpolation works with complex strings
    c = OmegaConf.create(dict(
        a='the year ${year}',
        year='of the cat',
    ))

    assert c.a == 'the year of the cat'


def test_str_interpolation_4():
    # Test that a string with multiple str_interpolations works
    c = OmegaConf.create(dict(
        a='${ha} ${ha} ${ha}, said Pennywise, ${ha} ${ha}... ${ha}!',
        ha='HA',
    ))

    assert c.a == 'HA HA HA, said Pennywise, HA HA... HA!'


def test_deep_str_interpolation_1():
    # Test deep str_interpolation works
    c = OmegaConf.create(dict(
        a='the answer to the universe and everything is ${nested.value}',
        nested=dict(
            value=42
        ),
    ))

    assert c.a == 'the answer to the universe and everything is 42'


def test_deep_str_interpolation_2():
    # Test that str_interpolation of a key that is nested works
    c = OmegaConf.create(dict(
        out=42,
        deep=dict(
            inside='the answer to the universe and everything is ${out}',
        ),
    ))

    assert c.deep.inside == 'the answer to the universe and everything is 42'


def test_simple_str_interpolation_inherit_type():
    # Test that str_interpolation of a key that is nested works
    c = OmegaConf.create(dict(
        inter1='${answer1}',
        inter2='${answer2}',
        inter3='${answer3}',
        inter4='${answer4}',
        answer1=42,
        answer2=42.0,
        answer3=False,
        answer4='string',
    ))

    assert type(c.inter1) == int
    assert type(c.inter2) == float
    assert type(c.inter3) == bool
    assert type(c.inter4) == str


def test_complex_str_interpolation_is_always_str_1():
    c = OmegaConf.create(dict(
        two=2,
        four=4,
        inter1='${four}${two}',
        inter2='4${two}',
    ))

    assert type(c.inter1) == str
    assert c.inter1 == '42'
    assert type(c.inter2) == str
    assert c.inter2 == '42'


@pytest.mark.parametrize('input_,key,expected', [
    (dict(a=10, b='${a}'), 'b', 10),
    (dict(a=10, b=[1, '${a}', 3, 4]), 'b.1', 10),
    (dict(a='${b.1}', b=[1, dict(c=10), 3, 4]), 'a', dict(c=10)),
    (dict(a='${b}', b=[1, 2]), 'a', [1, 2]),
    (dict(a='foo-${b}', b=[1, 2]), 'a', 'foo-[1, 2]'),
    (dict(a='foo-${b}', b=dict(c=10)), 'a', "foo-{'c': 10}"),
])
def test_interpolation(input_, key, expected):
    c = OmegaConf.create(input_)
    assert c.select(key) == expected


def test_2_step_interpolation():
    c = OmegaConf.create(dict(
        src='bar',
        copy_src='${src}',
        copy_copy='${copy_src}',
    ))
    assert c.copy_src == 'bar'
    assert c.copy_copy == 'bar'


def test_env_interpolation1():
    try:
        os.environ['foobar'] = '1234'
        c = OmegaConf.create(dict(
            path='/test/${env:foobar}',
        ))
        assert c.path == '/test/1234'
    finally:
        del os.environ['foobar']
        OmegaConf.clear_resolvers()


def test_env_interpolation_not_found():
    c = OmegaConf.create(dict(
        path='/test/${env:foobar}',
    ))
    with pytest.raises(KeyError):
        c.path


@pytest.mark.parametrize("value,expected", [
   ("false", False),
   ("off", False),
   ("no", False),
   ("true", True),
   ("on", True),
   ("yes", True),
   ("10", 10),
   ("-10", -10),
   ("10.0", 10.0),
   ("-10.0", -10.0),
   ("foo: bar", {'foo': 'bar'}),
   ("foo: \n - bar\n - baz", {'foo': ['bar', 'baz']}),
])
def test_values_from_env_come_parsed(value, expected):
    try:
        os.environ["my_key"] = value
        c = OmegaConf.create(
            dict(
                my_key="${env:my_key}",
            )
        )
        assert c.my_key == expected
    finally:
        del os.environ["my_key"]
        OmegaConf.clear_resolvers()


def test_register_resolver_twice_error():
    try:
        OmegaConf.register_resolver("foo", lambda: 10)
        with pytest.raises(AssertionError):
            OmegaConf.register_resolver("foo", lambda: 10)
    finally:
        OmegaConf.clear_resolvers()


def test_clear_resolvers():
    assert OmegaConf.get_resolver('foo') is None
    try:
        OmegaConf.register_resolver('foo', lambda x: int(x) + 10)
        assert OmegaConf.get_resolver('foo') is not None
    finally:
        OmegaConf.clear_resolvers()
        assert OmegaConf.get_resolver('foo') is None


def test_register_resolver_1():
    try:
        OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
        c = OmegaConf.create(dict(
            k='${plus_10:990}',
        ))

        assert type(c.k) == int
        assert c.k == 1000
    finally:
        OmegaConf.clear_resolvers()


def test_resolver_cache_1():
    # resolvers are always converted to stateless idempotent functions
    # subsequent calls to the same function with the same argument will always return the same value.
    # this is important to allow embedding of functions like time() without having the value change during
    # the program execution.
    try:
        OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
        c = OmegaConf.create(dict(
            k='${random:_}',
        ))
        assert c.k == c.k
    finally:
        OmegaConf.clear_resolvers()


def test_resolver_cache_2():
    """
    Tests that resolver cache is not shared between different OmegaConf objects 
    """
    try:
        OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
        c1 = OmegaConf.create(dict(
            k='${random:_}',
        ))
        c2 = OmegaConf.create(dict(
            k='${random:_}',
        ))
        assert c1.k != c2.k
        assert c1.k == c1.k
        assert c2.k == c2.k
    finally:
        OmegaConf.clear_resolvers()


def test_copy_cache():
    OmegaConf.register_resolver("random", lambda _: random.randint(0, 10000000))
    c1 = OmegaConf.create(dict(
        k='${random:_}',
    ))
    assert c1.k == c1.k

    c2 = OmegaConf.create(dict(
        k='${random:_}',
    ))
    assert c2.k != c1.k
    OmegaConf.set_cache(c2, OmegaConf.get_cache(c1))
    assert c2.k == c1.k

    c3 = OmegaConf.create(dict(
        k='${random:_}',
    ))

    assert c3.k != c1.k
    OmegaConf.copy_cache(c1, c3)
    assert c3.k == c1.k


def test_date_pattern():
    supported_chars = '%_-abc123.'
    c = OmegaConf.create(dict(
        dir1='${copy:' + supported_chars + '}',
    ))

    OmegaConf.register_resolver("copy", lambda x: x)
    assert c.dir1 == supported_chars


def test_str_interpolation_list_1():
    # interpolating a value in a list
    c = OmegaConf.create(dict(
        foo=['${ref}'],
        ref='bar'
    ))
    assert c.foo[0] == 'bar'


def test_interpolation_in_list_key_error():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(['${10}'])

    with pytest.raises(KeyError):
        c[0]


def test_interpolation_into_list():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(
        list=['bar'],
        foo='${list.0}'
    ))

    assert c.foo == 'bar'


def test_unsupported_interpolation_type():
    c = OmegaConf.create(dict(
        foo='${wrong_type:ref}',
    ))

    with pytest.raises(ValueError):
        c.foo


def test_resolve_none():
    c = OmegaConf.create(dict(
        foo=None
    ))

    assert c.foo is None


def test_incremental_dict_with_interpolation():
    conf = OmegaConf.create()
    conf.a = 1
    conf.b = OmegaConf.create()
    conf.b.c = "${a}"
    assert conf.b.c == conf.a
