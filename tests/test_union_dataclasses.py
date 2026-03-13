import sys
from dataclasses import dataclass, field
from typing import Any, Literal, Optional, Union, cast

import pytest

from omegaconf import MISSING, DictConfig, OmegaConf, ValidationError


@dataclass
class User:
    name: str = MISSING
    age: int = MISSING


@dataclass
class Admin(User):
    permissions: str = "all"


@dataclass
class Guest(User):
    temporary: bool = True


@dataclass
class Config:
    user: Union[Admin, Guest] = field(default_factory=Guest)


def test_union_dataclass_basic() -> None:
    cfg: Any = OmegaConf.structured(Config)
    cfg.user.name = "GuestUser"
    assert cfg.user.name == "GuestUser"
    assert cfg.user.temporary is True

    cfg.user = "Admin"
    user_cfg: Any = cfg.user
    user_cfg.name = "AdminUser"
    assert user_cfg.permissions == "all"
    assert user_cfg.name == "AdminUser"


def test_union_dataclass_merge() -> None:
    cfg: Any = OmegaConf.structured(Config)
    cfg.user = "Guest"
    OmegaConf.set_struct(cfg, False)
    OmegaConf.update(cfg, "user.name", "John")
    user_cfg: Any = cast(Any, cfg.user)
    assert user_cfg.name == "John"

    # Selection switch via update
    OmegaConf.update(cfg, "user", "Admin")
    OmegaConf.update(cfg, "user.name", "Jane")
    assert isinstance(cfg.user, DictConfig)
    user_cfg = cfg.user
    assert user_cfg.permissions == "all"
    assert user_cfg.name == "Jane"


def test_union_dataclass_invalid_selection() -> None:
    cfg: Any = OmegaConf.structured(Config)
    with pytest.raises(ValidationError):
        cfg.user = "Invalid"


def test_union_dataclass_error_reporting() -> None:
    @dataclass
    class ChildA:
        name: str
        age: int

    @dataclass
    class ChildB:
        title: str
        score: float

    @dataclass
    class Parent:
        child: Union[ChildA, ChildB]

    cfg: Any = OmegaConf.structured(Parent)
    with pytest.raises(ValidationError) as excinfo:
        cfg.child = {"name": "test", "age": "invalid_int"}

    msg = str(excinfo.value)
    assert (
        "Value '{'name': 'test', 'age': 'invalid_int'}' of type 'dict' is "
        "incompatible with type hint 'Union[ChildA, ChildB]'"
    ) in msg
    assert "Validation errors of candidate types:" in msg
    assert (
        "- Value 'invalid_int' of type 'str' is incompatible with type hint 'int'"
        in msg
    )
    assert "- Key 'name' not in 'ChildB'" in msg


def test_union_dataclass_merge_uses_type_discriminator() -> None:
    cfg: Any = OmegaConf.structured(Config)
    merged = OmegaConf.merge(
        cfg,
        {
            "user": {
                "_type_": f"{Admin.__module__}.Admin",
                "name": "Bob",
            }
        },
    )
    assert isinstance(merged.user, DictConfig)
    user_cfg: Any = merged.user
    assert user_cfg.permissions == "all"
    assert user_cfg.name == "Bob"
    assert "_type_" not in user_cfg


def test_union_dataclass_merge_unknown_type_discriminator_raises() -> None:
    cfg: Any = OmegaConf.structured(Config)
    with pytest.raises(ValidationError):
        OmegaConf.merge(cfg, {"user": {"_type_": "Unknown", "name": "Bob"}})


def test_union_with_primitive() -> None:
    @dataclass
    class Simple:
        val: Union[int, Admin] = 10

    cfg: Any = OmegaConf.structured(Simple)
    assert cfg.val == 10

    cfg.val = "Admin"
    val_cfg: Any = cfg.val
    assert val_cfg.permissions == "all"

    cfg.val = 20
    assert cfg.val == 20


