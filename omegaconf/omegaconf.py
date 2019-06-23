"""OmegaConf module"""
import copy
import io
import os
import re
import sys
from collections import Sequence
from collections import defaultdict

import yaml
from deprecated import deprecated


class MissingMandatoryValue(Exception):
    """Thrown when a variable flagged with '???' value is accessed to
    indicate that the value was not set"""


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


def register_default_resolvers():
    def env(key):
        try:
            return os.environ[key]
        except KeyError:
            raise KeyError("Environment variable '{}' not found".format(key))

    OmegaConf.register_resolver('env', env)


class Config(object):

    def __init__(self):
        """
        Can't be instantiated
        """
        raise NotImplementedError

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

    def get(self, key, default_value=None):
        raise NotImplementedError

    def _resolve_with_default(self, key, value, default_value=None):
        """returns the value with the specified key, like obj.key and obj['key']"""

        def is_mandatory_missing():
            return type(value) == str and value == '???'

        if default_value is not None and (value is None or is_mandatory_missing()):
            value = default_value
        if is_mandatory_missing():
            raise MissingMandatoryValue(self.get_full_key(key))
        return self._resolve_single(value) if isinstance(value, str) else value

    def get_full_key(self, key):
        full_key = ''
        child = None
        parent = self
        while parent is not None:
            if isinstance(parent, DictConfig):
                if child is None:
                    full_key = "{}".format(key)
                else:
                    for parent_key, v in parent.items():
                        if v == child:
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
                        if v == child:
                            if isinstance(child, ListConfig):
                                full_key = "[{}]{}".format(idx, full_key)
                            else:
                                full_key = "[{}].{}".format(idx, full_key)
                            break
            else:
                raise TypeError
            child = parent
            parent = child.__dict__['parent']

        return full_key

    def __str__(self):
        return self.content.__str__()

    def __repr__(self):
        return self.content.__repr__()

    def __eq__(self, other):
        return other == self.content

    # Support pickle
    def __getstate__(self):
        return self.__dict__

    # Support pickle
    def __setstate__(self, d):
        self.__dict__.update(d)

    def __delitem__(self, key):
        self.content.__delitem__(key)

    def __len__(self):
        return self.content.__len__()

    def __iter__(self):
        return self.content.__iter__()

    def __contains__(self, item):
        return self.content.__contains__(item)

    @staticmethod
    def _select_one(c, key_):

        def isint(s):
            try:
                int(s)
                return True
            except ValueError:
                return False

        if isinstance(c, DictConfig):
            if key_ in c:
                return c[key_], key_
            else:
                return None, key_
        elif isinstance(c, ListConfig):
            if not isint(key_):
                raise ValueError("Index {} is not an int".format(key_))
            idx = int(key_)
            if idx < 0 or idx + 1 > len(c):
                return None, idx
            return c[idx], idx
        else:
            raise TypeError("Unexpected config type")

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

        assert isinstance(root, Config)
        if isinstance(root, DictConfig):
            root[last] = value
        elif isinstance(root, ListConfig):
            idx = int(last)
            root[idx] = value
        else:
            raise TypeError()

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
    def _to_content(conf):
        if isinstance(conf, Config):
            conf = conf.content

        if isinstance(conf, dict):
            ret = {}
            for key, value in conf.items():
                if isinstance(value, Config):
                    ret[key] = Config._to_content(value)
                else:
                    ret[key] = value
            return ret
        elif isinstance(conf, Sequence):
            ret = []
            for item in conf:
                if isinstance(item, Config):
                    item = Config._to_content(item)
                ret.append(item)
            return ret

    def to_container(self):
        return Config._to_content(self)

    def to_dict(self):
        content = Config._to_content(self)
        assert isinstance(content, dict), "Configuration is a {} and not a dictionary".format(type(content))
        return content

    def to_list(self):
        content = Config._to_content(self)
        assert isinstance(content, Sequence), "Configuration is a {} and not a Sequence".format(type(content))
        return content

    def pretty(self):
        """return a pretty dump of the config content"""
        return yaml.dump(self.to_container(), default_flow_style=False)

    @staticmethod
    def map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""
        assert isinstance(dest, DictConfig)
        assert isinstance(src, DictConfig)

        dest = dest.content
        dest = copy.deepcopy(dest)
        src = copy.deepcopy(src)
        for key, value in src.items():
            if key in dest and isinstance(dest[key], Config):
                if isinstance(value, Config):
                    dest[key].merge_with(value)
                else:
                    dest[key] = value
            else:
                dest[key] = src[key]
        return dest

    @deprecated(version='1.1.10', reason="Use Config.merge_with(), this function will be removed soon")
    def merge_from(self, *others):
        self.merge_with(*others)

    def merge_with(self, *others):
        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            if isinstance(self, DictConfig) and isinstance(other, DictConfig):
                self.__dict__['content'] = Config.map_merge(self, other)
            elif isinstance(self, ListConfig) and isinstance(other, ListConfig):
                self.__dict__['content'] = copy.deepcopy(other.content)
            else:
                raise TypeError("Merging DictConfig with ListConfig is not supported")

        def re_parent(node):
            # update parents of first level Config nodes to self
            if isinstance(node, DictConfig):
                for _key, value in node.items():
                    if isinstance(value, Config):
                        value._set_parent(node)
                        re_parent(value)
            elif isinstance(node, ListConfig):
                for item in node:
                    if isinstance(item, Config):
                        item._set_parent(node)
                        re_parent(item)
            else:
                raise TypeError()

        # recursively correct the parent hierarchy after the merge
        re_parent(self)

    @staticmethod
    def resolve_value(root_node, inter_type, inter_key):
        inter_type = ('str:' if inter_type is None else inter_type)[0:-1]
        if inter_type == 'str':
            ret = root_node.select(inter_key)
            if ret is None:
                raise KeyError("{} interpolation key '{}' not found".format(inter_type, inter_key))
        else:
            resolver = OmegaConf.get_resolver(inter_type)
            if resolver is not None:
                ret = resolver(inter_key)
                if ret is None:
                    raise KeyError("{} failed to resolve {}".format(inter_type, inter_key))
            else:
                raise ValueError("Unsupported interpolation type {}".format(inter_type))

        if isinstance(ret, Config):
            # Currently this is not supported. interpolated value must be a primitive
            raise ValueError("String interpolation key '{}' refer a config node".format(inter_key))

        return ret

    def _resolve_single(self, value):
        if value is None:
            return None
        match_list = list(re.finditer(r"\${(\w+:)?([\w\.%_-]+?)}", value))
        if len(match_list) == 0:
            return value

        root = self._get_root()
        if len(match_list) == 1 and value == match_list[0].group(0):
            # simple interpolation, inherit type
            match = match_list[0]
            return Config.resolve_value(root, match.group(1), match.group(2))
        else:
            orig = value
            new = ''
            last_index = 0
            for match in match_list:
                new_val = Config.resolve_value(root, match.group(1), match.group(2))
                new += orig[last_index:match.start(0)] + str(new_val)
                last_index = match.end(0)

            new += orig[last_index:]
            return new

    def __deepcopy__(self, memodict={}):
        return OmegaConf.create(self.content)


