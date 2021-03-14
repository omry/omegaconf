# based on https://github.com/fabioz/PyDev.Debugger/tree/main/pydevd_plugins/extensions

import sys
from functools import lru_cache
from typing import Any, Dict

from _pydevd_bundle.pydevd_extension_api import TypeResolveProvider  # type: ignore

from omegaconf._utils import type_str


@lru_cache(maxsize=128)
def find_mod_attr(mod_name: str, attr: str) -> Any:
    mod = sys.modules.get(mod_name)
    return getattr(mod, attr, None)


class Wrapper(object):
    def __init__(self, target: Any, desc: str) -> None:
        self.target = target
        self.desc = desc

    def __repr__(self) -> str:  # pragma: no cover
        return self.desc

    def __getattr__(self, attr: str) -> Any:  # pragma: no cover
        return getattr(self.target, attr)

    def __eq__(self, other: Any) -> Any:  # pragma: no cover
        if isinstance(other, Wrapper):
            return self.desc == other.desc and self.target == other.target
        else:
            return NotImplemented

    def __ne__(self, other: Any) -> Any:  # pragma: no cover
        return not self.__eq__(other)


class OmegaConfNodeResolver(object):
    def can_provide(self, type_object: Any, type_name: str) -> bool:
        Node = find_mod_attr("omegaconf", "Node")

        return Node is not None and issubclass(type_object, (Node, Wrapper))

    def resolve(self, obj: Any, attribute: str) -> Any:
        Node = find_mod_attr("omegaconf", "Node")
        DictConfig = find_mod_attr("omegaconf", "DictConfig")
        ListConfig = find_mod_attr("omegaconf", "ListConfig")
        ValueNode = find_mod_attr("omegaconf", "ValueNode")

        if isinstance(obj, Wrapper):
            obj = obj.target

        if attribute == "->" and isinstance(obj, Node):
            field = obj._dereference_node(throw_on_resolution_failure=False)
        elif isinstance(obj, DictConfig):
            field = obj.__dict__["_content"][attribute]
        elif isinstance(obj, ListConfig):
            field = obj.__dict__["_content"][int(attribute)]
        else:  # pragma: no cover
            assert False

        if isinstance(field, Node) and field._is_interpolation():
            resolved = field._dereference_node(throw_on_resolution_failure=False)
            if resolved is not None:
                if isinstance(resolved, ValueNode):
                    resolved_type = type_str(type(resolved._val))
                else:
                    resolved_type = type_str(type(resolved))
                desc = f"{field} -> {{ {resolved_type} }} {resolved}"
                field = Wrapper(field, desc)

        return field

    def get_dictionary(self, obj: Any) -> Dict[str, Any]:
        ListConfig = find_mod_attr("omegaconf", "ListConfig")
        DictConfig = find_mod_attr("omegaconf", "DictConfig")
        Node = find_mod_attr("omegaconf", "Node")
        ValueNode = find_mod_attr("omegaconf", "ValueNode")

        if isinstance(obj, Wrapper):
            obj = obj.target

        assert isinstance(obj, Node)

        d = {}

        if isinstance(obj, Node):
            if obj._is_missing() or obj._is_none():
                return {}
            if obj._is_interpolation():
                d["interpolation"] = obj._value()
                if obj._parent is not None:
                    resolved = obj._dereference_node(throw_on_resolution_failure=False)
                else:
                    resolved = None
                d["->"] = resolved
                return d
            else:
                if isinstance(obj, ValueNode):
                    d["_val"] = obj._value()

        if isinstance(obj, ListConfig):
            assert not obj._is_interpolation()
            assert not obj._is_none()
            assert not obj._is_missing()
            for idx, node in enumerate(obj.__dict__["_content"]):
                d[str(idx)] = node
        elif isinstance(obj, DictConfig):
            assert not obj._is_interpolation()
            assert not obj._is_none()
            assert not obj._is_missing()
            for key in obj.keys():
                node = obj._get_node(key, throw_on_missing_value=False)
                is_inter = node._is_interpolation()
                if is_inter:
                    resolved = node._dereference_node(throw_on_resolution_failure=False)
                    if resolved is not None:
                        value = resolved
                    else:
                        value = node
                else:
                    value = node._value()

                d[key] = value
        return d


TypeResolveProvider.register(OmegaConfNodeResolver)
