"""OmegaConf module"""
import io
import sys
import os
import six
import yaml
import re


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


if six.PY2:
    from collections import MutableMapping
else:
    from collections.abc import MutableMapping


class Config(MutableMapping):
    """Config implementation"""

    def __init__(self, content, parent=None):
        self._set_parent(parent)
        if content is None:
            self.set_dict({})
        else:
            if isinstance(content, str):
                self.set_dict({content: None})
            elif isinstance(content, dict):
                self.set_dict(content)
            else:
                raise TypeError()

    def get(self, key, default_value=None):
        """returns the value with the specified key, like obj.key and obj['key']"""
        v = self.__getattr__(key)
        if v is None:
            v = default_value
        return v

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

    def __setattr__(self, key, value):
        if isinstance(value, dict):
            value = Config(value, parent=self)
        self.content[key] = value

    def __getattr__(self, key):
        val = self.content.get(key)
        if val == '???':
            raise MissingMandatoryValue(key)
        return self._resolve_single(val) if isinstance(val, str) else val

    def __setitem__(self, key, value):
        if isinstance(value, dict):
            value = Config(value, parent=self)
        self.content[key] = value

    def __getitem__(self, key):
        return self.__getattr__(key)

    def __str__(self):
        return self.content.__str__()

    def __repr__(self):
        return self.content.__repr__()

    # Allow debugger to autocomplete correct fields
    def __dir__(self):
        return self.content.keys()

    def __eq__(self, other):
        return other == self.content

    def __getstate__(self):
        """ allows pickling
        :return:
        """
        return self.__dict__

    def __setstate__(self, d):
        """ allows pickling
        :return:
        """
        self.__dict__.update(d)

    def __delitem__(self, key):
        return self.content.__delitem__(key)

    def __len__(self):
        return len(self.content)

    def __iter__(self):
        return self.content.__iter__()

    def pop(self, key, default=None):
        return self.content.pop(key, default)

    def keys(self):
        return self.content.keys()

    def __contains__(self, item):
        return item in self.content

    def update(self, key, value=None):
        """Updates a dot separated key sequence to a value"""
        split = key.split('.')
        root = self
        for i in range(len(split) - 1):
            k = split[i]
            next_root = root[k]
            # if next_root is a primitive (string, int etc) replace it with an empty map
            if not isinstance(next_root, Config):
                root[k] = {}
                next_root = root[k]
            root = next_root

        last = split[-1]

        assert isinstance(root, Config)
        root[last] = value

    def select(self, key):
        """
        Select a value using dot separated key sequence
        :param key:
        :return:
        """
        split = key.split('.')
        root = self
        for i in range(len(split) - 1):
            k = split[i]
            root = root[k]

        if root is None:
            return None

        last = split[-1]

        if last in root:
            return root[last]
        else:
            return None

    def is_empty(self):
        """return true if config is empty"""
        return self.content == {}

    @staticmethod
    def _to_dict(conf):
        ret = {}
        if isinstance(conf, Config):
            conf = conf.content

        for k, v in conf.items():
            if isinstance(v, Config):
                ret[k] = Config._to_dict(v)
            else:
                ret[k] = v
        return ret

    def to_dict(self):
        return Config._to_dict(self)

    def pretty(self):
        """return a pretty dump of the config content"""
        return yaml.dump(self.to_dict(), default_flow_style=False)

    @staticmethod
    def map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""

        def dict_type(x):
            return isinstance(x, Config) or isinstance(x, dict)

        if isinstance(dest, Config):
            dest = dest.content
        # deep copy:
        ret = OmegaConf.from_dict(dest)
        for key, value in src.items():
            if key in dest and dict_type(dest[key]):
                if dict_type(value):
                    ret[key] = Config.map_merge(dest[key], value)
                else:
                    ret[key] = value
            else:
                ret[key] = src[key]
        return ret

    def merge_from(self, *others):
        """merge a list of other Config objects into this one, overriding as needed"""
        for other in others:
            assert isinstance(other, Config)
            self.set_dict(Config.map_merge(self, other))

        def re_parent(node):
            # update parents of first level Config nodes to self
            for _key, value in node.__dict__['content'].items():
                if isinstance(value, Config):
                    value._set_parent(node)
                    re_parent(value)
        # recursively correct the parent hierarchy after the merge
        re_parent(self)

    def set_dict(self, content):
        if isinstance(content, Config):
            content = content.content
        assert isinstance(content, dict)
        self.__dict__['content'] = {}
        for k, v in content.items():
            if isinstance(v, dict):
                self[k] = Config(v, parent=self)
            else:
                self[k] = v

    @staticmethod
    def resolve_value(root_node, inter_type, inter_key):
        inter_type = 'str:' if inter_type is None else inter_type
        if inter_type == 'str:':
            ret = root_node.select(inter_key)
        elif inter_type == 'env:':
            try:
                ret = os.environ[inter_key]
            except KeyError:
                # validate will raise a KeyError
                ret = None
        else:
            raise ValueError("Unsupported interpolation type {}".format(inter_type[0:-1]))

        if ret is None:
            raise KeyError("{} interpolation key '{}' not found".format(inter_type[0:-1], inter_key))
        if isinstance(ret, Config):
            # Currently this is not supported. interpolated value must be an actual value (str, int etc)
            raise ValueError("String interpolation key '{}' refer a config node".format(inter_key))

        return ret

    def _resolve_single(self, value):
        if value is None:
            return None
        match_list = list(re.finditer(r"\${(\w+:)?([\w\.]+?)}", value))
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


