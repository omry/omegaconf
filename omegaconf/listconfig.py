import copy
import itertools

import six

from .config import Config, isint
from .errors import ReadonlyConfigError
from .nodes import BaseNode, UntypedNode


class ListConfig(Config):
    def __init__(self, content, parent=None):
        super(ListConfig, self).__init__()
        self.__dict__["content"] = []
        self.__dict__["parent"] = parent
        assert isinstance(content, (list, tuple))
        for item in content:
            if isinstance(item, dict) or isinstance(item, (list, tuple)):
                from omegaconf import OmegaConf

                item = OmegaConf.create(item, parent=self)
            self.append(item)

    def __deepcopy__(self, memodict={}):
        res = ListConfig([])
        self._deepcopy_impl(res)
        return res

    def __getattr__(self, key):
        if isinstance(key, str) and isint(key):
            return self.__getitem__(int(key))
        else:
            raise AttributeError()

    # hide content while inspecting in debugger
    def __dir__(self):
        return [str(x) for x in range(0, len(self))]

    def __len__(self):
        return len(self.content)

    def __getitem__(self, index):
        assert isinstance(index, (int, slice))
        if isinstance(index, slice):
            result = []
            for slice_idx in itertools.islice(
                range(0, len(self)), index.start, index.stop, index.step
            ):
                val = self._resolve_with_default(
                    key=slice_idx, value=self.content[slice_idx], default_value=None
                )
                result.append(val)
            return result
        else:
            return self._resolve_with_default(
                key=index, value=self.content[index], default_value=None
            )

    def _set_at_index(self, index, value):

        value = self._prepare_value_to_add(index, value)

        if not isinstance(value, BaseNode):
            self.__dict__["content"][index].set_value(value)
        else:
            if not isinstance(value, BaseNode):
                value = UntypedNode(value)
            else:
                value = copy.deepcopy(value)
            self.__dict__["content"][index] = value

    def __setitem__(self, index, value):
        assert isinstance(index, int)
        self._set_at_index(index, value)

    def append(self, item):
        try:
            self.__dict__["content"].append(UntypedNode(None))
            self._set_at_index(len(self) - 1, item)
        except Exception:
            del self.__dict__["content"][len(self) - 1]
            raise

    def insert(self, index, item):
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(index))
        try:
            self.content.insert(index, UntypedNode(None))
            self._set_at_index(index, item)
        except Exception:
            del self.__dict__["content"][index]
            raise

    def extend(self, lst):
        assert isinstance(lst, (tuple, list, ListConfig))
        for x in lst:
            self.append(x)

    def remove(self, x):
        del self[self.index(x)]

    def clear(self):
        del self[:]

    def index(self, x):
        found_idx = -1
        for idx, item in enumerate(self):
            if x == item:
                found_idx = idx
                break
        if found_idx != -1:
            return found_idx
        else:
            raise ValueError("Item not found in ListConfig")

    def count(self, x):
        c = 0
        for item in self:
            if item == x:
                c = c + 1
        return c

    def copy(self):
        return copy.copy(self)

    if six.PY2:

        def __getslice__(self, start, stop):
            result = []
            for slice_idx in itertools.islice(range(0, len(self)), start, stop, 1):
                val = self._resolve_with_default(
                    key=slice_idx, value=self.content[slice_idx], default_value=None
                )
                result.append(val)
            return ListConfig(content=result, parent=self.__dict__["parent"])

    def get_node(self, index):
        assert type(index) == int
        return self.content[index]

    def get(self, index, default_value=None):
        assert type(index) == int
        return self._resolve_with_default(
            key=index, value=self.content[index], default_value=default_value
        )

    def pop(self, index=-1):
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(index if index != -1 else ""))
        return self._resolve_with_default(
            key=index, value=self.content.pop(index), default_value=None
        )

    def sort(self, key=None, reverse=False):
        if self._get_flag("readonly"):
            raise ReadonlyConfigError()

        if key is None:

            def key1(x):
                return x.value()

        else:

            def key1(x):
                return key(x.value())

        self.content.sort(key=key1, reverse=reverse)

    def __eq__(self, other):
        if isinstance(other, list):
            return Config._list_eq(self, ListConfig(other))
        if isinstance(other, ListConfig):
            return Config._list_eq(self, other)
        return NotImplemented

    def __ne__(self, other):
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self):
        # TODO: should actually iterate
        return hash(str(self))

    def __iter__(self):
        class MyItems(object):
            def __init__(self, l):
                self.lst = l
                self.iterator = iter(l)

            def __iter__(self):
                return self

            # Python 3 compatibility
            def __next__(self):
                return self.next()

            def next(self):
                v = next(self.iterator)
                if isinstance(v, BaseNode):
                    v = v.value()
                return v

        return MyItems(self.content)

    def __add__(self, o):
        # res is sharing this list's parent to allow interpolation to work as expected
        res = ListConfig(parent=self.__dict__["parent"], content=[])
        res.extend(self)
        res.extend(o)
        return res
