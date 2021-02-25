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
    Sequence,
    Tuple,
    Type,
    Union,
)

from ._utils import (
    ValueKind,
    _get_value,
    _is_interpolation,
    _valid_dict_key_annotation_type,
    format_and_raise,
    get_structured_config_data,
    get_type_of,
    get_value_kind,
    is_container_annotation,
    is_dict,
    is_primitive_dict,
    is_structured_config,
    is_structured_config_frozen,
    type_str,
    valid_value_annotation_type,
)
from .base import Container, ContainerMetadata, DictKeyType, Node
from .basecontainer import DEFAULT_VALUE_MARKER, BaseContainer
from .errors import (
    ConfigAttributeError,
    ConfigKeyError,
    ConfigTypeError,
    InterpolationResolutionError,
    KeyValidationError,
    MissingMandatoryValue,
    OmegaConfBaseException,
    ReadonlyConfigError,
    UnsupportedInterpolationType,
    ValidationError,
)
from .nodes import EnumNode, ValueNode


class DictConfig(BaseContainer, MutableMapping[Any, Any]):

    _metadata: ContainerMetadata
    _content: Union[Dict[DictKeyType, Node], None, str]

    def __init__(
        self,
        content: Union[Dict[DictKeyType, Any], Any],
        key: Any = None,
        parent: Optional[Container] = None,
        ref_type: Union[Any, Type[Any]] = Any,
        key_type: Union[Any, Type[Any]] = Any,
        element_type: Union[Any, Type[Any]] = Any,
        is_optional: bool = True,
        flags: Optional[Dict[str, bool]] = None,
    ) -> None:
        try:
            if isinstance(content, DictConfig):
                if flags is None:
                    flags = content._metadata.flags
            super().__init__(
                parent=parent,
                metadata=ContainerMetadata(
                    key=key,
                    optional=is_optional,
                    ref_type=ref_type,
                    object_type=None,
                    key_type=key_type,
                    element_type=element_type,
                    flags=flags,
                ),
            )
            if not valid_value_annotation_type(
                element_type
            ) and not is_structured_config(element_type):
                raise ValidationError(f"Unsupported value type : {element_type}")

            if not _valid_dict_key_annotation_type(key_type):
                raise KeyValidationError(f"Unsupported key type {key_type}")

            if is_structured_config(content) or is_structured_config(ref_type):
                self._set_value(content, flags=flags)
                if is_structured_config_frozen(content) or is_structured_config_frozen(
                    ref_type
                ):
                    self._set_flag("readonly", True)

            else:
                if isinstance(content, DictConfig):
                    metadata = copy.deepcopy(content._metadata)
                    metadata.key = key
                    metadata.optional = is_optional
                    metadata.element_type = element_type
                    metadata.key_type = key_type
                    self.__dict__["_metadata"] = metadata
                self._set_value(content, flags=flags)
        except Exception as ex:
            format_and_raise(node=None, key=None, value=None, cause=ex, msg=str(ex))

    def __deepcopy__(self, memo: Dict[int, Any]) -> "DictConfig":
        res = DictConfig(None)
        res.__dict__["_metadata"] = copy.deepcopy(self.__dict__["_metadata"], memo=memo)
        res.__dict__["_flags_cache"] = copy.deepcopy(
            self.__dict__["_flags_cache"], memo=memo
        )

        src_content = self.__dict__["_content"]
        if isinstance(src_content, dict):
            content_copy = {}
            for k, v in src_content.items():
                old_parent = v.__dict__["_parent"]
                try:
                    v.__dict__["_parent"] = None
                    vc = copy.deepcopy(v, memo=memo)
                    vc.__dict__["_parent"] = res
                    content_copy[k] = vc
                finally:
                    v.__dict__["_parent"] = old_parent
        else:
            # None and strings can be assigned as is
            content_copy = src_content

        res.__dict__["_content"] = content_copy
        # parent is retained, but not copied
        res.__dict__["_parent"] = self.__dict__["_parent"]
        return res

    def copy(self) -> "DictConfig":
        return copy.copy(self)

    def _is_typed(self) -> bool:
        return self._metadata.object_type not in (Any, None) and not is_dict(
            self._metadata.object_type
        )

    def _validate_get(self, key: Any, value: Any = None) -> None:
        is_typed = self._is_typed()

        is_struct = self._get_flag("struct") is True
        if key not in self.__dict__["_content"]:
            if is_typed:
                # do not raise an exception if struct is explicitly set to False
                if self._get_node_flag("struct") is False:
                    return
            if is_typed or is_struct:
                if is_typed:
                    assert self._metadata.object_type is not None
                    msg = f"Key '{key}' not in '{self._metadata.object_type.__name__}'"
                else:
                    msg = f"Key '{key}' is not in struct"
                self._format_and_raise(
                    key=key, value=value, cause=ConfigAttributeError(msg)
                )

    def _validate_set(self, key: Any, value: Any) -> None:
        from omegaconf import OmegaConf

        vk = get_value_kind(value)
        if vk == ValueKind.INTERPOLATION:
            return
        self._validate_non_optional(key, value)
        if (isinstance(value, str) and value == "???") or value is None:
            return

        target = self._get_node(key) if key is not None else self

        target_has_ref_type = isinstance(
            target, DictConfig
        ) and target._metadata.ref_type not in (Any, dict)
        is_valid_target = target is None or not target_has_ref_type

        if is_valid_target:
            return

        assert isinstance(target, Node)

        target_type = target._metadata.ref_type
        value_type = OmegaConf.get_type(value)

        if is_dict(value_type) and is_dict(target_type):
            return
        if is_container_annotation(target_type) and not is_container_annotation(
            value_type
        ):
            raise ValidationError(
                f"Cannot assign {type_str(value_type)} to {type_str(target_type)}"
            )
        validation_error = (
            target_type is not None
            and value_type is not None
            and not issubclass(value_type, target_type)
        )
        if validation_error:
            self._raise_invalid_value(value, value_type, target_type)

    def _validate_merge(self, value: Any) -> None:
        from omegaconf import OmegaConf

        dest = self
        src = value

        self._validate_non_optional(None, src)

        dest_obj_type = OmegaConf.get_type(dest)
        src_obj_type = OmegaConf.get_type(src)

        if dest._is_missing() and src._metadata.object_type is not None:
            self._validate_set(key=None, value=_get_value(src))

        if src._is_missing():
            return

        validation_error = (
            dest_obj_type is not None
            and src_obj_type is not None
            and is_structured_config(dest_obj_type)
            and not OmegaConf.is_none(src)
            and not is_dict(src_obj_type)
            and not issubclass(src_obj_type, dest_obj_type)
        )
        if validation_error:
            msg = (
                f"Merge error : {type_str(src_obj_type)} is not a "
                f"subclass of {type_str(dest_obj_type)}. value: {src}"
            )
            raise ValidationError(msg)

    def _validate_non_optional(self, key: Any, value: Any) -> None:
        from omegaconf import OmegaConf

        if OmegaConf.is_none(value):
            if key is not None:
                child = self._get_node(key)
                if child is not None:
                    assert isinstance(child, Node)
                    if not child._is_optional():
                        self._format_and_raise(
                            key=key,
                            value=value,
                            cause=ValidationError("child '$FULL_KEY' is not Optional"),
                        )
            else:
                if not self._is_optional():
                    self._format_and_raise(
                        key=None,
                        value=value,
                        cause=ValidationError("field '$FULL_KEY' is not Optional"),
                    )

    def _raise_invalid_value(
        self, value: Any, value_type: Any, target_type: Any
    ) -> None:
        assert value_type is not None
        assert target_type is not None
        msg = (
            f"Invalid type assigned : {type_str(value_type)} is not a "
            f"subclass of {type_str(target_type)}. value: {value}"
        )
        raise ValidationError(msg)

    def _validate_and_normalize_key(self, key: Any) -> DictKeyType:
        return self._s_validate_and_normalize_key(self._metadata.key_type, key)

    def _s_validate_and_normalize_key(self, key_type: Any, key: Any) -> DictKeyType:
        if key_type is Any:
            for t in DictKeyType.__args__:  # type: ignore
                if isinstance(key, t):
                    return key  # type: ignore
            raise KeyValidationError("Incompatible key type '$KEY_TYPE'")
        elif key_type is bool and key in [0, 1]:
            # Python treats True as 1 and False as 0 when used as dict keys
            #   assert hash(0) == hash(False)
            #   assert hash(1) == hash(True)
            return bool(key)
        elif key_type in (str, int, float, bool):  # primitive type
            if not isinstance(key, key_type):
                raise KeyValidationError(
                    f"Key $KEY ($KEY_TYPE) is incompatible with ({key_type.__name__})"
                )

            return key  # type: ignore
        elif issubclass(key_type, Enum):
            try:
                ret = EnumNode.validate_and_convert_to_enum(
                    key_type, key, allow_none=False
                )
                assert ret is not None
                return ret
            except ValidationError:
                valid = ", ".join([x for x in key_type.__members__.keys()])
                raise KeyValidationError(
                    f"Key '$KEY' is incompatible with the enum type '{key_type.__name__}', valid: [{valid}]"
                )
        else:
            assert False, f"Unsupported key type {key_type}"

    def __setitem__(self, key: DictKeyType, value: Any) -> None:
        try:
            self.__set_impl(key=key, value=value)
        except AttributeError as e:
            self._format_and_raise(
                key=key, value=value, type_override=ConfigKeyError, cause=e
            )
        except Exception as e:
            self._format_and_raise(key=key, value=value, cause=e)

    def __set_impl(self, key: DictKeyType, value: Any) -> None:
        key = self._validate_and_normalize_key(key)
        self._set_item_impl(key, value)

    # hide content while inspecting in debugger
    def __dir__(self) -> Iterable[str]:
        if self._is_missing() or self._is_none():
            return []
        return self.__dict__["_content"].keys()  # type: ignore

    def __setattr__(self, key: str, value: Any) -> None:
        """
        Allow assigning attributes to DictConfig
        :param key:
        :param value:
        :return:
        """
        try:
            self.__set_impl(key, value)
        except Exception as e:
            if isinstance(e, OmegaConfBaseException) and e._initialized:
                raise e
            self._format_and_raise(key=key, value=value, cause=e)
            assert False

    def __getattr__(self, key: str) -> Any:
        """
        Allow accessing dictionary values as attributes
        :param key:
        :return:
        """
        if key == "__name__":
            raise AttributeError()

        try:
            return self._get_impl(key=key, default_value=DEFAULT_VALUE_MARKER)
        except ConfigKeyError as e:
            self._format_and_raise(
                key=key, value=None, cause=e, type_override=ConfigAttributeError
            )
        except Exception as e:
            self._format_and_raise(key=key, value=None, cause=e)

    def __getitem__(self, key: DictKeyType) -> Any:
        """
        Allow map style access
        :param key:
        :return:
        """

        try:
            return self._get_impl(key=key, default_value=DEFAULT_VALUE_MARKER)
        except AttributeError as e:
            self._format_and_raise(
                key=key, value=None, cause=e, type_override=ConfigKeyError
            )
        except Exception as e:
            self._format_and_raise(key=key, value=None, cause=e)

    def __delitem__(self, key: DictKeyType) -> None:
        key = self._validate_and_normalize_key(key)
        if self._get_flag("readonly"):
            self._format_and_raise(
                key=key,
                value=None,
                cause=ReadonlyConfigError(
                    "DictConfig in read-only mode does not support deletion"
                ),
            )
        if self._get_flag("struct"):
            self._format_and_raise(
                key=key,
                value=None,
                cause=ConfigTypeError(
                    "DictConfig in struct mode does not support deletion"
                ),
            )
        if self._is_typed() and self._get_node_flag("struct") is not False:
            self._format_and_raise(
                key=key,
                value=None,
                cause=ConfigTypeError(
                    f"{type_str(self._metadata.object_type)} (DictConfig) does not support deletion"
                ),
            )

        try:
            del self.__dict__["_content"][key]
        except KeyError:
            msg = "Key not found: '$KEY'"
            self._format_and_raise(key=key, value=None, cause=ConfigKeyError(msg))

    def get(self, key: DictKeyType, default_value: Any = None) -> Any:
        """Return the value for `key` if `key` is in the dictionary, else
        `default_value` (defaulting to `None`)."""
        try:
            return self._get_impl(key=key, default_value=default_value)
        except KeyValidationError as e:
            self._format_and_raise(key=key, value=None, cause=e)

    def _get_impl(self, key: DictKeyType, default_value: Any) -> Any:
        try:
            node = self._get_node(key=key, throw_on_missing_key=True)
        except (ConfigAttributeError, ConfigKeyError):
            if default_value is not DEFAULT_VALUE_MARKER:
                node = default_value
            else:
                raise
        return self._resolve_with_default(
            key=key, value=node, default_value=default_value
        )

    def _get_node(
        self,
        key: DictKeyType,
        validate_access: bool = True,
        throw_on_missing_value: bool = False,
        throw_on_missing_key: bool = False,
    ) -> Union[Optional[Node], List[Optional[Node]]]:
        try:
            key = self._validate_and_normalize_key(key)
        except KeyValidationError:
            if validate_access:
                raise
            else:
                return None

        if validate_access:
            self._validate_get(key)

        value: Optional[Node] = self.__dict__["_content"].get(key)
        if value is None:
            if throw_on_missing_key:
                raise ConfigKeyError(f"Missing key {key}")
        elif throw_on_missing_value and value._is_missing():
            raise MissingMandatoryValue("Missing mandatory value")
        return value

    def pop(self, key: DictKeyType, default: Any = DEFAULT_VALUE_MARKER) -> Any:
        try:
            if self._get_flag("readonly"):
                raise ReadonlyConfigError("Cannot pop from read-only node")
            if self._get_flag("struct"):
                raise ConfigTypeError("DictConfig in struct mode does not support pop")
            if self._is_typed() and self._get_node_flag("struct") is not False:
                raise ConfigTypeError(
                    f"{type_str(self._metadata.object_type)} (DictConfig) does not support pop"
                )
            key = self._validate_and_normalize_key(key)
            node = self._get_node(key=key, validate_access=False)
            if node is not None:
                value = self._resolve_with_default(
                    key=key, value=node, default_value=default
                )

                del self[key]
                return value
            else:
                if default is not DEFAULT_VALUE_MARKER:
                    return default
                else:
                    full = self._get_full_key(key=key)
                    if full != key:
                        raise ConfigKeyError(f"Key not found: '{key}' (path: '{full}')")
                    else:
                        raise ConfigKeyError(f"Key not found: '{key}'")
        except Exception as e:
            self._format_and_raise(key=key, value=None, cause=e)

    def keys(self) -> Any:
        if self._is_missing() or self._is_interpolation() or self._is_none():
            return list()
        return self.__dict__["_content"].keys()

    def __contains__(self, key: object) -> bool:
        """
        A key is contained in a DictConfig if there is an associated value and
        it is not a mandatory missing value ('???').
        :param key:
        :return:
        """

        try:
            key = self._validate_and_normalize_key(key)
        except KeyValidationError:
            return False

        try:
            node = self._get_node(key)
            assert node is None or isinstance(node, Node)
        except (KeyError, AttributeError):
            node = None

        if node is None:
            return False
        else:
            try:
                self._resolve_with_default(key=key, value=node)
                return True
            except UnsupportedInterpolationType:
                # Value that has unsupported interpolation counts as existing.
                return True
            except (MissingMandatoryValue, KeyError, InterpolationResolutionError):
                return False

    def __iter__(self) -> Iterator[DictKeyType]:
        return iter(self.keys())

    def items(self) -> AbstractSet[Tuple[DictKeyType, Any]]:
        return self.items_ex(resolve=True, keys=None)

    def setdefault(self, key: DictKeyType, default: Any = None) -> Any:
        if key in self:
            ret = self.__getitem__(key)
        else:
            ret = default
            self.__setitem__(key, default)
        return ret

    def items_ex(
        self, resolve: bool = True, keys: Optional[Sequence[DictKeyType]] = None
    ) -> AbstractSet[Tuple[DictKeyType, Any]]:
        items: List[Tuple[DictKeyType, Any]] = []
        for key in self.keys():
            if resolve:
                value = self.get(key)
            else:
                value = self.__dict__["_content"][key]
                if isinstance(value, ValueNode):
                    value = value._value()
            if keys is None or key in keys:
                items.append((key, value))

        # For some reason items wants to return a Set, but if the values are not
        # hashable this is a problem. We use a list instead. most use cases should just
        # be iterating on pairs anyway.
        return items  # type: ignore

    def __eq__(self, other: Any) -> bool:
        if other is None:
            return self.__dict__["_content"] is None
        if is_primitive_dict(other) or is_structured_config(other):
            other = DictConfig(other, flags={"allow_objects": True})
            return DictConfig._dict_conf_eq(self, other)
        if isinstance(other, DictConfig):
            return DictConfig._dict_conf_eq(self, other)
        return NotImplemented

    def __ne__(self, other: Any) -> bool:
        x = self.__eq__(other)
        if x is not NotImplemented:
            return not x
        return NotImplemented

    def __hash__(self) -> int:
        return hash(str(self))

    def _promote(self, type_or_prototype: Optional[Type[Any]]) -> None:
        """
        Retypes a node.
        This should only be used in rare circumstances, where you want to dynamically change
        the runtime structured-type of a DictConfig.
        It will change the type and add the additional fields based on the input class or object
        """
        if type_or_prototype is None:
            return
        if not is_structured_config(type_or_prototype):
            raise ValueError(f"Expected structured config class : {type_or_prototype}")

        from omegaconf import OmegaConf

        proto: DictConfig = OmegaConf.structured(type_or_prototype)
        object_type = proto._metadata.object_type
        # remove the type to prevent assignment validation from rejecting the promotion.
        proto._metadata.object_type = None
        self.merge_with(proto)
        # restore the type.
        self._metadata.object_type = object_type

    def _set_value(self, value: Any, flags: Optional[Dict[str, bool]] = None) -> None:
        try:
            previous_content = self.__dict__["_content"]
            self._set_value_impl(value, flags)
        except Exception as e:
            self.__dict__["_content"] = previous_content
            raise e

    def _set_value_impl(
        self, value: Any, flags: Optional[Dict[str, bool]] = None
    ) -> None:
        from omegaconf import OmegaConf, flag_override

        if flags is None:
            flags = {}

        assert not isinstance(value, ValueNode)
        self._validate_set(key=None, value=value)

        if OmegaConf.is_none(value):
            self.__dict__["_content"] = None
            self._metadata.object_type = None
        elif _is_interpolation(value, strict_interpolation_validation=True):
            self.__dict__["_content"] = value
            self._metadata.object_type = None
        elif value == "???":
            self.__dict__["_content"] = "???"
            self._metadata.object_type = None
        else:
            self.__dict__["_content"] = {}
            if is_structured_config(value):
                self._metadata.object_type = None
                data = get_structured_config_data(
                    value,
                    allow_objects=self._get_flag("allow_objects"),
                )
                for k, v in data.items():
                    self.__setitem__(k, v)
                self._metadata.object_type = get_type_of(value)
            elif isinstance(value, DictConfig):
                self.__dict__["_metadata"] = copy.deepcopy(value._metadata)
                self._metadata.flags = copy.deepcopy(flags)
                # disable struct and readonly for the construction phase
                # retaining other flags like allow_objects. The real flags are restored at the end of this function
                with flag_override(self, "struct", False):
                    with flag_override(self, "readonly", False):
                        for k, v in value.__dict__["_content"].items():
                            self.__setitem__(k, v)

            elif isinstance(value, dict):
                for k, v in value.items():
                    self.__setitem__(k, v)
            else:  # pragma: no cover
                msg = f"Unsupported value type : {value}"
                raise ValidationError(msg)

    @staticmethod
    def _dict_conf_eq(d1: "DictConfig", d2: "DictConfig") -> bool:

        d1_none = d1.__dict__["_content"] is None
        d2_none = d2.__dict__["_content"] is None
        if d1_none and d2_none:
            return True
        if d1_none != d2_none:
            return False

        assert isinstance(d1, DictConfig)
        assert isinstance(d2, DictConfig)
        if len(d1) != len(d2):
            return False
        for k, v in d1.items_ex(resolve=False):
            if k not in d2.__dict__["_content"]:
                return False
            if not BaseContainer._item_eq(d1, k, d2, k):
                return False

        return True
