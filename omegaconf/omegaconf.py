"""OmegaConf module"""
import copy
import io
import os
import sys
import warnings
from collections import defaultdict
from .config import Config
import yaml


def register_default_resolvers():
    def env(key):
        try:
            return os.environ[key]
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

    # noinspection PyProtectedMember
    @staticmethod
    def register_resolver(name, resolver):
        assert callable(resolver), "resolver must be callable"
        assert name not in Config._resolvers, "resolved {} is already registered".format(name)

        # noinspection PyProtectedMember
        def caching(config, key):
            cache = Config._resolvers_cache[id(config)][name]
            val = cache[key] if key in cache else resolver(key)
            cache[key] = val
            return val

        Config._resolvers[name] = caching

    # noinspection PyProtectedMember
    @staticmethod
    def get_resolver(name):
        return Config._resolvers[name] if name in Config._resolvers else None

    # noinspection PyProtectedMember
    @staticmethod
    def clear_resolvers():
        Config._resolvers = {}
        Config._resolvers_cache = defaultdict(lambda: defaultdict(dict))
        register_default_resolvers()

    @staticmethod
    def set_readonly(conf, value):
        # noinspection PyProtectedMember
        conf._set_flag('freeze', value)

    @staticmethod
    def is_readonly(conf):
        # noinspection PyProtectedMember
        return conf._get_flag('freeze')

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