class DictConfig(Config):
    def __init__(self, content, parent=None):
        assert isinstance(content, dict)
        self.__dict__['content'] = {}
        self.__dict__['parent'] = parent
        for k, v in content.items():
            self[k] = v

    def __setitem__(self, key, value):
        assert isinstance(key, str)
        if not isinstance(value, Config) and (isinstance(value, dict) or isinstance(value, list)):
            value = OmegaConf.create(value, parent=self)
        self.__dict__['content'][key] = value

    # hide content while inspecting in debugger
    def __dir__(self):
        return self.content.keys()

    def __setattr__(self, key, value):
        """
        Allow assigning attributes to DictConfig
        :param key:
        :param value:
        :return:
        """
        if isinstance(value, (dict, list, tuple)):
            value = OmegaConf.create(value, parent=self)
        self.content[key] = value

    def __getattr__(self, key):
        """
        Allow accessing dictionary values as attributes
        :param key:
        :return:
        """
        return self._resolve_with_default(key=key, value=self.content[key], default_value=None)

    def __getitem__(self, key):
        """
        Allow map style access
        :param key:
        :return:
        """
        return self.__getattr__(key)

    def get(self, key, default_value=None):
        return self._resolve_with_default(key=key, value=self.content.get(key), default_value=default_value)

    __marker = object()

    def pop(self, key, default=__marker):
        val = self.content.pop(key, default)
        if val is self.__marker:
            raise KeyError(key)
        return val

    def keys(self):
        return self.content.keys()

    def items(self):
        return self.content.items()


