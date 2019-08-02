import copy
import io
import os
import re
import sys
import warnings
from abc import abstractmethod

import six
import yaml

from .errors import MissingMandatoryValue, FrozenConfigError
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
        u'tag:yaml.org,2002:float',
        re.compile(u'''^(?:
         [-+]?(?:[0-9][0-9_]*)\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?(?:[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)
        |\\.[0-9_]+(?:[eE][-+][0-9]+)?
        |[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+\\.[0-9_]*
        |[-+]?\\.(?:inf|Inf|INF)
        |\\.(?:nan|NaN|NAN))$''', re.X),
        list(u'-+0123456789.'))
    return loader


class Config(object):

    def __init__(self):
        if type(self) == Config:
            raise NotImplementedError

    def save(self, f):
        data = self.pretty()
        if isinstance(f, str):
            with io.open(os.path.abspath(f), 'w', encoding='utf-8') as f:
                f.write(six.u(data))
        elif hasattr(f, 'write'):
            f.write(data)
            f.flush()
        else:
            raise TypeError("Unexpected file type")

    def _set_parent(self, parent):
        assert parent is None or isinstance(parent, Config)
        self.__dict__['parent'] = parent

    def _get_root(self):
        root = self.__dict__['parent']
        if root is None:
            return self
        while root.__dict__['parent'] is not None:
            root = root.__dict__['parent']
        return root

    # noinspection PyProtectedMember
    def __del__(self):
        if 'parent' not in self.__dict__ or self.__dict__['parent'] is None:
            from .omegaconf import OmegaConf
            # root node, remove resolver cache
            id_ = id(self)
            if id_ in OmegaConf._resolvers_cache:
                del OmegaConf._resolvers_cache[id_]

    def freeze(self, flag):
        """
        Freezes this config object
        A frozen config cannot be modified.
        If an attempt ot modify is made a FrozenConfigError will be thrown
        By default config objects are not frozen
        :param flag: True: freeze. False unfreeze, None sets back to default behavior (inherit from parent)
        :return:
        """
        assert flag is None or isinstance(flag, bool)
        self.__dict__['frozen_flag'] = flag

    def _frozen(self):
        """
        Returns True if this config node is frozen.
        A node is frozen if node.freeze(True) was called
        or one if it's parents is frozen
        :return:
        """
        if self.__dict__['frozen_flag'] is not None:
            return self.__dict__['frozen_flag']

        # root leaf, and frozen is not set.
        if self.__dict__['parent'] is None:
            return False
        else:
            return self.__dict__['parent']._frozen()

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
            return type(val) == str and val == '???'

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
        full_key = ''
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
            parent = child.__dict__['parent']

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
        if self._frozen():
            raise FrozenConfigError(self.get_full_key(key))
        self.content.__delitem__(key)

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
        for arg in dotlist:
            args = arg.split('=')
            key = args[0]
            value = None
            if len(args) > 1:
                # load with yaml to get correct automatic typing with the same rules as yaml parsing
                value = yaml.load(args[1], Loader=get_yaml_loader())
            self.update(key, value)

    def update(self, key, value=None):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig
        """Updates a dot separated key sequence to a value"""
        split = key.split('.')
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
        """
        Select a value using dot separated key sequence
        :param key:
        :return:
        """

        split = key.split('.')
        root = self
        for i in range(len(split) - 1):
            if root is None:
                break
            k = split[i]
            root, _ = Config._select_one(root, k)

        if root is None:
            return None

        value, _ = Config._select_one(root, split[-1])
        return value

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
        return Config._to_content(self, resolve)

    def pretty(self, resolve=False):
        """
        returns a yaml dump of this config object.
        :param resolve: if True, will return a string with the interpolations resolved, otherwise
        interpolations are preserved
        :return: A string containing the yaml representation.
        """
        return yaml.dump(self.to_container(resolve=resolve), default_flow_style=False)

    @staticmethod
    def map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""
        from .dictconfig import DictConfig

        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)

        dest = dest.content
        dest = copy.deepcopy(dest)
        src = copy.deepcopy(src)
        for key, value in src.items(resolve=False):
            if key in dest:
                if isinstance(dest[key].value(), Config):
                    if isinstance(value, Config):
                        dest[key].value().merge_with(value)
                    else:
                        dest[key].set_value(value)
                else:
                    dest[key].set_value(src.content[key].value())
            else:
                dest[key] = src.content[key]
        return dest

    def merge_from(self, *others):
        warnings.warn("Use Config.merge_with() (since 1.1.10)", DeprecationWarning,
                      stacklevel=2)

        self.merge_with(*others)

    def merge_with(self, *others):
        from .listconfig import ListConfig
        from .dictconfig import DictConfig
        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if other is None:
                raise ValueError("Cannot merge with a None config")
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                self.__dict__['content'] = Config.map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                self.__dict__['content'] = copy.deepcopy(other.content)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        def re_parent(node):
            # update parents of first level Config nodes to self
            assert isinstance(node, (DictConfig, ListConfig))
            if isinstance(node, DictConfig):
                for _key, value in node.items(resolve=False):
                    if isinstance(value, Config):
                        value._set_parent(node)
                        re_parent(value)
            elif isinstance(node, ListConfig):
                for item in node:
                    if isinstance(item, Config):
                        item._set_parent(node)
                        re_parent(item)

        # recursively correct the parent hierarchy after the merge
        re_parent(self)

    @staticmethod
    def _resolve_value(root_node, inter_type, inter_key):
        from omegaconf import OmegaConf
        inter_type = ('str:' if inter_type is None else inter_type)[0:-1]
        if inter_type == 'str':
            ret = root_node.select(inter_key)
            if ret is None:
                raise KeyError("{} interpolation key '{}' not found".format(inter_type, inter_key))
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                ret = resolver(root_node, inter_key)
            else:
                raise ValueError("Unsupported interpolation type {}".format(inter_type))

        return ret

    def _resolve_single(self, value):
        match_list = list(re.finditer(r"\${(\w+:)?([\w\.%_-]+?)}", value))
        if len(match_list) == 0:
            return value

        root = self._get_root()
        if len(match_list) == 1 and value == match_list[0].group(0):
            # simple interpolation, inherit type
            match = match_list[0]
            return Config._resolve_value(root, match.group(1), match.group(2))
        else:
            orig = value
            new = ''
            last_index = 0
            for match in match_list:
                new_val = Config._resolve_value(root, match.group(1), match.group(2))
                new += orig[last_index:match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return new

    def __deepcopy__(self, memodict={}):
        from omegaconf import OmegaConf
        return OmegaConf.create(self.content)

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
            valid.append(unicode)

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
