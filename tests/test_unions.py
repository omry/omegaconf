from pathlib import Path
from typing import Any, Union

from pytest import mark, param, raises

from omegaconf import OmegaConf, UnionNode, ValidationError
from omegaconf._utils import _get_value
from tests import Color


@mark.parametrize(
    "union_args",
    [
        param((int, float), id="int_float"),
        param((float, bool), id="float_bool"),
        param((bool, str), id="bool_str"),
        param((str, bytes), id="str_bytes"),
        param((bytes, Color), id="bytes_color"),
        param((Color, int), id="color_int"),
    ],
)
@mark.parametrize(
    "input_",
    [
        param(123, id="123"),
        param(10.1, id="10.1"),
        param(b"binary", id="binary"),
        param(True, id="true"),
        param("abc", id="abc"),
        param("RED", id="red_str"),
        param("123", id="123_str"),
        param("10.1", id="10.1_str"),
        param(Color.RED, id="Color.RED"),
        param(Path("hello.txt"), id="path"),
        param(object(), id="object"),
    ],
)
class TestUnionNode:
    def test_creation(self, input_: Any, union_args: Any) -> None:
        ref_type = Union[union_args]
        legal = type(input_) in union_args
        if legal:
            node = UnionNode(input_, ref_type)
            assert _get_value(node) == input_
        else:
            with raises(ValidationError):
                UnionNode(input_, ref_type)

    def test_set_value(self, input_: Any, union_args: Any) -> None:
        ref_type = Union[union_args]
        legal = type(input_) in union_args
        node = UnionNode(None, ref_type)
        if legal:
            node._set_value(input_)
            assert _get_value(node) == input_
        else:
            with raises(ValidationError):
                node._set_value(input_)


@mark.parametrize(
    "optional", [param(True, id="optional"), param(False, id="not_optional")]
)
@mark.parametrize(
    "input_",
    [
        param("???", id="missing"),
        param("${interp}", id="interp"),
        param(None, id="none"),
    ],
)
class TestUnionNodeSpecial:
    def test_creation_special(self, input_: Any, optional: bool) -> None:
        if input_ is None and not optional:
            with raises(ValidationError):
                UnionNode(input_, Union[int, str], is_optional=optional)
        else:
            node = UnionNode(input_, Union[int, str], is_optional=optional)
            assert node._value() == input_

    def test_set_value_special(self, input_: Any, optional: bool) -> None:
        node = UnionNode(123, Union[int, str], is_optional=optional)
        if input_ is None and not optional:
            with raises(ValidationError):
                node._set_value(input_)
        else:
            node._set_value(input_)
            assert node._value() == input_


def test_get_parent_container() -> None:
    cfg = OmegaConf.create({"foo": UnionNode(123, Union[int, str]), "bar": "baz"})

    unode = cfg._get_node("foo")
    nested_node = unode._value()  # type: ignore
    assert unode._get_parent_container() is cfg  # type: ignore
    assert nested_node._get_parent_container() is cfg
    assert cfg._get_node("bar")._get_parent_container() is cfg  # type: ignore


def test_union_node_get_root_standalone() -> None:
    from tests import User

    # Destination config. We set 'no_deepcopy_set_nodes' flag to True, as this is
    # the internal flag used by OmegaConf.unsafe_merge to speed up operations.
    dest = OmegaConf.create({"val": UnionNode(123, Union[User, int])})
    dest._set_flag("no_deepcopy_set_nodes", True)

    # Source: a standalone UnionNode containing a structured DictConfig
    user = OmegaConf.structured(User)
    src_union = UnionNode(content=user, ref_type=Union[User, int])

    # Assignment triggers the _get_root() check in BaseContainer._set_item_impl
    # This used to raise AssertionError because UnionNode is not a Container.
    dest.val = src_union
    assert dest.val == user