class ListConfig(Config, list):
    def __init__(self, content, parent=None):
        assert isinstance(content, (list, tuple))
        self.__dict__['content'] = []
        self.__dict__['parent'] = parent
        for item in content:
            if isinstance(item, dict) or isinstance(item, (list, tuple)):
                item = OmegaConf.create(item, parent=self)
            self.append(item)

    # hide content while inspecting in debugger
    def __dir__(self):
        return dir(self.content)

    def __getitem__(self, item):
        return self.content[item]

    def get(self, key, default_value=None):
        return self._resolve_with_default(key=key, value=self.content[key], default_value=default_value)

    def __setitem__(self, index, value):
        assert isinstance(index, int)
        if not isinstance(value, Config) and (isinstance(value, dict) or isinstance(value, list)):
            value = OmegaConf.create(value, parent=self)
        self.__dict__['content'][index] = value

    def pop(self, key=-1):
        return self.content.pop(key)

    def append(self, value):
        if not isinstance(value, Config) and (isinstance(value, dict) or isinstance(value, list)):
            value = OmegaConf.create(value, parent=self)
        self.__dict__['content'].append(value)

    def insert(self, index, item):
        self.cotnent.insert(index, item)

    def sort(self, key=None, reverse=False):
        self.content.sort(key, reverse)


class OmegaConf:
    """OmegaConf primary class"""

    def __init__(self):
        raise NotImplementedError("Use one of the static construction functions")

    @staticmethod
    def create(obj=None, parent=None):
        if isinstance(obj, str):
            new_obj = yaml.load(obj, Loader=get_yaml_loader())
            if new_obj is None:
                new_obj = {}
            elif isinstance(new_obj, str):
                new_obj = {obj: None}
            return OmegaConf.create(new_obj)
        else:
            if obj is None:
                obj = {}

            if isinstance(obj, dict):
                return DictConfig(obj, parent)
            elif isinstance(obj, (list, tuple)):
                return ListConfig(obj, parent)
            else:
                raise RuntimeError("Unsupported type {}".format(type(obj).__name__))

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.create(), this function will be removed soon")
    def empty():
        """Creates an empty config"""
        return Config(content=None)

    @staticmethod
    def load(file_):
        if isinstance(file_, str):
            with io.open(os.path.abspath(file_), 'r') as f:
                return OmegaConf.create(yaml.load(f, Loader=get_yaml_loader()))
        elif getattr(file_, 'read'):
            return OmegaConf.create(yaml.load(file_, Loader=get_yaml_loader()))
        else:
            raise ValueError("Unexpected file type")

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.load(), this function will be removed soon")
    def from_filename(filename):
        """Creates config from the content of the specified filename"""
        assert isinstance(filename, str)
        return OmegaConf.load(filename)

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.load(), this function will be removed soon")
    def from_file(file_):
        """Creates config from the content of the specified file object"""
        return OmegaConf.load(file_)

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.create(), this function will be removed soon")
    def from_string(content):
        """Creates config from the content of string"""
        assert isinstance(content, str)
        yamlstr = yaml.load(content, Loader=get_yaml_loader())
        return OmegaConf.create(yamlstr)

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.create(), this function will be removed soon")
    def from_dict(dict_):
        """Creates config from a dictionary"""
        assert isinstance(dict_, dict)
        return OmegaConf.create(dict_)

    @staticmethod
    @deprecated(version='1.1.5', reason="Use OmegaConf.create(), this function will be removed soon")
    def from_list(list_):
        """Creates config from a list"""
        assert isinstance(list_, list)
        return OmegaConf.create(list_)

    @staticmethod
    def from_cli(args_list=None):
        if args_list is None:
            # Skip program name
            args_list = sys.argv[1:]
        return OmegaConf.from_dotlist(args_list)

    @staticmethod
    def from_dotlist(dotlist):
        """
        Creates config from the content sys.argv or from the specified args list of not None
        :param dotlist:
        :return:
        """
        conf = OmegaConf.create()
        conf.merge_with_dotlist(dotlist)
        return conf

    @staticmethod
    def merge(*others):
        """Merge a list of previously created configs into a single one"""
        assert len(others) > 0
        target = copy.deepcopy(others[0])
        target.merge_with(*others[1:])
        return target

    _resolvers = {}
    _resolvers_cache = defaultdict(dict)

    @staticmethod
    def register_resolver(name, resolver):
        assert callable(resolver), "resolver must be callable"
        assert name not in OmegaConf._resolvers, "resolved {} is already registered".format(name)

        def caching(key):
            cache = OmegaConf._resolvers_cache[name]
            val = cache[key] if key in cache else resolver(key)
            cache[key] = val
            return val

        OmegaConf._resolvers[name] = caching

    @staticmethod
    def get_resolver(name):
        return OmegaConf._resolvers[name] if name in OmegaConf._resolvers else None

    @staticmethod
    def clear_resolvers():
        OmegaConf._resolvers = {}
        OmegaConf._resolvers_cache = defaultdict(dict)
        register_default_resolvers()


# register all default resolvers
register_default_resolvers()
