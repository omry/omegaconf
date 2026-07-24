import copy
import pickle
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union

import attr
from pytest import mark, param, raises

from omegaconf import (
    MISSING,
    DictConfig,
    OmegaConf,
    UnionNode,
    ValidationError,
    open_dict,
)
from omegaconf._utils import is_supported_union_annotation


@dataclass
class Animal:
    name: str = MISSING


@dataclass
class Dog(Animal):
    breed: str = MISSING


@dataclass
class Cat(Animal):
    indoor: bool = MISSING


@dataclass
class GuideDog(Dog):
    trained: bool = True


@dataclass
class Bird(Animal):
    can_fly: bool = True


@dataclass
class PetConfig:
    pet: Union[Dog, Cat] = MISSING


@dataclass
class AnimalOrDogConfig:
    pet: Union[Animal, Dog] = MISSING


@dataclass
class Pep604PetConfig:
    pet: Dog | Cat = MISSING


@dataclass
class PetWithDefaultConfig:
    pet: Union[Dog, Cat] = field(default_factory=lambda: Dog(name="Rex", breed="Lab"))


@dataclass
class DogOrIntConfig:
    pet: Union[Dog, int] = MISSING


@dataclass
class DogOrMappingConfig:
    pet: Union[Dog, Dict[str, Any]] = MISSING


@dataclass
class OptionalPetConfig:
    pet: Optional[Union[Dog, Cat]] = None


@dataclass(frozen=True)
class FrozenDog:
    name: str = MISSING
    breed: str = MISSING


@dataclass
class FrozenDogOrIntConfig:
    pet: Union[FrozenDog, int] = MISSING


@dataclass
class FlexibleDog:
    name: str = "Rex"
    payload: Any = 10
    items: List[Any] = field(default_factory=lambda: [10, "text"])
    metadata: Dict[str, Any] = field(default_factory=lambda: {"count": 1})


@dataclass
class FlexibleDogOrIntConfig:
    pet: Union[FlexibleDog, int] = field(default_factory=FlexibleDog)


@dataclass
class NumericDog:
    age: int = MISSING
    scores: List[int] = field(default_factory=list)


@dataclass
class NumericCat:
    lives: int = 9


@dataclass
class NumericPetConfig:
    pet: Union[NumericDog, NumericCat] = field(
        default_factory=lambda: NumericDog(age=5)
    )


@dataclass
class NumericInterpolationConfig:
    age_text: str = "10"
    pet: Union[NumericDog, NumericCat] = field(
        default_factory=lambda: NumericDog(age="${age_text}")  # type: ignore[arg-type]
    )


def _default_pets() -> List[Union[Dog, Cat]]:
    return [Dog(name="Rex", breed="Lab")]


@dataclass
class PetListConfig:
    pets: List[Union[Dog, Cat]] = field(default_factory=_default_pets)


@dataclass
class PetInterpolationConfig:
    dog: Dog = field(default_factory=lambda: Dog(name="Rex", breed="Lab"))
    pet: Union[Dog, Cat] = "${dog}"  # type: ignore[assignment]


@dataclass
class Left:
    left: int = 1


@dataclass
class Right:
    right: int = 2


@dataclass
class Child(Left, Right):
    child: int = 3


@dataclass
class MultipleInheritanceConfig:
    value: Union[Right, Left] = MISSING


@attr.s(auto_attribs=True)
class AttrDog:
    name: str = MISSING
    breed: str = MISSING


@attr.s(auto_attribs=True)
class AttrCat:
    name: str = MISSING
    indoor: bool = MISSING


@attr.s(auto_attribs=True)
class AttrPetConfig:
    pet: Union[AttrDog, AttrCat] = MISSING


class UnsupportedType:
    pass


@dataclass
class DataclassWithUnsupportedUnion:
    value: Union[int, UnsupportedType] = 10


@attr.s(auto_attribs=True)
class AttrWithUnsupportedUnion:
    value: Union[int, UnsupportedType] = 10


def _selected_ref_type(cfg: DictConfig, key: str = "pet") -> Any:
    node = cfg._get_node(key)
    assert isinstance(node, UnionNode)
    selected = node._value()
    assert isinstance(selected, DictConfig)
    return selected._metadata.ref_type


def test_structured_configs_are_supported_union_members() -> None:
    assert is_supported_union_annotation(Union[Dog, Cat])
    assert is_supported_union_annotation(Union[Dog, int])


