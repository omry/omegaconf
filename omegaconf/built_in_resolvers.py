import os
import warnings

# from collections.abc import Mapping, MutableMapping
from typing import Any, List, Mapping, Optional, Union

from ._utils import _DEFAULT_MARKER_, Marker, _get_value, decode_primitive
from .base import Container
from .basecontainer import BaseContainer
from .dictconfig import DictConfig
from .errors import ConfigKeyError, ValidationError
from .grammar_parser import parse
from .listconfig import ListConfig
from .nodes import AnyNode
from .omegaconf import OmegaConf

# Special marker use as default value when calling `OmegaConf.select()`. It must be
# different from `_DEFAULT_MARKER_`, which is used by `OmegaConf.select()`.
_DEFAULT_SELECT_MARKER_: Any = Marker("_DEFAULT_SELECT_MARKER_")


def decode(expr: Optional[str], _parent_: Container) -> Any:
    """
    Parse and evaluate `expr` according to the `singleElement` rule of the grammar.

    If `expr` is `None`, then return `None`.
    """
    if expr is None:
        return None

    if not isinstance(expr, str):
        raise TypeError(
            f"`oc.decode` can only take strings or None as input, "
            f"but `{expr}` is of type {type(expr).__name__}"
        )

    parse_tree = parse(expr, parser_rule="singleElement", lexer_mode="VALUE_MODE")
    val = _parent_.resolve_parse_tree(parse_tree)
    return _get_value(val)


def dict_keys(
    in_dict: Union[str, Mapping[Any, Any]],
    _root_: BaseContainer,
    _parent_: Container,
) -> ListConfig:
    in_dict = _get_and_validate_dict_input(
        in_dict, root=_root_, resolver_name="oc.dict.keys"
    )
    assert isinstance(_parent_, BaseContainer)

    ret = OmegaConf.create(list(in_dict.keys()), parent=_parent_)
    assert isinstance(ret, ListConfig)
    return ret


def dict_values(
    in_dict: Union[str, Mapping[Any, Any]], _root_: BaseContainer, _parent_: Container
) -> ListConfig:
    in_dict = _get_and_validate_dict_input(
        in_dict, root=_root_, resolver_name="oc.dict.values"
    )

    if isinstance(in_dict, DictConfig):
        # DictConfig objects are handled in a special way: the goal is to make the
        # returned ListConfig point to the DictConfig nodes through interpolations.

        dict_key: Optional[str] = None
        if in_dict._get_root() is _root_:
            # Try to obtain the full key through which we can access `in_dict`.
            if in_dict is _root_:
                dict_key = ""
            else:
                dict_key = in_dict._get_full_key(None)
                if dict_key:
                    dict_key += "."  # append dot for future concatenation
                else:
                    # This can happen e.g. if `in_dict` is a transient node.
                    dict_key = None

        if dict_key is None:
            # No path to `in_dict` in the existing config.
            raise NotImplementedError(
                "`oc.dict.values` currently only supports input config nodes that "
                "are accessible through the root config. See "
                "https://github.com/omry/omegaconf/issues/650 for details."
            )

        ret = ListConfig([])
        content = in_dict._content
        assert isinstance(content, dict)

        for key, node in content.items():
            ref_node = AnyNode(f"${{{dict_key}{key}}}")
            ret.append(ref_node)

        # Finalize result by setting proper type and parent.
        element_type: Any = in_dict._metadata.element_type
        ret._metadata.element_type = element_type
        ret._metadata.ref_type = List[element_type]
        ret._set_parent(_parent_)

        return ret

    # Other dict-like object: simply create a ListConfig from its values.
    assert isinstance(_parent_, BaseContainer)
    ret = OmegaConf.create(list(in_dict.values()), parent=_parent_)
    assert isinstance(ret, ListConfig)
    return ret


def env(key: str, default: Any = _DEFAULT_MARKER_) -> Optional[str]:
    """
    :param key: Environment variable key
    :param default: Optional default value to use in case the key environment variable is not set.
                    If default is not a string, it is converted with str(default).
                    None default is returned as is.
    :return: The environment variable 'key'. If the environment variable is not set and a default is
            provided, the default is used. If used, the default is converted to a string with str(default).
            If the default is None, None is returned (without a string conversion).
    """
    try:
        return os.environ[key]
    except KeyError:
        if default is not _DEFAULT_MARKER_:
            return str(default) if default is not None else None
        else:
            raise KeyError(f"Environment variable '{key}' not found")


# DEPRECATED: remove in 2.2
def legacy_env(key: str, default: Optional[str] = None) -> Any:
    warnings.warn(
        "The `env` resolver is deprecated, see https://github.com/omry/omegaconf/issues/573"
    )

    try:
        return decode_primitive(os.environ[key])
    except KeyError:
        if default is not None:
            return decode_primitive(default)
        else:
            raise ValidationError(f"Environment variable '{key}' not found")


def _get_and_validate_dict_input(
    in_dict: Union[str, Mapping[Any, Any]],
    root: BaseContainer,
    resolver_name: str,
) -> Mapping[Any, Any]:
    if isinstance(in_dict, str):
        # Path to an existing key in the config: use `select()`.
        key = in_dict
        in_dict = OmegaConf.select(
            root, key, throw_on_missing=True, default=_DEFAULT_SELECT_MARKER_
        )
        if in_dict is _DEFAULT_SELECT_MARKER_:
            raise ConfigKeyError(f"Key not found: '{key}'")

    if not isinstance(in_dict, Mapping):
        raise TypeError(
            f"`{resolver_name}` cannot be applied to objects of type: "
            f"{type(in_dict).__name__}"
        )

    return in_dict
