"""OmegaConf module"""
import io
import copy
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

    def __init__(self, content):
        if content is None:
            self.__dict__['content'] = {}
        else:
            if isinstance(content, str):
                self.__dict__['content'] = {content: None}
            elif isinstance(content, dict):
                self.__dict__['content'] = content
            else:
                raise TypeError()

    def get(self, key, default_value=None):
        """returns the value with the specified key, like obj.key and obj['key']"""
        v = self.__getattr__(key)
        if v is None:
            v = default_value
        return v

    def __setattr__(self, key, value):
        self.content[key] = value

    # return a ConfigAccess to the result, or the actual result if it's a leaf in content
    def __getattr__(self, key):
        val = self.content.get(key)
        if isinstance(val, dict):
            return Config(val)
        if val == '???':
            raise MissingMandatoryValue(key)
        return val

    def __setitem__(self, key, value):
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

    def update(self, key, value=None):
        """Updates a dot separated key sequence to a value"""
        split = key.split('.')
        root = self
        for i in range(len(split) - 1):
            k = split[i]
            next_root = root.get(k)
            # if next_root is a primitive (string, int etc) replace it with an empty map
            if not isinstance(next_root, Config):
                root[k] = {}
                next_root = root.get(k)
            root = next_root

        last = split[-1]
        root[last] = value

    def is_empty(self):
        """return true if config is empty"""
        return self.content == {}

    def pretty(self):
        """return a pretty dump of the config content"""
        return yaml.dump(self.content, default_flow_style=False)

    @staticmethod
    def map_merge(dest, src):
        """merge src into dest and return a new copy, does not modified input"""
        ret = copy.deepcopy(dest)
        for key, value in src.items():
            if key in dest and isinstance(dest[key], dict):
                if isinstance(value, dict):
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
            self.__dict__['content'] = Config.map_merge(self.content, other.content)


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
    def from_file(file):
        """Creates config from the content of the specified file object"""
        if six.PY3:
            assert isinstance(file, io.IOBase)
        return Config(yaml.load(file, Loader=get_yaml_loader()))

    @staticmethod
    def from_string(content):
        """Creates config from the content of string"""
        assert isinstance(content, str)
        yamlstr = yaml.load(content, Loader=get_yaml_loader())
        return Config(yamlstr)

    @staticmethod
    def from_cli(args_list=None):
        """Creates config from the content sys.argv or from the specified args list of not None"""
        return CLIConfig(args_list)

    @staticmethod
    def from_env(prefix="OC."):
        """Creates config from the content os.environ"""
        return EnvConfig(prefix)

    @staticmethod
    def merge(*others):
        """Merge a list of previously created configs into a single one"""
        target = Config({})
        target.merge_from(*others)
        return target