@mark.parametrize(
    "schema",
    [DataclassWithUnsupportedUnion, AttrWithUnsupportedUnion],
)
def test_unsupported_union_member_is_rejected(schema: Any) -> None:
    with raises(ValueError, match="Unsupported type annotation in Union"):
        OmegaConf.structured(schema)


def test_missing_default_leaves_branch_unselected() -> None:
    cfg = OmegaConf.structured(PetConfig)

    assert OmegaConf.is_missing(cfg, "pet")


def test_structured_default_selects_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    assert _selected_ref_type(cfg) is Dog
    assert cfg.pet == {"name": "Rex", "breed": "Lab"}


def test_typed_assignment_selects_and_switches_branch() -> None:
    cfg = OmegaConf.structured(PetConfig)

    cfg.pet = Dog(name="Rex", breed="Lab")
    assert _selected_ref_type(cfg) is Dog

    cfg.pet = Cat(name="Mochi", indoor=True)
    assert _selected_ref_type(cfg) is Cat
    assert cfg.pet == {"name": "Mochi", "indoor": True}


def test_typed_dictconfig_selects_branch() -> None:
    cfg = OmegaConf.structured(PetConfig)
    dog = OmegaConf.structured(Dog(name="Rex", breed="Lab"))

    cfg.pet = dog

    assert _selected_ref_type(cfg) is Dog


def test_subclass_selects_most_specific_declared_branch() -> None:
    cfg = OmegaConf.structured(AnimalOrDogConfig)
    cfg.pet = Dog(name="Rex", breed="Lab")

    assert _selected_ref_type(cfg) is Dog


def test_typed_dictconfig_subclass_uses_runtime_mro() -> None:
    cfg = OmegaConf.structured(AnimalOrDogConfig)
    guide_dog = OmegaConf.structured(GuideDog(name="Rex", breed="Lab", trained=True))

    cfg.pet = guide_dog

    assert _selected_ref_type(cfg) is Dog


def test_multiple_inheritance_uses_runtime_mro_not_union_order() -> None:
    cfg = OmegaConf.structured(MultipleInheritanceConfig)
    cfg.value = Child()

    assert _selected_ref_type(cfg, "value") is Left


def test_pep604_structured_union() -> None:
    cfg = OmegaConf.structured(Pep604PetConfig)

    cfg.pet = Cat(name="Mochi", indoor=True)

    assert _selected_ref_type(cfg) is Cat


def test_unrelated_structured_value_is_rejected() -> None:
    cfg = OmegaConf.structured(PetConfig)

    with raises(ValidationError):
        cfg.pet = Bird(name="Robin")


def test_plain_mapping_selects_only_structured_branch() -> None:
    cfg = OmegaConf.structured(DogOrIntConfig)

    cfg.pet = {"name": "Fido"}

    assert _selected_ref_type(cfg) is Dog
    assert cfg.pet["name"] == "Fido"
    assert OmegaConf.is_missing(cfg.pet, "breed")


def test_plain_mapping_without_selected_branch_is_ambiguous() -> None:
    cfg = OmegaConf.structured(PetConfig)

    with raises(ValidationError, match="[Aa]mbig"):
        cfg.pet = {"name": "Fido"}


def test_plain_mapping_considers_typed_dict_branch_ambiguous() -> None:
    cfg = OmegaConf.structured(DogOrMappingConfig)

    with raises(ValidationError, match="[Aa]mbig"):
        cfg.pet = {"name": "Fido"}


def test_explicit_typed_dict_selects_dict_branch() -> None:
    cfg = OmegaConf.structured(DogOrMappingConfig)
    mapping = OmegaConf.typed_dict({"name": "Fido"}, key_type=str, element_type=str)

    cfg.pet = mapping

    node = cfg._get_node("pet")
    assert isinstance(node, UnionNode)
    selected = node._value()
    assert isinstance(selected, DictConfig)
    assert selected._metadata.ref_type == Dict[str, Any]


def test_plain_mapping_assignment_reuses_selected_dict_branch() -> None:
    cfg = OmegaConf.structured(DogOrMappingConfig)
    cfg.pet = OmegaConf.typed_dict({"name": "Fido"}, key_type=str, element_type=str)

    cfg.pet = {"name": "Spot"}

    node = cfg._get_node("pet")
    assert isinstance(node, UnionNode)
    selected = node._value()
    assert isinstance(selected, DictConfig)
    assert selected._metadata.ref_type == Dict[str, Any]
    assert cfg.pet == {"name": "Spot"}


