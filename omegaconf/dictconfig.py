from .config import Config
from .nodes import BaseNode, UntypedNode
from .errors import ReadonlyConfigError
import copy


class DictConfig(Config):

    def __init__(self, content, parent=None):
        super(DictConfig, self).__init__()
        assert isinstance(content, dict)
        self.__dict__['content'] = {}
        self.__dict__['parent'] = parent
        for k, v in content.items():
            self.__setitem__(k, v)

    def __deepcopy__(self, memodict={}):
        res = DictConfig({})
        self._deepcopy_impl(res)
        return res

    def __setitem__(self, key, value):
        assert isinstance(key, str)
        if not isinstance(value, Config) and (isinstance(value, dict) or isinstance(value, list)):
            from omegaconf import OmegaConf
            value = OmegaConf.create(value, parent=self)
        if not Config.is_primitive_type(value):
            full_key = self.get_full_key(key)
            raise ValueError("key {}: {} is not a primitive type".format(full_key, type(value).__name__))
        if self._get_flag('freeze'):
            raise ReadonlyConfigError(self.get_full_key(key))
        if key not in self.content and self._get_flag('struct') is True:
            raise KeyError("Accessing unknown key in a struct : {}".format(self.get_full_key(key)))

        input_config_or_node = isinstance(value, (BaseNode, Config))
        if key in self:
            # BaseNode or Config, assign as is
            if input_config_or_node:
                self.__dict__['content'][key] = value
            else:
                # primitive input
                if isinstance(self.__dict__['content'][key], Config):
                    # primitive input replaces config nodes
                    self.__dict__['content'][key] = value
                else:
                    self.__dict__['content'][key].set_value(value)
        else:
            if input_config_or_node:
                self.__dict__['content'][key] = value
            else:
                self.__dict__['content'][key] = UntypedNode(value)

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
        self.__setitem__(key, value)

    def __getattr__(self, key):
        """
        Allow accessing dictionary values as attributes
        :param key:
        :return:
        """
        return self.get(key=key, default_value=None)

    def __getitem__(self, key):
        """
        Allow map style access
        :param key:
        :return:
        """
        return self.__getattr__(key)

    def get(self, key, default_value=None):
        return self._resolve_with_default(key=key, value=self.get_node(key), default_value=default_value)

    def get_node(self, key):
        value = self.__dict__['content'].get(key)
        if key not in self.content and self._get_flag('struct'):
            raise KeyError("Accessing unknown key in a struct : {}".format(self.get_full_key(key)))
        return value

    __marker = object()

    def pop(self, key, default=__marker):
        if self._get_flag('freeze'):
            raise ReadonlyConfigError(self.get_full_key(key))
        val = self.content.pop(key, default)
        if val is self.__marker:
            raise KeyError(key)
        return val

    def keys(self):
        return self.content.keys()

    def __iter__(self):
        return iter(self.keys())

    def items(self, resolve=True):
        class MyItems(object):
            def __init__(self, m):
                self.map = m
                self.iterator = iter(m)

            def __iter__(self):
                return self

            # Python 3 compatibility
            def __next__(self):
                return self.next()

            def next(self):
                k = next(self.iterator)
                if resolve:
                    v = self.map.get(k)
                else:
                    v = self.map.content[k]
                    if isinstance(v, BaseNode):
                        v = v.value()
                kv = (k, v)
                return kv

        return MyItems(self)

    def __eq__(self, other):
        if isinstance(other, dict):
            return Config._dict_conf_eq(self, DictConfig(other))
        if isinstance(other, DictConfig):
            return Config._dict_conf_eq(self, other)
        return NotImplemented

    def __ne__(self, other):
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self):
        # TODO: should actually iterate
        return hash(str(self))