def test_optional_union_dataclass() -> None:
    @dataclass
    class OptionalConfig:
        user: Optional[Union[Admin, Guest]] = None

    cfg: Any = OmegaConf.structured(OptionalConfig)
    assert cfg.user is None

    cfg.user = "Admin"
    user_cfg: Any = cfg.user
    assert user_cfg.permissions == "all"

    cfg.user = None
    assert cfg.user is None


def test_nested_union_dataclass() -> None:
    @dataclass
    class Sub:
        x: int = 1

    @dataclass
    class Parent:
        child: Union[Sub, int] = field(default_factory=Sub)

    @dataclass
    class Root:
        node: Parent = field(default_factory=Parent)

    cfg: Any = OmegaConf.structured(Root)
    assert cfg.node.child.x == 1

    cfg.node.child = 10
    assert cfg.node.child == 10

    cfg.node.child = "Sub"
    child_cfg: Any = cfg.node.child
    assert child_cfg.x == 1


def test_union_dataclass_from_dict() -> None:
    cfg: Any = OmegaConf.structured(Config)
    # This should work if it matches Admin uniquely (duck typing still works if not selecting via string?)
    cfg.user = {"permissions": "some", "name": "AdminUser"}
    user_cfg: Any = cfg.user
    assert user_cfg.permissions == "some"
    assert user_cfg.name == "AdminUser"


def test_union_dataclass_duck_typing_ambiguity() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        x: int = 2

    @dataclass
    class C:
        val: Union[A, B] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(C)
    assert cfg.val.x == 1

    # Matching x uniquely. If both have x, the first one (A) might be picked by duck typing
    cfg.val = {"x": 10}
    # Current OmegaConf duck typing picks the first candidate that works.
    val_cfg: Any = cfg.val
    assert val_cfg.x == 10

    # Explicit switch
    cfg.val = "B"
    val_cfg = cfg.val
    assert val_cfg.x == 2


def test_hierarchical_union_dataclass() -> None:
    @dataclass
    class InnerA:
        a: int = 1

    @dataclass
    class InnerB:
        b: int = 2

    @dataclass
    class OuterA:
        inner: Union[InnerA, InnerB] = field(default_factory=InnerA)

    @dataclass
    class OuterB:
        val: int = 10

    @dataclass
    class Root:
        outer: Union[OuterA, OuterB] = field(default_factory=OuterA)

    cfg: Any = OmegaConf.structured(Root)
    assert cfg.outer.inner.a == 1

    # Switch inner
    cfg.outer.inner = "InnerB"
    inner_cfg: Any = cfg.outer.inner
    assert inner_cfg.b == 2

    # Switch outer
    cfg.outer = "OuterB"
    outer_cfg: Any = cfg.outer
    assert outer_cfg.val == 10

    # Switch outer back to A
    cfg.outer = "OuterA"
    outer_cfg = cfg.outer
    assert outer_cfg.inner.a == 1


def test_union_with_any() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class ConfigWithAny:
        val: Union[A, Any] = 10

    cfg: Any = OmegaConf.structured(ConfigWithAny)
    assert cfg.val == 10

    cfg.val = "A"
    val_cfg: Any = cfg.val
    assert val_cfg.x == 1

    cfg.val = {"x": 20}
    val_cfg = cfg.val
    assert val_cfg.x == 20

    cfg.val = "hello"
    assert cfg.val == "hello"


def test_union_mandatory_missing() -> None:
    @dataclass
    class A:
        x: int = MISSING

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(Config)
    from omegaconf.errors import MissingMandatoryValue

    with pytest.raises(MissingMandatoryValue):
        _ = cfg.val.x

    cfg.val.x = 10
    assert cfg.val.x == 10


def test_union_readonly() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(Config)
    OmegaConf.set_readonly(cfg, True)

    from omegaconf.errors import ReadonlyConfigError

    with pytest.raises(ReadonlyConfigError):
        cfg.val = "B"

    with pytest.raises(ReadonlyConfigError):
        cfg.val.x = 10


