import copy
import re
from typing import Any

import pytest

from omegaconf import (
    BooleanNode,
    DictConfig,
    EnumNode,
    FloatNode,
    IntegerNode,
    ListConfig,
    OmegaConf,
    StringNode,
    ValidationError,
    ValueNode,
)

from . import Color, Group

SKIP = object()


def verify(
    cfg: Any,
    key: Any,
    none: bool,
    opt: bool,
    missing: bool,
    inter: bool,
    exp: Any = SKIP,
) -> None:
    target_node = cfg._get_node(key)
    assert target_node._key() == key
    assert target_node._is_none() == none
    assert target_node._is_optional() == opt
    assert target_node._is_missing() == missing
    assert target_node._is_interpolation() == inter

    if exp is not SKIP:
        assert cfg.get(key) == exp

    assert OmegaConf.is_missing(cfg, key) == missing
    assert OmegaConf.is_none(cfg, key) == none
    assert OmegaConf.is_optional(cfg, key) == opt
    assert OmegaConf.is_interpolation(cfg, key) == inter


# for each type Node type : int, bool, str, float, Color (enum) and User (@dataclass), DictConfig, ListConfig
#   for each MISSING, None, Optional and interpolation:
@pytest.mark.parametrize(
    "node_type, values",
    [
        (BooleanNode, [True, False]),
        (FloatNode, [3.1415]),
        (IntegerNode, [42]),
        (StringNode, ["hello"]),
        # EnumNode
        (
            lambda value, is_optional, key=None: EnumNode(
                enum_type=Color, value=value, is_optional=is_optional, key=key
            ),
            [Color.RED],
        ),
        # DictConfig
        (
            lambda value, is_optional, key=None: DictConfig(
                is_optional=is_optional, content=value, key=key
            ),
            [{}, {"foo": "bar"}],
        ),
        # ListConfig
        (
            lambda value, is_optional, key=None: ListConfig(
                is_optional=is_optional, content=value, key=key
            ),
            [[], [1, 2, 3]],
        ),
        # dataclass
        (
            lambda value, is_optional, key=None: DictConfig(
                ref_type=Group, is_optional=is_optional, content=value, key=key
            ),
            [Group, Group()],
        ),
    ],
    ids=(
        "BooleanNode",
        "FloatNode",
        "IntegerNode",
        "StringNode",
        "EnumNode",
        "DictConfig",
        "ListConfig",
        "dataclass",
    ),
)
class TestNodeTypesMatrix:
    def test_none_assignment_and_merging_in_dict(
        self, node_type: Any, values: Any
    ) -> None:
        values = copy.deepcopy(values)
        for value in values:
            node = node_type(value=value, is_optional=False)
            data = {"node": node}
            cfg = OmegaConf.create(obj=data)
            verify(cfg, "node", none=False, opt=False, missing=False, inter=False)
            msg = "field 'node' is not Optional"
            with pytest.raises(ValidationError, match=re.escape(msg)):
                cfg.node = None

            with pytest.raises(ValidationError):
                OmegaConf.merge(cfg, {"node": None})

    def test_dict_non_none_assignment(self, node_type: Any, values: Any) -> None:
        values = copy.deepcopy(values)
        for value in values:
            value_backup = copy.deepcopy(value)
            cfg = OmegaConf.create({"node": node_type(value=None, is_optional=True)})
            verify(cfg, "node", none=True, opt=True, missing=False, inter=False)

            cfg.node = value
            assert cfg._get_node("node") == value
            verify(cfg, "node", none=False, opt=True, missing=False, inter=False)

            cfg.node = "???"
            verify(cfg, "node", none=False, opt=True, missing=True, inter=False)

            cfg.node = value_backup
            assert cfg._get_node("node") == value_backup
            verify(cfg, "node", none=False, opt=True, missing=False, inter=False)

    def test_none_assignment_in_list(self, node_type: Any, values: Any) -> None:
        values = copy.deepcopy(values)
        for value in values:
            key = 0
            d = node_type(value=value, key=key, is_optional=False)
            cfg = OmegaConf.create([d])
            verify(cfg, key, none=False, opt=False, missing=False, inter=False)

            with pytest.raises(ValidationError):
                cfg[key] = None

    def test_list_non_none_assignment(self, node_type: Any, values: Any) -> None:
        values = copy.deepcopy(values)
        for value in values:
            key = 0
            cfg = OmegaConf.create([node_type(value=None, key=key, is_optional=True)])
            verify(cfg, key, none=True, opt=True, missing=False, inter=False)

            cfg[key] = value
            assert cfg[key] == value
            verify(cfg, key, none=False, opt=True, missing=False, inter=False)

    def test_none_construction(self, node_type: Any, values: Any) -> None:
        values = copy.deepcopy(values)
        node = node_type(value=None, is_optional=True)
        if isinstance(node, ValueNode):
            assert node._value() is None
            assert node._is_optional()
        assert node.__eq__(None)
        assert OmegaConf.is_none(node)

        for value in values:
            node._set_value(value)
            assert node.__eq__(value)
            assert not node.__eq__(None)
            assert not OmegaConf.is_none(node)

        with pytest.raises(ValidationError):
            node_type(value=None, is_optional=False)

    def test_interpolation(
        self, node_type: Any, values: Any, restore_resolvers: Any
    ) -> None:
        resolver_output = 9999
        OmegaConf.register_resolver("func", lambda: resolver_output)
        values = copy.deepcopy(values)
        for value in values:
            node = {
                "reg": node_type(value=value, is_optional=False),
                "opt": node_type(value=value, is_optional=True),
            }
            cfg = OmegaConf.create(
                {
                    "const": 10,
                    "primitive_missing": "???",
                    "resolver": StringNode(value="${func:}", is_optional=False),
                    "opt_resolver": StringNode(value="${func:}", is_optional=True),
                    "node": DictConfig(content=node, is_optional=False),
                    "opt_node": DictConfig(content=node, is_optional=True),
                    "reg": node_type(value=value, is_optional=False),
                    "opt": node_type(value=value, is_optional=True),
                    "opt_none": node_type(value=None, is_optional=True),
                    "missing": node_type(value="???", is_optional=False),
                    "opt_missing": node_type(value="???", is_optional=True),
                    # Interpolations
                    "int_reg": "${reg}",
                    "int_opt": "${opt}",
                    "int_opt_none": "${opt_none}",
                    "int_missing": "${missing}",
                    "int_opt_missing": "${opt_missing}",
                    "str_int_const": StringNode(
                        value="foo_${const}", is_optional=False
                    ),
                    "opt_str_int_const": StringNode(
                        value="foo_${const}", is_optional=True
                    ),
                    "str_int_with_primitive_missing": StringNode(
                        value="foo_${primitive_missing}", is_optional=False
                    ),
                    "opt_str_int_with_primitive_missing": StringNode(
                        value="foo_${primitive_missing}", is_optional=True
                    ),
                    "int_node": "${node}",
                    "int_opt_node": "${opt_node}",
                    "int_resolver": "${resolver}",
                    "int_opt_resolver": "${opt_resolver}",
                }
            )

            verify(
                cfg, "const", none=False, opt=True, missing=False, inter=False, exp=10,
            )

            verify(
                cfg,
                "resolver",
                none=False,
                # Note, resolvers are always optional because the underlying function may return None
                opt=True,
                missing=False,
                inter=True,
                exp=resolver_output,
            )

            verify(
                cfg,
                "opt_resolver",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp=resolver_output,
            )

            verify(
                cfg,
                "reg",
                none=False,
                opt=False,
                missing=False,
                inter=False,
                exp=value,
            )

            verify(
                cfg, "opt", none=False, opt=True, missing=False, inter=False, exp=value
            )
            verify(
                cfg,
                "opt_none",
                none=True,
                opt=True,
                missing=False,
                inter=False,
                exp=None,
            )
            verify(cfg, "missing", none=False, opt=False, missing=True, inter=False)
            verify(cfg, "opt_missing", none=False, opt=True, missing=True, inter=False)

            verify(
                cfg,
                "int_reg",
                none=False,
                opt=False,
                missing=False,
                inter=True,
                exp=value,
            )
            verify(
                cfg,
                "int_opt",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp=value,
            )
            verify(
                cfg,
                "int_opt_none",
                none=True,
                opt=True,
                missing=False,
                inter=True,
                exp=None,
            )
            verify(cfg, "int_missing", none=False, opt=False, missing=True, inter=True)
            verify(
                cfg, "int_opt_missing", none=False, opt=True, missing=True, inter=True
            )

            verify(
                cfg,
                "str_int_const",
                none=False,
                opt=False,
                missing=False,
                inter=True,
                exp="foo_10",
            )
            verify(
                cfg,
                "opt_str_int_const",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp="foo_10",
            )
            verify(
                cfg,
                "int_node",
                none=False,
                opt=False,
                missing=False,
                inter=True,
                exp=node,
            )

            verify(
                cfg,
                "int_opt_node",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp=node,
            )

            verify(
                cfg,
                "int_resolver",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp=resolver_output,
            )

            verify(
                cfg,
                "int_opt_resolver",
                none=False,
                opt=True,
                missing=False,
                inter=True,
                exp=resolver_output,
            )

            verify(
                cfg,
                "str_int_with_primitive_missing",
                none=False,
                opt=False,
                missing=True,
                inter=True,
            )

            verify(
                cfg,
                "opt_str_int_with_primitive_missing",
                none=False,
                opt=True,
                missing=True,
                inter=True,
            )
