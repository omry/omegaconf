from .config import Config
import copy
from .errors import (
    ReadonlyConfigError,
    MissingMandatoryValue,
    UnsupportedInterpolationType,
)
from .nodes import BaseNode, UntypedNode


class DictConfig(Config):
    def __init__(self, content, parent=None):
        super(DictConfig, self).__init__()
        assert isinstance(content, dict)
        self.__dict__["content"] = {}
        self.__dict__["parent"] = parent
        for k, v in content.items():
            self.__setitem__(k, v)

    def __deepcopy__(self, memodict={}):
        res = DictConfig({})
        self._deepcopy_impl(res)
        return res

    def __copy__(self):
        res = DictConfig({})
        res.__dict__["content"] = copy.copy(self.__dict__["content"])
        res.__dict__["parent"] = self.__dict__["parent"]
        return res

    def copy(self):
        return copy.copy(self)

    def __setitem__(self, key, value):
        assert isinstance(key, str)

        value = self._prepare_value_to_add(key, value)

        if key not in self.content and self._get_flag("struct") is True:
            raise KeyError(
                "Accessing unknown key in a struct : {}".format(self.get_full_key(key))
            )

        input_config_or_node = isinstance(value, (BaseNode, Config))
        if key in self:
            # BaseNode or Config, assign as is
            if input_config_or_node:
                self.__dict__["content"][key] = value
            else:
                # primitive input
                if isinstance(self.__dict__["content"][key], Config):
                    # primitive input replaces config nodes
                    self.__dict__["content"][key] = value
                else:
                    self.__dict__["content"][key].set_value(value)
        else:
            if input_config_or_node:
                self.__dict__["content"][key] = value
            else:
                self.__dict__["content"][key] = UntypedNode(value)

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
        # PyCharm is sometimes inspecting __members__. returning None or throwing is
        # confusing it and it prints an error when inspecting this object.
        if key == "__members__":
            return {}
        return self.get(key=key, default_value=None)

    def __getitem__(self, key):
        """
        Allow map style access
        :param key:
        :return:
        """
        return self.__getattr__(key)

    def get(self, key, default_value=None):
        return self._resolve_with_default(
            key=key,
            value=self.get_node(key, default_value),
            default_value=default_value,
        )

    def get_node(self, key, default_value=None):
        value = self.__dict__["content"].get(key)
        if key not in self.content and self._get_flag("struct"):
            if default_value is not None:
                return default_value
            raise KeyError(
                "Accessing unknown key in a struct : {}".format(self.get_full_key(key))
            )
        return value

    __marker = object()

    def pop(self, key, default=__marker):
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))
        val = self.content.pop(key, default)
        if val is self.__marker:
            raise KeyError(key)
        return val

    def keys(self):
        return self.content.keys()

    def __contains__(self, key):
        """
        A key is contained in a DictConfig if there is an associated value and
        it is not a mandatory missing value ('???').
        :param key:
        :return:
        """
        try:
            node = self.get_node(key)
        except KeyError:
            node = None

        if node is None:
            return False
        else:
            try:
                self._resolve_with_default(key, node, None)
                return True
            except UnsupportedInterpolationType:
                # Value that has unsupported interpolation counts as existing.
                return True
            except (MissingMandatoryValue, KeyError):
                return False

    def __iter__(self):
        return iter(self.keys())

    def items(self, resolve=True, keys=None):
        class MyItems(object):
            def __init__(self, m):
                self.map = m
                self.iterator = iter(m)

            def __iter__(self):
                return self

            def __next__(self):
                k, v = self._next_pair()
                if keys is not None:
                    while True:
                        if k not in keys:
                            k, v = self._next_pair()
                        else:
                            break
                return k, v

            def next(self):
                return self.__next__()

            def _next_pair(self):
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
