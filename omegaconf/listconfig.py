import itertools

import six

from .config import Config, isint


class ListConfig(Config):
    def __init__(self, content, parent=None):
        assert isinstance(content, (list, tuple))
        self.__dict__['content'] = []
        self.__dict__['parent'] = parent
        for item in content:
            if isinstance(item, dict) or isinstance(item, (list, tuple)):
                from omegaconf import OmegaConf
                item = OmegaConf.create(item, parent=self)
            self.append(item)

    def __getattr__(self, obj):
        if isinstance(obj, str) and isint(obj):
            return self.__getitem__(int(obj))
        else:
            raise AttributeError()

    def __iter__(self):
        return iter(self.content)

    # hide content while inspecting in debugger
    def __dir__(self):
        return [str(x) for x in range(0, len(self))]

    def __len__(self):
        return len(self.content)

    def __getitem__(self, index):
        assert isinstance(index, (int, slice))
        if isinstance(index, slice):
            result = []
            for slice_idx in itertools.islice(range(0, len(self)), index.start, index.stop, index.step):
                val = self._resolve_with_default(key=slice_idx, value=self.content[slice_idx], default_value=None)
                result.append(val)
            return result
        else:
            return self._resolve_with_default(key=index, value=self.content[index], default_value=None)

    def __setitem__(self, index, value):
        assert isinstance(index, int)
        if not isinstance(value, Config) and (isinstance(value, dict) or isinstance(value, list)):
            from omegaconf import OmegaConf
            value = OmegaConf.create(value, parent=self)
        self.validate(index, value)
        self.__dict__['content'][index] = value

    def __delitem__(self, key):
        self.content.__delitem__(key)

    if six.PY2:
        def __getslice__(self, start, stop):
            result = []
            for slice_idx in itertools.islice(range(0, len(self)), start, stop, 1):
                val = self._resolve_with_default(key=slice_idx, value=self.content[slice_idx], default_value=None)
                result.append(val)
            return ListConfig(content=result, parent=self.__dict__['parent'])

    def get(self, index, default_value=None):
        assert type(index) == int
        return self._resolve_with_default(key=index, value=self.content[index], default_value=default_value)

    def sort(self, key=None, reverse=False):
        self.content.sort(key, reverse)

    def pop(self, index=-1):
        return self._resolve_with_default(key=index, value=self.content.pop(index), default_value=None)

    def append(self, item):
        if not isinstance(item, Config) and (isinstance(item, dict) or isinstance(item, list)):
            from omegaconf import OmegaConf
            item = OmegaConf.create(item, parent=self)
        self.validate(len(self), item)
        self.__dict__['content'].append(item)

    def insert(self, index, item):
        self.validate(index, item)
        self.content.insert(index, item)

    def sort(self, key=None, reverse=False):
        self.content.sort(key=key, reverse=reverse)
