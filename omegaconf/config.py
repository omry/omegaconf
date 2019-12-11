import copy
import sys
import warnings
from abc import abstractmethod
from collections import defaultdict

import re
import six
import yaml

from .errors import (
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
)
from .nodes import BaseNode


def isint(s):
    try:
        int(s)
        return True
    except ValueError:
        return False


def get_yaml_loader():
    loader = yaml.SafeLoader
    loader.add_implicit_resolver(
        u"tag:yaml.org,2002:float",
        re.compile(
            u"""^(?:
         [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
        |\\.[0-9_]+(?:[eE][-+][0-9]+)?
        |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
        |[-+]?\\.(?:inf|Inf|INF)
        |\\.(?:nan|NaN|NAN))$""",
            re.X,
        ),
        list(u"-+0123456789."),
    )
    loader.yaml_implicit_resolvers = {
        key: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != u"tag:yaml.org,2002:timestamp"
        ]
        for key, resolvers in loader.yaml_implicit_resolvers.items()
    }
    return loader


class Config(object):
    # static fields
    _resolvers = {}

    def __init__(self):
        if type(self) == Config:
            raise NotImplementedError
        # Flags have 3 modes:
        #   unset : inherit from parent, defaults to false in top level config.
        #   set to true: flag is true
        #   set to false: flag is false
        self.__dict__["flags"] = dict(
            # Read only config cannot be modified
            readonly=None,
            # Struct config throws a KeyError if a non existing field is accessed
            struct=None,
        )
        self.__dict__["_resolver_cache"] = defaultdict(dict)

    def save(self, f):
        warnings.warn(
            "Use OmegaConf.save(config, filename) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        from omegaconf import OmegaConf

        OmegaConf.save(self, f)

    def _set_parent(self, parent):
        assert parent is None or isinstance(parent, Config)
        self.__dict__["parent"] = parent

    def _get_root(self):
        root = self.__dict__["parent"]
        if root is None:
            return self
        while root.__dict__["parent"] is not None:
            root = root.__dict__["parent"]
        return root

    def _set_flag(self, flag, value):
        assert value is None or isinstance(value, bool)
        self.__dict__["flags"][flag] = value

    def _get_node_flag(self, flag):
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        return self.__dict__["flags"][flag]

    def _get_flag(self, flag):
        """
        Returns True if this config node flag is set
        A flag is set if node.set_flag(True) was called
        or one if it's parents is flag is set
        :return:
        """
        assert flag in self.__dict__["flags"]
        if flag in self.__dict__["flags"] and self.__dict__["flags"][flag] is not None:
            return self.__dict__["flags"][flag]

        # root leaf, and frozen is not set.
        if self.__dict__["parent"] is None:
            return False
        else:
            # noinspection PyProtectedMember
            return self.__dict__["parent"]._get_flag(flag)

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

        if isinstance(value, BaseNode):
            value = value.value()

        if default_value is not None and (value is None or is_mandatory_missing(value)):
            value = default_value

        if is_mandatory_missing(value):
            raise MissingMandatoryValue(self.get_full_key(key))

        return self._resolve_single(value) if isinstance(value, str) else value

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
                    for parent_key, v in parent.items():
                        if id(v) == id(child):
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
            parent = child.__dict__["parent"]

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

    def __contains__(self, item):
        return self.content.__contains__(item)

    @staticmethod
    def _select_one(c, key_):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        assert isinstance(c, (DictConfig, ListConfig))
        if isinstance(c, DictConfig):
            if key_ in c:
                return c[key_], key_
            else:
                return None, key_
        elif isinstance(c, ListConfig):
            if not isint(key_):
                raise TypeError("Index {} is not an int".format(key_))
            idx = int(key_)
            if idx < 0 or idx + 1 > len(c):
                return None, idx
            return c[idx], idx

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
            next_root, key_ = Config._select_one(root, k)
            if not isinstance(next_root, Config):
                root[key_] = {}
            root = root[key_]

        last = split[-1]

        assert isinstance(root, (DictConfig, ListConfig))
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
            root, _ = Config._select_one(root, k)

        if root is None:
            return None, None, None

        last_key = split[-1]
        value, _ = Config._select_one(root, last_key)
        return root, last_key, value

    def is_empty(self):
        """return true if config is empty"""
        return len(self.content) == 0

    @staticmethod
    def _to_content(conf, resolve):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        assert isinstance(conf, Config)
        if isinstance(conf, DictConfig):
            ret = {}
            for key, value in conf.items(resolve=resolve):
                if isinstance(value, Config):
                    ret[key] = Config._to_content(value, resolve)
                else:
                    ret[key] = value
            return ret
        elif isinstance(conf, ListConfig):
            ret = []
            for index, item in enumerate(conf):
                if resolve:
                    item = conf[index]
                if isinstance(item, Config):
                    item = Config._to_content(item, resolve)
                ret.append(item)
            return ret

    def to_container(self, resolve=False):
        warnings.warn(
            "Use OmegaConf.to_container(config, resolve) (since 1.4.0)",
            DeprecationWarning,
            stacklevel=2,
        )

        return Config._to_content(self, resolve)

    def pretty(self, resolve=False):
        from omegaconf import OmegaConf

        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :return: A string containing the yaml representation.
        """
        return yaml.dump(
            OmegaConf.to_container(self, resolve=resolve), default_flow_style=False
        )

    @staticmethod
    def _map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""
        from .dictconfig import DictConfig

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)
        src = copy.deepcopy(src)

        for key, value in src.items(resolve=False):
            if key in dest:
                dest_node = dest.get_node(key)
                if isinstance(dest_node, Config):
                    if isinstance(value, Config):
                        dest_node.merge_with(value)
                    else:
                        dest.__setitem__(key, value)
                else:
                    if isinstance(value, Config):
                        dest.__setitem__(key, value)
                    else:
                        dest_node.set_value(value)
            else:
                dest[key] = src.get_node(key)

    def _deepcopy_impl(self, res, _memodict={}):
        # memodict is intentionally not used.
        # Using it can cause python to return objects that were since modified, undoing their modifications!
        res.__dict__["content"] = copy.deepcopy(self.__dict__["content"])
        res.__dict__["flags"] = copy.deepcopy(self.__dict__["flags"])
        # intentionally not deepcopying the parent. this can cause all sorts of mayhem and stack overflow.
        # instead of just re-parent the result node. this will break interpolation in cases of deepcopying
        # a node that is not the root node, but that is almost guaranteed to break anyway.
        Config._re_parent(res)

    @staticmethod
    def _re_parent(node):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        # update parents of first level Config nodes to self
        assert isinstance(node, (DictConfig, ListConfig))
        if isinstance(node, DictConfig):
            for _key, value in node.items(resolve=False):
                if isinstance(value, Config):
                    value._set_parent(node)
                    Config._re_parent(value)
        elif isinstance(node, ListConfig):
            for item in node:
                if isinstance(item, Config):
                    item._set_parent(node)
                    Config._re_parent(item)

    def merge_with(self, *others):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if other is None:
                raise ValueError("Cannot merge with a None config")
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                Config._map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                if self._get_flag("readonly"):
                    raise ReadonlyConfigError(self.get_full_key(""))

                self.__dict__["content"] = copy.deepcopy(other.content)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        # recursively correct the parent hierarchy after the merge
        Config._re_parent(self)

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
        key_prefix = r"\${(\w+:)?"
        legal_characters = r"([\w\.%_ \\,-]*?)}"
        match_list = list(re.finditer(key_prefix + legal_characters, value))
        if len(match_list) == 0:
            return value

        root = self._get_root()
        if len(match_list) == 1 and value == match_list[0].group(0):
            # simple interpolation, inherit type
            match = match_list[0]
            return Config._resolve_value(root, match.group(1), match.group(2))
        else:
            orig = value
            new = ""
            last_index = 0
            for match in match_list:
                new_val = Config._resolve_value(root, match.group(1), match.group(2))
                new += orig[last_index : match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return new

    def _prepare_value_to_add(self, key, value):
        from omegaconf import OmegaConf

        if isinstance(value, Config):
            value = OmegaConf.to_container(value)

        if isinstance(value, (dict, list, tuple)):

            value = OmegaConf.create(value, parent=self)

        if not Config.is_primitive_type(value):
            full_key = self.get_full_key(key)
            raise ValueError(
                "key {}: {} is not a primitive type".format(
                    full_key, type(value).__name__
                )
            )

        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))

        return value

    @staticmethod
    def is_primitive_type(value):
        """
        Ensures this value type is of a valid type
        Throws ValueError otherwise
        :param value:
        :return:
        """
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        # None is valid
        if value is None:
            return True
        valid = [bool, int, str, float, DictConfig, ListConfig, BaseNode]
        if six.PY2:
            valid.append(unicode)  # noqa F821

        return isinstance(value, tuple(valid))

    @staticmethod
    def _item_eq(c1, k1, c2, k2):
        v1 = c1.content[k1]
        v2 = c2.content[k2]
        if isinstance(v1, BaseNode):
            v1 = v1.value()
            if isinstance(v1, str):
                # noinspection PyProtectedMember
                v1 = c1._resolve_single(v1)
        if isinstance(v2, BaseNode):
            v2 = v2.value()
            if isinstance(v2, str):
                # noinspection PyProtectedMember
                v2 = c2._resolve_single(v2)

        if isinstance(v1, Config) and isinstance(v2, Config):
            if not Config._config_eq(v1, v2):
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
            if not Config._item_eq(l1, i, l2, i):
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
            if not Config._item_eq(d1, k, d2, k):
                return False

        return True

    @staticmethod
    def _config_eq(c1, c2):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig

        assert isinstance(c1, Config)
        assert isinstance(c2, Config)
        if isinstance(c1, DictConfig) and isinstance(c2, DictConfig):
            return DictConfig._dict_conf_eq(c1, c2)
        if isinstance(c1, ListConfig) and isinstance(c2, ListConfig):
            return Config._list_eq(c1, c2)
        # if type does not match objects are different
        return False
