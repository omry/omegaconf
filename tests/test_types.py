from omegaconf import OmegaConf, types, ValidationError
import pytest


def test_integer_1():
    c = OmegaConf.create()
    c.foo = types.Integer(10)
    assert c.foo == 10

    with pytest.raises(ValidationError):
        c.foo = "string"


def test_integer_rejects_string():
    c = OmegaConf.create()
    c.foo = types.Integer(10)
    assert c.foo == 10
    with pytest.raises(ValidationError):
        c.foo = "string"
    assert c.foo == 10

# TODO:
"""
Complete all types.
test all sorts of madness with types, assignment, choices etc
"""
