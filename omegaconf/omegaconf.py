import io
import yaml
import copy
import sys
import os


class MissingMandatoryValue(Exception):
    def __init__(self, message):
        super().__init__(message)


class Config:

    def __init__(self, content):
        if content is None:
            self.__dict__['content'] = {}
        else:
            if isinstance(content, str):
                self.__dict__['content'] = {content: None}
            else:
                self.__dict__['content'] = content

    def get(self, key):
        return self.__getattr__(key)

    def __setattr__(self, key, value):
        self.content[key] = value

    # return a ConfigAccess to the result, or the actual result if it's a leaf in content
    def __getattr__(self, key):
        x = self.content.get(key)
        if type(x) == dict:
            return Config(x)
        else:
            if x == '???':
                raise MissingMandatoryValue(key)
            return x

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

    def update_key(self, key, value=None):
        self.__setattr__(key, value)

    def update(self, key, value=None):
        split = key.split('.')

        root = self
        for i in range(len(split) - 1):
            k = split[i]
            next_root = root.get(k)
            # if next_root is a primitive (string, int etc) replace it with an empty map
            if not isinstance(next_root, Config):
                root.update_key(k, {})
                next_root = root.get(k)
            root = next_root

        last = split[-1]
        root.update_key(last, value)

    def is_empty(self):
        return self.content == {}

    def pretty(self):
        return yaml.dump(self.content, default_flow_style=False)

    @staticmethod
    def map_merge(dest, src):
        ret = copy.deepcopy(dest)
        for k, v in src.items():
            if k in dest and isinstance(dest[k], dict):
                ret[k] = Config.map_merge(dest[k], src[k])
            else:
                ret[k] = src[k]
        return ret

    def merge_from(self, *others):
        for other in others:
            assert isinstance(other, Config)
            self.__dict__['content'] = Config.map_merge(self.content, other.content)


class CLIConfig(Config):
    def __init__(self):
        super().__init__(None)
        for i, arg in enumerate(sys.argv):
            # Skip program name
            if i == 0:
                continue
            a2 = arg.split('=')
            key = a2[0]
            value = None
            if len(a2) > 1:
                # load with yaml to get correct automatic typing with the same rules as yaml parsing
                value = yaml.load(a2[1])
            self.update(key, value)


class EnvConfig(Config):
    def __init__(self, lowercase_keys=True):
        super().__init__(None)
        for key, value in os.environ.items():
            # load with yaml to get correct automatic typing with the same rules as yaml parsing
            value = yaml.load(value)
            if lowercase_keys:
                key = key.lower()
            self.update(key, value)


class OmegaConf(Config):
    @staticmethod
    def empty():
        return OmegaConf.from_string('')

    @staticmethod
    def from_filename(filename: str):
        return OmegaConf.from_file(io.open(filename, 'r'))

    @staticmethod
    def from_file(file: io.TextIOBase):
        return Config(yaml.load(file))

    @staticmethod
    def from_string(content: str):
        s = yaml.load(content)
        return Config(s)

    @staticmethod
    def from_cli():
        return CLIConfig()

    @staticmethod
    def from_env():
        return EnvConfig()

    @staticmethod
    def merge(*others):
        target = Config({})
        target.merge_from(*others)
        return target