def test_plain_mapping_assignment_replaces_active_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    cfg.pet = {"name": "Fido"}

    assert _selected_ref_type(cfg) is Dog
    assert cfg.pet["name"] == "Fido"
    assert OmegaConf.is_missing(cfg.pet, "breed")


def test_plain_mapping_assignment_supports_frozen_branch() -> None:
    cfg = OmegaConf.structured(FrozenDogOrIntConfig)

    cfg.pet = {"name": "Fido"}

    assert _selected_ref_type(cfg) is FrozenDog
    assert cfg.pet["name"] == "Fido"
    assert OmegaConf.is_missing(cfg.pet, "breed")
    pet = cfg.pet
    assert isinstance(pet, DictConfig)
    assert OmegaConf.is_readonly(pet)


def test_selected_structured_branch_supports_any_fields() -> None:
    cfg = OmegaConf.structured(FlexibleDogOrIntConfig)

    assert cfg.pet.payload == 10
    assert cfg.pet["items"] == [10, "text"]
    assert cfg.pet.metadata == {"count": 1}

    cfg.pet.payload = "updated"
    cfg.pet["items"].append({"nested": True})
    cfg.pet.metadata["labels"] = ["one", "two"]

    assert cfg.pet.payload == "updated"
    assert cfg.pet["items"] == [10, "text", {"nested": True}]
    assert cfg.pet.metadata == {"count": 1, "labels": ["one", "two"]}


def test_selected_structured_branch_supports_open_dict() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    with open_dict(cfg.pet):
        cfg.pet.age = 2

    assert cfg.pet.age == 2


def test_selected_structured_branch_preserves_field_conversion() -> None:
    cfg = OmegaConf.structured(NumericPetConfig)

    cfg.pet.age = "10"
    cfg.pet.scores.append("20")
    assert cfg.pet == {"age": 10, "scores": [20]}

    cfg.pet = {"age": "30", "scores": ["40"]}
    assert cfg.pet == {"age": 30, "scores": [40]}

    merged = OmegaConf.merge(cfg, {"pet": {"age": "50", "scores": ["60"]}})
    assert merged.pet == {"age": 50, "scores": [60]}

    cfg.pet |= {"age": "70"}
    assert cfg.pet == {"age": 70, "scores": [40]}


def test_selected_structured_branch_interpolation_preserves_field_conversion() -> None:
    cfg = OmegaConf.structured(NumericInterpolationConfig)

    assert cfg.pet.age == 10

    OmegaConf.resolve(cfg)

    assert cfg.pet.age == 10


def test_merge_plain_mapping_preserves_active_branch_values() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    merged = OmegaConf.merge(cfg, {"pet": {"name": "Fido"}})

    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Dog
    assert merged.pet == {"name": "Fido", "breed": "Lab"}
    assert cfg.pet == {"name": "Rex", "breed": "Lab"}


def test_mapping_merge_respects_selected_structured_and_typed_dict_branches() -> None:
    cfg = OmegaConf.structured(DogOrMappingConfig)
    cfg.pet = Dog(name="Rex", breed="Lab")

    merged = OmegaConf.merge(cfg, {"pet": {"name": "Fido"}})
    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Dog
    assert merged.pet == {"name": "Fido", "breed": "Lab"}

    typed_mapping = OmegaConf.typed_dict(
        {"name": "Fido"}, key_type=str, element_type=str
    )
    switched = OmegaConf.merge(cfg, {"pet": typed_mapping})
    assert isinstance(switched, DictConfig)
    assert _selected_ref_type(switched) == Dict[str, Any]
    assert switched.pet == {"name": "Fido"}


@mark.parametrize(
    "source",
    [
        param(
            OmegaConf.structured(PetWithDefaultConfig(pet=Dog(name="Fido"))),
            id="structured-owner",
        ),
        param({"pet": Dog(name="Fido")}, id="dataclass"),
        param(
            {"pet": OmegaConf.structured(Dog(name="Fido"))},
            id="structured-dictconfig",
        ),
        param(
            {
                "pet": OmegaConf.typed_dict(
                    {"name": "Fido"}, key_type=str, element_type=str
                )
            },
            id="typed-mapping",
        ),
    ],
)
def test_typed_same_branch_merge_preserves_active_branch_values(
    source: Any,
) -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    merged = OmegaConf.merge(cfg, source)

    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Dog
    assert merged.pet == {"name": "Fido", "breed": "Lab"}
    assert cfg.pet == {"name": "Rex", "breed": "Lab"}