def test_union_interpolation() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = field(default_factory=A)
        target: str = "B"
        proxy: Union[A, B] = cast(Union[A, B], "${val}")

    cfg: Any = OmegaConf.structured(Config)
    assert cfg.proxy.x == 1

    cfg.val = "B"
    proxy_cfg: Any = cfg.proxy
    assert proxy_cfg.y == 2

    # Interpolation to selection string
    cfg.val = "${target}"
    val_cfg: Any = cfg.val
    assert val_cfg.y == 2
    proxy_cfg = cfg.proxy
    assert proxy_cfg.y == 2


def test_union_none_handling() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class Config:
        val: Optional[Union[A, int]] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(Config)
    assert cfg.val.x == 1

    cfg.val = None
    assert cfg.val is None

    cfg.val = 10
    assert cfg.val == 10

    cfg.val = "A"
    val_cfg: Any = cfg.val
    assert val_cfg.x == 1


def test_union_dataclass_complex_merge() -> None:
    @dataclass
    class Inner1:
        v1: int = 1

    @dataclass
    class Inner2:
        v2: int = 2

    @dataclass
    class Middle:
        inner: Union[Inner1, Inner2] = field(default_factory=Inner1)
        m: int = 0

    @dataclass
    class Root:
        middle: Middle = field(default_factory=Middle)

    cfg: Any = OmegaConf.structured(Root)
    assert cfg.middle.inner.v1 == 1

    # Merge a dict that changes middle.m and middle.inner.v1
    cfg.merge_with({"middle": {"m": 10, "inner": {"v1": 100}}})
    assert cfg.middle.m == 10
    assert cfg.middle.inner.v1 == 100

    # Merge a dict that switches middle.inner to Inner2 and sets v2
    # This tests if UnionNode handles nested updates that include a selection string
    cfg.merge_with({"middle": {"inner": "Inner2"}})
    inner_cfg: Any = cfg.middle.inner
    assert inner_cfg.v2 == 2

    # Merge and switch simultaneously
    cfg.merge_with({"middle": {"inner": {"v2": 200}}})  # Duck typing should keep Inner2
    inner_cfg = cfg.middle.inner
    assert inner_cfg.v2 == 200

    # Test merging two structured configs
    over = {"middle": {"inner": "Inner1", "m": 50}}
    cfg.merge_with(over)
    assert cfg.middle.inner.v1 == 1
    assert cfg.middle.m == 50


def test_union_merge_into_missing() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = MISSING

    cfg: Any = OmegaConf.structured(Config)

    # Merging "selection string" into missing
    cfg.merge_with({"val": "A"})
    val_cfg: Any = cfg.val
    assert val_cfg.x == 1

    # Merging dict (duck typing) into missing
    cfg = OmegaConf.structured(Config)
    cfg.merge_with({"val": {"y": 10}})
    val_cfg = cfg.val
    assert val_cfg.y == 10


def test_union_or_operator_syntax() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    if sys.version_info >= (3, 10):
        ns: dict[str, Any] = {"A": A, "B": B, "dataclass": dataclass, "field": field}
        exec(
            """
@dataclass
class Config:
    val: A | B = field(default_factory=A)
""",
            ns,
            ns,
        )
        cfg: Any = OmegaConf.structured(ns["Config"])
        assert cfg.val.x == 1
    else:
        with pytest.raises(TypeError):
            exec("A | B", {"A": A, "B": B})


def test_union_merge_string_selection() -> None:
    @dataclass
    class RSNNConfig:
        foo: int = 1

    @dataclass
    class TCNConfig:
        bar: int = 2

    @dataclass
    class Config:
        backbone: Union[RSNNConfig, TCNConfig] = field(default_factory=RSNNConfig)

    cfg: Any = OmegaConf.structured(Config)

    # Test merging string matching the current type (no-op effectively, but ensures validity)
    cfg.merge_with({"backbone": "RSNNConfig"})
    assert cfg.backbone.foo == 1
    assert isinstance(cfg.backbone, DictConfig)

    # Test switching type via merge with string
    cfg.merge_with({"backbone": "TCNConfig"})
    assert cfg.backbone.bar == 2
    assert "foo" not in cfg.backbone


