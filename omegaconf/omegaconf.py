"""OmegaConf module"""
import copy
import io
import os
import re
import sys
import warnings
from contextlib import contextmanager

import yaml

from .config import Config


def register_default_resolvers():
    def env(key):
        try:
            return yaml.safe_load(os.environ[key])
        except KeyError:
            raise KeyError("Environment variable '{}' not found".format(key))

    OmegaConf.register_resolver('env', env)


class OmegaConf:
    """OmegaConf primary class"""

    def __init__(self):
        raise NotImplementedError("Use one of the static construction functions")

    @staticmethod
    def create(obj=None, parent=None):
        from .dictconfig import DictConfig
        from .listconfig import ListConfig
        from .config import get_yaml_loader

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
    def empty():
        warnings.warn("Use OmegaConf.create() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)
        """Creates an empty config"""
        return OmegaConf.create()

    @staticmethod
    def load(file_):
        from .config import get_yaml_loader
        if isinstance(file_, str):
            with io.open(os.path.abspath(file_), 'r', encoding='utf-8') as f:
                return OmegaConf.create(yaml.load(f, Loader=get_yaml_loader()))
        elif getattr(file_, 'read'):
            return OmegaConf.create(yaml.load(file_, Loader=get_yaml_loader()))
        else:
            raise TypeError("Unexpected file type")

    @staticmethod
    def from_filename(filename):
        warnings.warn("use OmegaConf.load() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)

        """Creates config from the content of the specified filename"""
        assert isinstance(filename, str)
        return OmegaConf.load(filename)

    @staticmethod
    def from_file(file_):
        """Creates config from the content of the specified file object"""
        warnings.warn("use OmegaConf.load() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)
        return OmegaConf.load(file_)

    @staticmethod
    def from_string(content):
        from .config import get_yaml_loader
        warnings.warn("use OmegaConf.create() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)
        """Creates config from the content of string"""
        assert isinstance(content, str)
        yamlstr = yaml.load(content, Loader=get_yaml_loader())
        return OmegaConf.create(yamlstr)

    @staticmethod
    def from_dict(dict_):
        """Creates config from a dictionary"""
        warnings.warn("use OmegaConf.create() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)
        assert isinstance(dict_, dict)
        return OmegaConf.create(dict_)

    @staticmethod
    def from_list(list_):
        """Creates config from a list"""
        warnings.warn("use OmegaConf.create() (since 1.1.5)", DeprecationWarning,
                      stacklevel=2)
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


    @staticmethod
    def _tokenize_args(string):
        if string is None or string == '':
            return []
        def _unescape_word_boundary(match):
            if match.start() == 0 or match.end() == len(match.string):
                return ''
            return match.group(0)
        escaped = re.split(r'(?<!\\),', string)
        escaped = [re.sub(r'(?<!\\) ', _unescape_word_boundary, x) for x in escaped]
        return [re.sub(r'(\\([ ,]))', lambda x: x.group(2), x) for x in escaped]

    @staticmethod
    def register_resolver(name, resolver):
        assert callable(resolver), "resolver must be callable"
        # noinspection PyProtectedMember
        assert name not in Config._resolvers, "resolved {} is already registered".format(name)

        def caching(config, key):
            cache = OmegaConf.get_cache(config)[name]
            val = cache[key] if key in cache else resolver(*OmegaConf._tokenize_args(key))
            cache[key] = val
            return val

        # noinspection PyProtectedMember
        Config._resolvers[name] = caching

    # noinspection PyProtectedMember
    @staticmethod
    def get_resolver(name):
        return Config._resolvers[name] if name in Config._resolvers else None

    # noinspection PyProtectedMember
    @staticmethod
    def clear_resolvers():
        Config._resolvers = {}
        register_default_resolvers()

    @staticmethod
    def get_cache(conf):
        return conf.__dict__['_resolver_cache']

    @staticmethod
    def set_cache(conf, cache):
        conf.__dict__['_resolver_cache'] = copy.deepcopy(cache)

    @staticmethod
    def copy_cache(from_config, to_config):
        OmegaConf.set_cache(to_config, OmegaConf.get_cache(from_config))

    @staticmethod
    def set_readonly(conf, value):
        # noinspection PyProtectedMember
        conf._set_flag('readonly', value)

    @staticmethod
    def is_readonly(conf):
        # noinspection PyProtectedMember
        return conf._get_flag('readonly')

    @staticmethod
    def set_struct(conf, value):
        # noinspection PyProtectedMember
        conf._set_flag('struct', value)

    @staticmethod
    def is_struct(conf):
        # noinspection PyProtectedMember
        return conf._get_flag('struct')


# register all default resolvers
register_default_resolvers()


# noinspection PyProtectedMember
@contextmanager
def flag_override(config, name, value):
    prev_state = config._get_flag(name)
    try:
        config._set_flag(name, value)
        yield config
    finally:
        config._set_flag(name, prev_state)


# noinspection PyProtectedMember
@contextmanager
def read_write(config):
    prev_state = OmegaConf.is_readonly(config)
    try:
        OmegaConf.set_readonly(config, False)
        yield config
    finally:
        OmegaConf.set_readonly(config, prev_state)


@contextmanager
def open_dict(config):
    prev_state = OmegaConf.is_struct(config)
    try:
        OmegaConf.set_struct(config, False)
        yield config
    finally:
        OmegaConf.set_struct(config, prev_state)