def test_unsafe_merge_preserves_active_same_branch_values() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)
    source = OmegaConf.structured(PetWithDefaultConfig(pet=Dog(name="Fido")))

    merged = OmegaConf.unsafe_merge(cfg, source)

    assert merged is cfg
    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Dog
    assert merged.pet == {"name": "Fido", "breed": "Lab"}


def test_same_branch_merge_supports_frozen_structured_config() -> None:
    cfg = OmegaConf.structured(FrozenDogOrIntConfig)
    cfg.pet = FrozenDog(name="Rex", breed="Lab")
    source = OmegaConf.structured(FrozenDogOrIntConfig)
    source.pet = FrozenDog(name="Fido")

    merged = OmegaConf.merge(cfg, source)

    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is FrozenDog
    assert merged.pet == {"name": "Fido", "breed": "Lab"}
    assert OmegaConf.is_readonly(merged.pet)


def test_subclass_merge_uses_same_declared_mro_branch() -> None:
    cfg = OmegaConf.structured(AnimalOrDogConfig)
    cfg.pet = Dog(name="Rex", breed="Lab")
    source = OmegaConf.structured(AnimalOrDogConfig)
    source.pet = GuideDog(name="Fido", trained=False)

    merged = OmegaConf.merge(cfg, source)

    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Dog
    assert OmegaConf.get_type(merged.pet) is GuideDog
    assert merged.pet == {"name": "Fido", "breed": "Lab", "trained": False}


def test_in_place_or_merges_active_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    cfg.pet |= {"name": "Fido"}

    assert _selected_ref_type(cfg) is Dog
    assert cfg.pet == {"name": "Fido", "breed": "Lab"}


def test_typed_merge_source_can_switch_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)
    other = OmegaConf.structured(
        PetWithDefaultConfig(pet=Cat(name="Mochi", indoor=True))
    )

    merged = OmegaConf.merge(cfg, other)

    assert isinstance(merged, DictConfig)
    assert _selected_ref_type(merged) is Cat
    assert merged.pet == {"name": "Mochi", "indoor": True}


def test_interpolation_selects_structured_branch() -> None:
    cfg = OmegaConf.structured(PetInterpolationConfig)

    assert OmegaConf.get_type(cfg.pet) is Dog

    OmegaConf.resolve(cfg)

    assert _selected_ref_type(cfg) is Dog
    assert cfg.pet == {"name": "Rex", "breed": "Lab"}


def test_optional_structured_union() -> None:
    cfg = OmegaConf.structured(OptionalPetConfig)
    assert cfg.pet is None

    cfg.pet = Dog(name="Rex", breed="Lab")
    assert _selected_ref_type(cfg) is Dog

    cfg.pet = None
    assert cfg.pet is None


def test_structured_union_inside_list() -> None:
    cfg = OmegaConf.structured(PetListConfig)

    cfg.pets.append(Cat(name="Mochi", indoor=True))

    assert OmegaConf.get_type(cfg.pets[0]) is Dog
    assert OmegaConf.get_type(cfg.pets[1]) is Cat


def test_selected_branch_rejects_nonconvertible_field_values() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    with raises(ValidationError):
        cfg.pet.breed = []


def test_attrs_structured_union() -> None:
    cfg = OmegaConf.structured(AttrPetConfig)

    cfg.pet = AttrDog(name="Rex", breed="Lab")

    assert _selected_ref_type(cfg) is AttrDog
    assert cfg.pet == {"name": "Rex", "breed": "Lab"}


def test_to_container_and_to_object() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    assert OmegaConf.to_container(cfg) == {"pet": {"name": "Rex", "breed": "Lab"}}
    obj = OmegaConf.to_object(cfg)
    assert isinstance(obj, PetWithDefaultConfig)
    assert obj == PetWithDefaultConfig(pet=Dog(name="Rex", breed="Lab"))
    assert type(obj.pet) is Dog


def test_deepcopy_preserves_selected_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    copied = copy.deepcopy(cfg)

    assert _selected_ref_type(copied) is Dog
    copied.pet.name = "Fido"
    assert cfg.pet.name == "Rex"


def test_pickle_preserves_selected_branch() -> None:
    cfg = OmegaConf.structured(PetWithDefaultConfig)

    copied = pickle.loads(pickle.dumps(cfg))

    assert _selected_ref_type(copied) is Dog
    assert copied.pet == {"name": "Rex", "breed": "Lab"}