def test_union_with_str_skip_selection() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class Config:
        val: Union[str, A] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(Config)

    # "A" matches class name A. But str is in Union.
    # So it should NOT be converted to A(). It should be treated as a plain string.
    cfg.val = "A"
    assert cfg.val == "A"


def test_union_dataclass_to_object() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = field(default_factory=A)

    cfg: Any = OmegaConf.structured(Config)

    # Default is A
    obj = OmegaConf.to_object(cfg)
    assert isinstance(obj, Config)
    assert isinstance(obj.val, A)
    assert obj.val.x == 1

    # Switch to B
    cfg.val = "B"
    obj = OmegaConf.to_object(cfg)
    assert isinstance(obj, Config)
    assert isinstance(obj.val, B)
    assert obj.val.y == 2


def test_union_dataclass_from_cli_to_object() -> None:
    @dataclass
    class A:
        x: int = 1

    @dataclass
    class B:
        y: int = 2

    @dataclass
    class Config:
        val: Union[A, B] = field(default_factory=A)

    base = OmegaConf.structured(Config)
    # Simulate CLI arguments to switch to B and set value
    cli_conf = OmegaConf.from_cli(["val._type_=B", "val.y=3"])
    merged = OmegaConf.merge(base, cli_conf)

    obj = OmegaConf.to_object(merged)
    assert isinstance(obj, Config)
    assert isinstance(obj.val, B)
    assert obj.val.y == 3


def test_union_dataclass_deep_nested_to_object() -> None:
    @dataclass
    class LeafA:
        name: str = "A"

    @dataclass
    class LeafB:
        count: int = 0

    @dataclass
    class Level2:
        # List of Unions
        items: list[Union[LeafA, LeafB]] = field(default_factory=list)
        # Dict of Unions
        mapping: dict[str, Union[LeafA, LeafB]] = field(default_factory=dict)

    @dataclass
    class Root:
        lvl2: Level2 = field(default_factory=Level2)

    cfg: Any = OmegaConf.structured(Root)

    # Populate with mixed types
    cfg.lvl2.items = [
        {"_type_": "LeafA", "name": "a1"},
        {"_type_": "LeafB", "count": 1},
    ]
    cfg.lvl2.mapping = {
        "first": {"_type_": "LeafA", "name": "a2"},
        "second": {"_type_": "LeafB", "count": 2},
    }

    obj = OmegaConf.to_object(cfg)

    assert isinstance(obj, Root)
    assert isinstance(obj.lvl2, Level2)

    # Check List
    assert len(obj.lvl2.items) == 2
    assert isinstance(obj.lvl2.items[0], LeafA)
    assert obj.lvl2.items[0].name == "a1"
    assert isinstance(obj.lvl2.items[1], LeafB)
    assert obj.lvl2.items[1].count == 1

    # Check Dict
    assert len(obj.lvl2.mapping) == 2
    assert isinstance(obj.lvl2.mapping["first"], LeafA)
    assert obj.lvl2.mapping["first"].name == "a2"
    assert isinstance(obj.lvl2.mapping["second"], LeafB)
    assert obj.lvl2.mapping["second"].count == 2


def test_union_literals() -> None:
    @dataclass
    class MyConfig:
        strategy: Union[
            Literal["ee_inverse_pool", "ee_ie_inverse_pool"],
            Literal["e_inverse_pool", "e_i_inverse_pool"],
        ] = "ee_inverse_pool"

    cfg = OmegaConf.structured(MyConfig)
    assert cfg.strategy == "ee_inverse_pool"

    cfg.strategy = "e_inverse_pool"
    assert cfg.strategy == "e_inverse_pool"

    with pytest.raises(ValidationError):
        cfg.strategy = "invalid_strategy"
