import copy
import sys
import warnings
from abc import abstractmethod
from collections import defaultdict
from enum import Enum

import yaml
from typing import Any

from ._utils import (
    get_value_kind,
    ValueKind,
    _maybe_wrap,
    _select_one,
    get_yaml_loader,
    _re_parent,
    is_structured_config,
)
from .errors import (
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
)
from .node import Node
from .nodes import ValueNode


class Container(Node):
    # static fields
    _resolvers = {}

    def __init__(self, element_type, parent: Node):
        super().__init__(parent=parent)
        if type(self) == Container:
            raise NotImplementedError
        self.__dict__["content"] = None
        self.__dict__["_resolver_cache"] = defaultdict(dict)
        self.__dict__["_element_type"] = element_type

    def save(self, f):
        warnings.warn(
            "Use OmegaConf.save(config, filename) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        from omegaconf import OmegaConf

        OmegaConf.save(self, f)

    @abstractmethod
    def get(self, key, default_value=None):
        raise NotImplementedError

    @abstractmethod
    def get_node(self, key):
        """
        returns raw node object for this key
        :param key:
        :return:
        """
        raise NotImplementedError

    def _resolve_with_default(self, key, value, default_value=None):
        """returns the value with the specified key, like obj.key and obj['key']"""

        def is_mandatory_missing(val):
            return type(val) == str and val == "???"

        if isinstance(value, ValueNode):
            value = value.value()

        if default_value is not None and (value is None or is_mandatory_missing(value)):
            value = default_value

        value = self._resolve_single(value) if isinstance(value, str) else value
        if is_mandatory_missing(value):
            raise MissingMandatoryValue(self.get_full_key(key))

        return value

    def get_full_key(self, key):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        full_key = ""
        child = None
        parent = self
        while parent is not None:
            assert isinstance(parent, (DictConfig, ListConfig))
            if isinstance(parent, DictConfig):
                if child is None:
                    full_key = "{}".format(key)
                else:
                    # find which the key for child in the parent
                    for parent_key in parent.keys():
                        if id(parent.get_node(parent_key)) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "{}{}".format(parent_key, full_key)
                            else:
                                full_key = "{}.{}".format(parent_key, full_key)
                            break
            elif isinstance(parent, ListConfig):
                if child is None:
                    if key == "":
                        full_key = key
                    else:
                        full_key = "[{}]".format(key)
                else:
                    for idx, v in enumerate(parent):
                        if id(v) == id(child):
                            if isinstance(child, ListConfig):
                                full_key = "[{}]{}".format(idx, full_key)
                            else:
                                full_key = "[{}].{}".format(idx, full_key)
                            break
            child = parent
            parent = child._get_parent()

        return full_key

    def __str__(self):
        return self.content.__str__()

    def __repr__(self):
        return self.content.__repr__()

    @abstractmethod
    def __eq__(self, other):
        raise NotImplementedError()

    @abstractmethod
    def __ne__(self, other):
        raise NotImplementedError()

    @abstractmethod
    def __hash__(self):
        raise NotImplementedError()

    # Support pickle
    def __getstate__(self):
        return self.__dict__

    # Support pickle
    def __setstate__(self, d):
        self.__dict__.update(d)

    def __delitem__(self, key):
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))
        del self.content[key]

    def __len__(self):
        return self.content.__len__()

    @abstractmethod
    def __iter__(self):
        raise NotImplementedError()

    def merge_with_cli(self):
        args_list = sys.argv[1:]
        self.merge_with_dotlist(args_list)

    def merge_with_dotlist(self, dotlist):
        def fail():
            raise ValueError("Input list must be a list or a tuple of strings")

        if not isinstance(dotlist, (list, tuple)):
            fail()

        for arg in dotlist:
            if not isinstance(arg, str):
                fail()

            idx = arg.find("=")
            if idx == -1:
                key = arg
                value = None
            else:
                key = arg[0:idx]
                value = arg[idx + 1 :]
                value = yaml.load(value, Loader=get_yaml_loader())

            self.update(key, value)

    def update(self, key, value=None):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        """Updates a dot separated key sequence to a value"""
        split = key.split(".")
        root = self
        for i in range(len(split) - 1):
            k = split[i]
            # if next_root is a primitive (string, int etc) replace it with an empty map
            next_root, key_ = _select_one(root, k)
            if not isinstance(next_root, Container):
                root[key_] = {}
            root = root[key_]

        last = split[-1]

        assert isinstance(
            root, Container
        ), f"Unexpected type for root : {type(root).__name__}"

        if isinstance(root, DictConfig):
            root[last] = value
        elif isinstance(root, ListConfig):
            idx = int(last)
            root[idx] = value

    def select(self, key):
        _root, _last_key, value = self._select_impl(key)
        return value

    def _select_impl(self, key):
        """
        Select a value using dot separated key sequence
        :param key:
        :return:
        """

        split = key.split(".")
        root = self
        for i in range(len(split) - 1):
            if root is None:
                break
            k = split[i]
            root, _ = _select_one(root, k)

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = _select_one(root, last_key)
        return root, last_key, value

    def is_empty(self):
        """return true if config is empty"""
        return len(self.content) == 0

    @staticmethod
    def _to_content(conf, resolve, enum_to_str=False):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        def convert(val):
            if enum_to_str:
                if isinstance(val, Enum):
                    val = "{}.{}".format(type(val).__name__, val.name)

            return val

        assert isinstance(conf, Container)
        if isinstance(conf, DictConfig):
            ret = {}
            for key, value in conf.items(resolve=resolve):
                if isinstance(value, Container):
                    ret[key] = Container._to_content(
                        value, resolve=resolve, enum_to_str=enum_to_str
                    )
                else:
                    ret[key] = convert(value)
            return ret
        elif isinstance(conf, ListConfig):
            ret = []
            for index, item in enumerate(conf):
                if resolve:
                    item = conf[index]
                item = convert(item)
                if isinstance(item, Container):
                    item = Container._to_content(
                        item, resolve=resolve, enum_to_str=enum_to_str
                    )
                ret.append(item)
            return ret

    def to_container(self, resolve=False):
        warnings.warn(
            "Use OmegaConf.to_container(config, resolve) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        return Container._to_content(self, resolve)

    def pretty(self, resolve=False):
        from omegaconf import OmegaConf

        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :return: A string containing the yaml representation.
        """
        container = OmegaConf.to_container(self, resolve=resolve, enum_to_str=True)
        return yaml.dump(container, default_flow_style=False, allow_unicode=True)

    @staticmethod
    def _map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""
        from .dictconfig import DictConfig

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)
        src = copy.deepcopy(src)

        for key, value in src.items(resolve=False):
            dest_type = dest.__dict__["_element_type"]
            typed = dest_type not in (None, Any)
            if (dest.get_node(key) is not None) or typed:
                dest_node = dest.get_node(key)
                if dest_node is None and typed:
                    dest[key] = DictConfig(content=dest_type, parent=dest)
                    dest_node = dest.get_node(key)

                if isinstance(dest_node, Container):
                    if isinstance(value, Container):
                        dest_node.merge_with(value)
                    else:
                        dest.__setitem__(key, value)
                else:
                    if isinstance(value, Container):
                        dest.__setitem__(key, value)
                    else:
                        dest_node.set_value(value)
            else:
                dest[key] = src.get_node(key)

    def merge_with(self, *others):
        from .omegaconf import OmegaConf
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if isinstance(other, (dict, list, tuple)) or is_structured_config(other):
                other = OmegaConf.create(other, parent=None)

            if other is None:
                raise ValueError("Cannot merge with a None config")
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                Container._map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                if self._get_flag("readonly"):
                    raise ReadonlyConfigError(self.get_full_key(""))
                self.__dict__["content"].clear()
                for item in other:
                    self.append(item)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        # recursively correct the parent hierarchy after the merge
        _re_parent(self)

    @staticmethod
    def _resolve_value(root_node, inter_type, inter_key):
        from omegaconf import OmegaConf

        inter_type = ("str:" if inter_type is None else inter_type)[0:-1]
        if inter_type == "str":
            parent, last_key, value = root_node._select_impl(inter_key)
            if parent is None or (value is None and last_key not in parent):
                raise KeyError(
                    "{} interpolation key '{}' not found".format(inter_type, inter_key)
                )
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                value = resolver(root_node, inter_key)
            else:
                raise UnsupportedInterpolationType(
                    "Unsupported interpolation type {}".format(inter_type)
                )

        return value

    def _resolve_single(self, value):
        value_kind, match_list = get_value_kind(value=value, return_match_list=True)

        if value_kind in (ValueKind.VALUE, ValueKind.MANDATORY_MISSING):
            return value

        root = self._get_root()
        if value_kind == ValueKind.INTERPOLATION:
            # simple interpolation, inherit type
            match = match_list[0]
            return Container._resolve_value(root, match.group(1), match.group(2))
        elif value_kind == ValueKind.STR_INTERPOLATION:
            # Concatenated interpolation, always a string
            orig = value
            new = ""
            last_index = 0
            for match in match_list:
                new_val = Container._resolve_value(root, match.group(1), match.group(2))
                new += orig[last_index : match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return new

    # noinspection PyProtectedMember
    def _set_item_impl(self, key, value):
        must_wrap = isinstance(value, (dict, list))
        input_config = isinstance(value, Container)
        input_node = isinstance(value, ValueNode)
        if isinstance(self.__dict__["content"], dict):
            target_node = key in self.__dict__["content"] and isinstance(
                self.__dict__["content"][key], ValueNode
            )

        elif isinstance(self.__dict__["content"], list):
            target_node = self.__dict__["content"] and isinstance(
                self.__dict__["content"][key], ValueNode
            )

        def wrap(val):
            return _maybe_wrap(
                annotated_type=self.__dict__["_element_type"],
                value=val,
                is_optional=True,
                parent=self,
            )

        if must_wrap:
            self.__dict__["content"][key] = wrap(value)
        elif input_node and target_node:
            # both nodes, replace existing node with new one
            value._set_parent(self)
            self.__dict__["content"][key] = value
        elif not input_node and target_node:
            # input is not node, can be primitive or config
            if input_config:
                value._set_parent(self)
                self.__dict__["content"][key] = value
            else:
                self.__dict__["content"][key].set_value(value)
        elif input_node and not target_node:
            # target must be config, replace target with input node
            value._set_parent(self)
            self.__dict__["content"][key] = value
        elif not input_node and not target_node:
            # target must be config.
            # input can be primitive or config
            if input_config:
                value._set_parent(self)
                self.__dict__["content"][key] = value
            else:
                self.__dict__["content"][key] = wrap(value)

    @staticmethod
    def _item_eq(c1, k1, c2, k2):
        v1 = c1.content[k1]
        v2 = c2.content[k2]
        if isinstance(v1, ValueNode):
            v1 = v1.value()
            if isinstance(v1, str):
                # noinspection PyProtectedMember
                v1 = c1._resolve_single(v1)
        if isinstance(v2, ValueNode):
            v2 = v2.value()
            if isinstance(v2, str):
                # noinspection PyProtectedMember
                v2 = c2._resolve_single(v2)

        if isinstance(v1, Container) and isinstance(v2, Container):
            if not Container._config_eq(v1, v2):
                return False
        return v1 == v2

    @staticmethod
    def _list_eq(l1, l2):
        from .listconfig import ListConfig

        assert isinstance(l1, ListConfig)
        assert isinstance(l2, ListConfig)
        if len(l1) != len(l2):
            return False
        for i in range(len(l1)):
            if not Container._item_eq(l1, i, l2, i):
                return False

        return True

    @staticmethod
    def _dict_conf_eq(d1, d2):
        from .dictconfig import DictConfig

        assert isinstance(d1, DictConfig)
        assert isinstance(d2, DictConfig)
        if len(d1) != len(d2):
            return False
        k1 = sorted(d1.keys())
        k2 = sorted(d2.keys())
        if k1 != k2:
            return False
        for k in k1:
            if not Container._item_eq(d1, k, d2, k):
                return False

        return True

    @staticmethod
    def _config_eq(c1, c2):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        assert isinstance(c1, Container)
        assert isinstance(c2, Container)
        if isinstance(c1, DictConfig) and isinstance(c2, DictConfig):
            return DictConfig._dict_conf_eq(c1, c2)
        if isinstance(c1, ListConfig) and isinstance(c2, ListConfig):
            return Container._list_eq(c1, c2)
        # if type does not match objects are different
        return False
