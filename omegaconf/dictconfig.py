import copy
from enum import Enum
from typing import (
    AbstractSet,
    Any,
    Dict,
    Iterable,
    Iterator,
    List,
    MutableMapping,
    Optional,
    Tuple,
    Type,
    Union,
)

from ._utils import (
    ValueKind,
    get_structured_config_data,
    get_value_kind,
    is_primitive_dict,
    is_structured_config,
    is_structured_config_frozen,
)
from .base import Container, Node
from .basecontainer import BaseContainer
from .errors import (
    KeyValidationError,
    MissingMandatoryValue,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
    UnsupportedValueType,
    ValidationError,
)
from .nodes import EnumNode, ValueNode


class DictConfig(BaseContainer, MutableMapping[str, Any]):
    def __init__(
        self,
        content: Union[Dict[str, Any], Any],
        parent: Optional[Container] = None,
        key_type: Any = Any,
        element_type: Any = Any,
    ) -> None:
        super().__init__(element_type=element_type, parent=parent)

        self.__dict__["_type"] = None
        self.__dict__["_key_type"] = key_type
        if get_value_kind(content) == ValueKind.MANDATORY_MISSING:
            self.__dict__["_missing"] = True
            self.__dict__["content"] = None
        else:
            self.__dict__["_missing"] = False
            self.__dict__["content"] = {}
            if is_structured_config(content):
                d = get_structured_config_data(content)
                for k, v in d.items():
                    self.__setitem__(k, v)

                if is_structured_config_frozen(content):
                    self._set_flag("readonly", True)

                if isinstance(content, type):
                    self.__dict__["_type"] = content
                else:
                    self.__dict__["_type"] = type(content)

            else:
                for k, v in content.items():
                    self.__setitem__(k, v)

                if isinstance(content, BaseContainer):
                    for field in ["flags", "_element_type", "_resolver_cache"]:
                        self.__dict__[field] = copy.deepcopy(content.__dict__[field])

    def __deepcopy__(self, memo: Dict[int, Any] = {}) -> "DictConfig":
        res = DictConfig({})
        for k in [
            "content",
            "flags",
            "_element_type",
            "_key_type",
            "_type",
            "_missing",
        ]:
            res.__dict__[k] = copy.deepcopy(self.__dict__[k], memo=memo)
        res._re_parent()
        return res

    def __copy__(self) -> "DictConfig":
        res = DictConfig(content={}, element_type=self.__dict__["_element_type"])
        for k in ["content", "flags", "_element_type", "_key_type", "_type"]:
            res.__dict__[k] = copy.copy(self.__dict__[k])
        res._re_parent()
        return res

    def copy(self) -> "DictConfig":
        return copy.copy(self)

    def _validate_and_normalize_key(self, key: Any) -> Union[str, Enum]:
        return self._s_validate_and_normalize_key(self.__dict__["_key_type"], key)

    @staticmethod
    def _s_validate_and_normalize_key(key_type: Any, key: Any) -> Union[str, Enum]:
        if key_type is Any:
            for t in (str, Enum):
                try:
                    return DictConfig._s_validate_and_normalize_key(key_type=t, key=key)
                except KeyValidationError:
                    pass
            raise KeyValidationError(
                f"Key {key} (type {type(key).__name__}) is incompatible with {key_type}"
            )

        if key_type == str:
            if not isinstance(key, str):
                raise KeyValidationError(
                    f"Key {key} is incompatible with {key_type.__name__}"
                )
            return key

        try:
            ret = EnumNode.validate_and_convert_to_enum(key_type, key)
            assert ret is not None
            return ret
        except ValidationError as e:
            raise KeyValidationError(
                f"Key {key} is incompatible with {key_type.__name__} : {e}"
            )

    def __setitem__(self, key: Union[str, Enum], value: Any) -> None:
        try:
            self.__set_impl(key, value)
        except AttributeError as e:
            raise KeyError(str(e))

    def __set_impl(self, key: Union[str, Enum], value: Any) -> None:
        key = self._validate_and_normalize_key(key)
        self._validate_access(key)

        self._validate_type(key, value)

        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))

        if isinstance(value, BaseContainer):
            value._set_parent(self)

        try:
            self._set_item_impl(key, value)
        except UnsupportedValueType:
            raise UnsupportedValueType(
                f"key {self.get_full_key(key)}: {type(value).__name__} is not a supported type"
            )

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        if self._is_missing():
            return []
        return self.__dict__["content"].keys()  # type: ignore

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Allow assigning attributes to DictConfig
        :param key:
        :param value:
        :return:
        """
        self.__set_impl(key, value)

    def __getattr__(self, key: str) -> Any:
        """
        Allow accessing dictionary values as attributes
        :param key:
        :return:
        """
        # PyCharm is sometimes inspecting __members__, be sure to tell it we don't have that.
        if key == "__members__":
            raise AttributeError()

        return self.get(key=key, default_value=None)

    def __getitem__(self, key: Union[str, Enum]) -> Any:
        """
        Allow map style access
        :param key:
        :return:
        """
        try:
            return self.get(key=key, default_value=None)
        except AttributeError as e:
            raise KeyError(str(e))

    def get(self, key: Union[str, Enum], default_value: Any = None) -> Any:
        key = self._validate_and_normalize_key(key)
        return self._resolve_with_default(
            key=key,
            value=self.get_node_ex(key=key, default_value=default_value),
            default_value=default_value,
        )

    def get_node(self, key: Union[str, Enum]) -> Node:
        return self.get_node_ex(key)

    def get_node_ex(
        self,
        key: Union[str, Enum],
        default_value: Any = None,
        validate_access: bool = True,
    ) -> Node:
        value: Node = self.__dict__["content"].get(key)
        if validate_access:
            try:
                self._validate_access(key)
            except (KeyError, AttributeError):
                if default_value is not None:
                    value = default_value
                else:
                    raise
        else:
            if default_value is not None:
                value = default_value
        return value

    __marker = object()

    def pop(self, key: Union[str, Enum], default: Any = __marker) -> Any:
        key = self._validate_and_normalize_key(key)
        if self._get_flag("readonly"):
            raise ReadonlyConfigError(self.get_full_key(key))
        value = self._resolve_with_default(
            key=key, value=self.content.pop(key, default), default_value=default
        )
        if value is self.__marker:
            raise KeyError(key)
        return value

    def keys(self) -> Any:
        if self._is_missing():
            return list()
        return self.content.keys()

    def __contains__(self, key: object) -> bool:
        """
        A key is contained in a DictConfig if there is an associated value and
        it is not a mandatory missing value ('???').
        :param key:
        :return:
        """

        key = self._validate_and_normalize_key(key)
        try:
            node: Optional[Node] = self.get_node(key)
        except (KeyError, AttributeError):
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

    def __iter__(self) -> Iterator[str]:
        return iter(self.keys())

    def items(self) -> AbstractSet[Tuple[str, Any]]:
        return self.items_ex(resolve=True, keys=None)

    def items_ex(
        self, resolve: bool = True, keys: Optional[List[str]] = None
    ) -> AbstractSet[Tuple[str, Any]]:
        # Using a dictionary because the keys are ordered
        items: Dict[Tuple[str, Any], None] = {}
        for key in self.keys():
            if resolve:
                value = self.get(key)
            else:
                value = self.__dict__["content"][key]
                if isinstance(value, ValueNode):
                    value = value.value()
            if keys is None or key in keys:
                items[(key, value)] = None

        return items.keys()

    def __eq__(self, other: Any) -> bool:
        if is_primitive_dict(other):
            return BaseContainer._dict_conf_eq(self, DictConfig(other))
        if isinstance(other, DictConfig):
            return BaseContainer._dict_conf_eq(self, other)
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def _validate_access(self, key: Union[str, Enum]) -> None:
        is_typed = self.__dict__["_type"] is not None
        is_struct = self._get_flag("struct") is True
        if key not in self.content:
            if is_typed:
                # do not raise an exception if struct is explicitly set to False
                if self._get_node_flag("struct") is False:
                    return
                # Or if type is a subclass if dict
                if issubclass(self.__dict__["_type"], dict):
                    return
            if is_typed or is_struct:
                if is_typed:
                    msg = f"Accessing unknown key in {self.__dict__['_type'].__name__} : {self.get_full_key(key)}"
                else:
                    msg = "Accessing unknown key in a struct : {}".format(
                        self.get_full_key(key)
                    )
                raise AttributeError(msg)

    def _validate_type(self, key: Union[str, Enum], value: Any) -> None:
        child = self.get_node(key)
        if child is None:
            return
        self._validate_node_type(child, value)

    def _promote(self, type_or_prototype: Type[Any]) -> None:
        """
        Retypes a node.
        This should only be used in rare circumstances, where you want to dynamically change
        the runtime structured-type of a DictConfig.
        It will change the type and add the additional fields based on the input class or object
        """
        if type_or_prototype is None:
            return
        if not is_structured_config(type_or_prototype):
            raise ValueError("Expected structured config class")

        from omegaconf import OmegaConf

        proto = OmegaConf.structured(type_or_prototype)
        type_ = proto.__dict__["_type"]
        # remove the type to prevent assignment validation from rejecting the promotion.
        proto.__dict__["_type"] = None
        self.merge_with(proto)
        # restore the type.
        self.__dict__["_type"] = type_