class CLIConfig(Config):
    """Config wrapping CLI arguments"""

    def __init__(self, args_list=None):
        super(CLIConfig, self).__init__(None)
        # if args list is not passed use sys.argv without the program name
        if args_list is None:
            # Skip program name
            args_list = sys.argv[1:]
        for arg in args_list:
            args = arg.split('=')
            key = args[0]
            value = None
            if len(args) > 1:
                # load with yaml to get correct automatic typing with the same rules as yaml parsing
                value = yaml.load(args[1], Loader=get_yaml_loader())
            self.update(key, value)


class EnvConfig(Config):
    """Config wrapping environment variables"""

    def __init__(self, prefix):
        assert isinstance(prefix, str)
        assert prefix != "", "Whitelist must contain at least one item"
        super(EnvConfig, self).__init__(None)
        for key, value in os.environ.items():
            if str.startswith(key, prefix):
                # load with yaml to get correct automatic typing with the same rules as yaml parsing
                key = key[len(prefix):]
                value = yaml.load(value, Loader=get_yaml_loader())
                self.update(key, value)


class OmegaConf:
    """OmegaConf primary class"""

    def __init__(self):
        raise NotImplemented("Use one of the static construction functions")

    @staticmethod
    def empty():
        """Creates an empty config"""
        return OmegaConf.from_string('')

    @staticmethod
    def from_filename(filename):
        """Creates config from the content of the specified filename"""
        assert isinstance(filename, str)
        filename = os.path.abspath(filename)
        with io.open(filename, 'r') as file:
            return OmegaConf.from_file(file)

    @staticmethod
    def from_file(file_):
        """Creates config from the content of the specified file object"""
        if six.PY3:
            assert isinstance(file_, io.IOBase)
        return Config(yaml.load(file_, Loader=get_yaml_loader()))

    @staticmethod
    def from_string(content):
        """Creates config from the content of string"""
        assert isinstance(content, str)
        yamlstr = yaml.load(content, Loader=get_yaml_loader())
        return Config(yamlstr)

    @staticmethod
    def from_dict(dict_):
        """Creates config from the content of string"""
        assert isinstance(dict_, dict)
        return Config(dict_)

    @staticmethod
    def from_cli(args_list=None):
        """Creates config from the content sys.argv or from the specified args list of not None"""
        return CLIConfig(args_list)

    @staticmethod
    def merge(*others):
        """Merge a list of previously created configs into a single one"""
        target = Config({})
        target.merge_from(*others)
        return target
