from .config import Config
from .types import Type, Any


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
            from omegaconf import OmegaConf
            value = OmegaConf.create(value, parent=self)
        if not Config.is_primitive_type(value):
            full_key = self.get_full_key(key)
            raise ValueError("key {}: {} is not a primitive type".format(full_key, type(value).__name__))

        if not isinstance(value, Type):
            value = Any(value)
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
                v = self.map.content[k]
                if isinstance(v, Type):
                    v = v.value()
                kv = (k, v)
                return kv

        return MyItems(self)

    def __eq__(self, other):
        if isinstance(other, dict):
            return Config._dict_eq(self.content, other)
        if isinstance(other, DictConfig):
            return Config._dict_eq(self.content, other.content)
        return NotImplemented

    def __ne__(self, other):
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self):
        # TODO: should actually iterate
        return hash(str(self))
