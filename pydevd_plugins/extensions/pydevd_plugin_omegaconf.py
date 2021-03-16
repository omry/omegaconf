# based on https://github.com/fabioz/PyDev.Debugger/tree/main/pydevd_plugins/extensions
import os
import sys
from functools import lru_cache
from typing import Any, Dict, Sequence

from _pydevd_bundle.pydevd_extension_api import (  # type: ignore
    StrPresentationProvider,
    TypeResolveProvider,
)


@lru_cache(maxsize=128)
def find_mod_attr(mod_name: str, attr: str) -> Any:
    mod = sys.modules.get(mod_name)
    return getattr(mod, attr, None)


class OmegaConfDeveloperResolver(object):
    def can_provide(self, type_object: Any, type_name: str) -> bool:
        Node = find_mod_attr("omegaconf", "Node")
        return Node is not None and issubclass(type_object, Node)

    def resolve(self, obj: Any, attribute: str) -> Any:
        return getattr(obj, attribute)

    def get_dictionary(self, obj: Any) -> Any:
        return obj.__dict__


class OmegaConfUserResolver(StrPresentationProvider):  # type: ignore
    def can_provide(self, type_object: Any, type_name: str) -> bool:
        Node = find_mod_attr("omegaconf", "Node")
        return Node is not None and issubclass(type_object, Node)

    def resolve(self, obj: Any, attribute: Any) -> Any:
        if isinstance(obj, Sequence) and isinstance(attribute, str):
            attribute = int(attribute)
        val = obj.__dict__["_content"][attribute]

        return val

    def _is_simple_value(self, val: Any) -> bool:
        ValueNode = find_mod_attr("omegaconf", "ValueNode")
        return (
            isinstance(val, ValueNode)
            and not val._is_none()
            and not val._is_missing()
            and not val._is_interpolation()
        )

    def get_dictionary(self, obj: Any) -> Dict[str, Any]:
        ListConfig = find_mod_attr("omegaconf", "ListConfig")
        DictConfig = find_mod_attr("omegaconf", "DictConfig")
        Node = find_mod_attr("omegaconf", "Node")

        if isinstance(obj, Node):
            obj = obj._dereference_node(throw_on_resolution_failure=False)
            if obj is None or obj._is_none() or obj._is_missing():
                return {}

        if isinstance(obj, DictConfig):
            d = {}
            for k, v in obj.__dict__["_content"].items():
                if self._is_simple_value(v):
                    v = v._value()
                d[k] = v
        elif isinstance(obj, ListConfig):
            d = {}
            for idx, v in enumerate(obj.__dict__["_content"]):
                if self._is_simple_value(v):
                    v = v._value()
                d[str(idx)] = v
        else:
            d = {}

        return d

    def get_str(self, val: Any) -> str:
        IRE = find_mod_attr("omegaconf.errors", "InterpolationResolutionError")

        if val._is_missing():
            return "??? <MISSING>"
        if val._is_interpolation():
            try:
                dr = val._dereference_node()
            except IRE as e:
                dr = f"ERR: {e}"
            return f"{val._value()} -> {dr}"
        else:
            return f"{val}"


# OC_PYDEVD_RESOLVER env can take:
#  DISABLE: Do not install a pydevd resolver
#  USER: Install a resolver for OmegaConf users (default)
#  DEV: Install a resolver for OmegaConf developers. Shows underlying data-model in the debugger.
resolver = os.environ.get("OC_PYDEVD_RESOLVER", "USER").upper()
if resolver != "DISABLE":  # pragma: no cover
    if resolver == "USER":
        TypeResolveProvider.register(OmegaConfUserResolver)
    elif resolver == "DEV":
        TypeResolveProvider.register(OmegaConfDeveloperResolver)
    else:
        sys.stderr.write(
            f"OmegaConf pydev plugin: Not installing. Unknown mode {resolver}. Supported one of [USER, DEV, DISABLE]\n"
        )
