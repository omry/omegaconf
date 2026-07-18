from dataclasses import dataclass
from typing import Any, Dict, Tuple

from pytest import raises

from omegaconf import MISSING, DictConfig, Node, OmegaConf, TupleConfig, read_write
from omegaconf.errors import ConfigTypeError, InterpolationToMissingValueError


@dataclass
class TupleObject:
    values: Tuple[int, str] = (1, "x")


def test_to_container_preserves_tuple_kind_and_nested_containers() -> None:
    cfg = OmegaConf.create({"values": (1, {"items": (2, 3)})})

    assert OmegaConf.to_container(cfg) == {"values": (1, {"items": (2, 3)})}


def test_to_object_instantiates_native_tuple_field() -> None:
    cfg = OmegaConf.structured(TupleObject)

    obj = OmegaConf.to_object(cfg)
    assert isinstance(obj, TupleObject)
    assert obj == TupleObject(values=(1, "x"))
    assert type(obj.values) is tuple


def test_to_yaml_represents_tuple_as_ordinary_sequence() -> None:
    cfg = OmegaConf.create({"values": (1, 2)})

    assert OmegaConf.to_yaml(cfg) == "values:\n- 1\n- 2\n"
    loaded = OmegaConf.create(OmegaConf.to_yaml(cfg))
    assert loaded == {"values": [1, 2]}


def test_select_traverses_tupleconfig() -> None:
    cfg = OmegaConf.create({"values": ({"name": "first"}, {"name": "second"})})

    assert OmegaConf.select(cfg, "values.1.name") == "second"
    assert OmegaConf.select(cfg["values"], "0.name") == "first"


def test_missing_keys_traverses_tupleconfig() -> None:
    cfg = OmegaConf.typed_tuple([{"value": "???"}], Tuple[Dict[str, str]])

    assert OmegaConf.missing_keys(cfg) == {"[0].value"}


def test_resolve_materializes_container_result_inside_untyped_tuple(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver("returns_dict", lambda: {"value": 10})
    cfg = OmegaConf.create(("${returns_dict:}",))

    assert cfg[0] == {"value": 10}
    OmegaConf.resolve(cfg)

    node = cfg._get_node(0)
    assert isinstance(node, DictConfig)
    assert cfg[0] == {"value": 10}
    assert OmegaConf.to_container(cfg, resolve=False) == ({"value": 10},)


def test_whole_tuple_resolver_is_lazy_then_materialized(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver("returns_tuple", lambda: (1, "x"))
    cfg = OmegaConf.structured(TupleObject(values="${returns_tuple:}"))  # type: ignore[arg-type]
    node = cfg._get_node("values")

    assert isinstance(node, TupleConfig)
    assert node._is_interpolation()
    assert cfg["values"] == (1, "x")
    assert node._is_interpolation()

    OmegaConf.resolve(cfg)
    node = cfg._get_node("values")
    assert isinstance(node, TupleConfig)
    assert not node._is_interpolation()
    assert cfg["values"] == (1, "x")


def test_whole_list_resolver_for_tuple_is_lazy_then_materialized(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver("returns_list", lambda: [1, "x"])
    cfg = OmegaConf.structured(TupleObject(values="${returns_list:}"))  # type: ignore[arg-type]
    node = cfg._get_node("values")

    assert isinstance(node, TupleConfig)
    assert node._is_interpolation()
    assert cfg["values"] == [1, "x"]

    OmegaConf.resolve(cfg)
    node = cfg._get_node("values")
    assert isinstance(node, TupleConfig)
    assert not node._is_interpolation()
    assert cfg["values"] == (1, "x")


def test_resolve_rejects_missing_direct_tuple_element(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver("returns_missing", lambda: MISSING)
    cfg = OmegaConf.typed_tuple(["${returns_missing:}"], Tuple[Any])

    with raises(InterpolationToMissingValueError, match="resolved to a missing"):
        OmegaConf.resolve(cfg)

    node = cfg._get_node(0)
    assert isinstance(node, Node)
    assert node._is_interpolation()


def test_create_existing_interpolated_tuple_preserves_interpolation() -> None:
    source = TupleConfig("${tuple_value:}", ref_type=Tuple[int, str])

    result = OmegaConf.create(source)

    assert isinstance(result, TupleConfig)
    assert result._is_interpolation()
    assert result._value() == "${tuple_value:}"


def test_cached_resolver_preserves_typed_tupleconfig_metadata(
    restore_resolvers: object,
) -> None:
    OmegaConf.register_resolver(
        "cached_tuple",
        lambda: OmegaConf.typed_tuple([], Tuple[int, ...]),
        use_cache=True,
    )
    cfg = OmegaConf.create({"first": "${cached_tuple:}", "second": "${cached_tuple:}"})

    first = cfg.first
    second = cfg.second
    assert isinstance(first, TupleConfig)
    assert isinstance(second, TupleConfig)
    assert first._metadata.ref_type == Tuple[int, ...]
    assert second._metadata.ref_type == Tuple[int, ...]


def test_flag_inheritance_reaches_tuple_children() -> None:
    cfg = OmegaConf.create({"values": ({"value": 1},)})
    values = cfg._get_node("values")
    assert isinstance(values, TupleConfig)
    child = values._get_node(0)
    assert isinstance(child, DictConfig)

    assert child._get_flag("readonly") is None
    OmegaConf.set_readonly(cfg, True)
    assert child._get_flag("readonly") is True


def test_update_rejects_tuple_element_replacement() -> None:
    cfg = OmegaConf.create({"values": (1, 2)})

    with raises(ConfigTypeError, match="immutable"):
        OmegaConf.update(cfg, "values.0", 10)


def test_update_replaces_whole_tuple_through_mutable_parent() -> None:
    cfg = OmegaConf.structured(TupleObject)

    OmegaConf.update(cfg, "values", [2, 3])

    assert cfg["values"] == (2, "3")


def test_update_can_mutate_nested_container_without_replacing_tuple_element() -> None:
    cfg = OmegaConf.create({"values": ({"value": 1},)})

    OmegaConf.update(cfg, "values.0.value", 10)

    assert cfg["values"] == ({"value": 10},)


def test_read_write_does_not_disable_tuple_immutability() -> None:
    cfg = OmegaConf.create((1, 2))
    OmegaConf.set_readonly(cfg, True)

    with read_write(cfg):
        with raises(ConfigTypeError, match="immutable"):
            cfg[0] = 10
