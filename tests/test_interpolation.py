import os
import random

from pytest import raises
import six

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

    with raises(KeyError):
        c.a


def test_str_interpolation_key_error_2():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(
        a='${not.found}',
    ))

    with raises(KeyError):
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


def test_interpolation_fails_on_config():
    # Test that a ValueError is thrown if an string interpolation used on config value
    c = OmegaConf.create(dict(
        config_obj=dict(
            value1=42,
            value2=43,
        ),
        deep=dict(
            inside='${config_obj}',
        ),
    ))

    with raises(ValueError):
        c.deep.inside


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
    with raises(KeyError):
        c.path


def catch_recursion(f):
    if six.PY2:
        with raises(RuntimeError):
            f()
    else:
        with raises(RecursionError):
            f()


def test_register_resolver_twice_error():
    try:
        OmegaConf.register_resolver("foo", lambda: 10)
        with raises(AssertionError):
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


def test_register_resolver_2():
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

    with raises(KeyError):
        c[0]


def test_interpolation_into_list():
    # Test that a KeyError is thrown if an str_interpolation key is not available
    c = OmegaConf.create(dict(
        list=['bar'],
        foo='${list.0}'
    ))

    assert c.foo == 'bar'


def test_unsuppoerted_interpolation_type():
    c = OmegaConf.create(dict(
        foo='${wrong_type:ref}',
    ))

    with raises(ValueError):
        c.foo


def test_resolve_none():
    c = OmegaConf.create(dict(
        foo=None
    ))

    assert c.foo is None
