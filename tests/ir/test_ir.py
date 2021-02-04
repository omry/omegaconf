import copy
from importlib import import_module
from typing import Any

from pytest import fixture

from omegaconf import MISSING
from omegaconf.ir import IRNode, get_dataclass_ir


def resolve_types(module: Any, ir: IRNode) -> None:
    if isinstance(ir.type, str):
        ir.type = getattr(module, ir.type)

    if isinstance(ir.val, list):
        for c in ir.val:
            resolve_types(module, c)


@fixture(
    params=["tests.ir.data.dataclass", "tests.ir.data.attr"],
    ids=lambda x: x.split(".")[-1],
)
def module(request: Any) -> Any:
    return import_module(request.param)


@fixture(
    params=[
        (
            "User",
            IRNode(
                name=None,
                type="User",
                opt=False,
                val=[
                    IRNode(name="name", type=str, opt=False, val=MISSING),
                    IRNode(name="age", type=int, opt=False, val=MISSING),
                ],
            ),
        ),
        (
            "UserWithMissing",
            IRNode(
                name=None,
                type="UserWithMissing",
                opt=False,
                val=[
                    IRNode(name="name", type=str, opt=False, val=MISSING),
                    IRNode(name="age", type=int, opt=False, val=MISSING),
                ],
            ),
        ),
    ],
    ids=lambda x: x[0],
)
def tested_type(module: Any, request: Any) -> Any:
    name = request.param[0]
    expected = copy.deepcopy(request.param[1])
    resolve_types(module, expected)
    return {"type": getattr(module, name), "expected": expected}


def test_get_dataclass_ir(tested_type: Any):
    assert get_dataclass_ir(tested_type["type"]) == tested_type["expected"]
