import dataclasses  # lgtm [py/import-and-import-from]
from dataclasses import dataclass
from typing import Any, Optional, get_type_hints

from omegaconf._utils import (
    _resolve_forward,
    _resolve_optional,
    get_type_of,
    is_attr_class,
    is_dataclass,
)


@dataclass
class IR:
    pass


@dataclass
class IRNode(IR):
    name: Optional[str]
    type: Any
    val: Any
    opt: bool


def get_dataclass_ir(obj: Any) -> IRNode:
    from omegaconf.omegaconf import MISSING

    resolved_hints = get_type_hints(get_type_of(obj))
    assert is_dataclass(obj)
    obj_type = get_type_of(obj)
    children = []
    for fld in dataclasses.fields(obj):
        name = fld.name
        opt, type_ = _resolve_optional(resolved_hints[name])
        type_ = _resolve_forward(type_, fld.__module__)

        if hasattr(obj, name):
            value = getattr(obj, name)
            if value == dataclasses.MISSING:
                value = MISSING
        else:
            if fld.default_factory == dataclasses.MISSING:  # type: ignore
                value = MISSING
            else:
                value = fld.default_factory()  # type: ignore
        ir = IRNode(name=name, type=type_, opt=opt, val=value)
        children.append(ir)

    return IRNode(name=None, val=children, type=obj_type, opt=False)


def get_attr_ir(obj: Any) -> IRNode:
    import attr
    import attr._make

    from omegaconf.omegaconf import MISSING

    resolved_hints = get_type_hints(get_type_of(obj))
    assert is_attr_class(obj)
    obj_type = get_type_of(obj)
    children = []
    for name, attrib in attr.fields_dict(obj).items():
        # for fld in dataclasses.fields(obj):
        # name = fld.name
        opt, type_ = _resolve_optional(resolved_hints[name])
        type_ = _resolve_forward(type_, obj_type.__module__)

        assert not hasattr(obj, name)  # no test coverage for this case yet
        if attrib.default == attr.NOTHING:
            value = MISSING
        elif isinstance(attrib.default, attr._make.Factory):
            assert not attrib.default.takes_self, "not supported yet"
            value = attrib.default.factory()
        else:
            value = attrib.default
        ir = IRNode(name=name, type=type_, opt=opt, val=value)
        children.append(ir)

    return IRNode(name=None, val=children, type=obj_type, opt=False)


def get_structured_config_ir(obj: Any) -> IRNode:
    if is_dataclass(obj):
        return get_dataclass_ir(obj)
    elif is_attr_class(obj):
        return get_attr_ir(obj)
    else:
        raise ValueError(f"Unsupported type: {type(obj).__name__}")
