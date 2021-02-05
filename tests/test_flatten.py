from typing import Any, List, Tuple

from pytest import mark, param

from omegaconf import DictConfig, ListConfig, OmegaConf


def dict_from_flatten(flatlist: List[Tuple[str, Any]]) -> DictConfig:
    return OmegaConf.from_dotlist([f"{k}={v}" for k, v in flatlist])


def flatten(cfg: Any, resolve: bool = False) -> List[Tuple[str, Any]]:
    ret = []

    def handle_dict(key: Any, value: Any, resolve: bool) -> List[Tuple[str, Any]]:
        return [(f"{key}.{k1}", v1) for k1, v1 in flatten(value, resolve=resolve)]

    def handle_list(key: Any, value: Any, resolve: bool) -> List[Tuple[str, Any]]:
        return [(f"{key}.{idx}", v1) for idx, v1 in flatten(value, resolve=resolve)]

    if isinstance(cfg, DictConfig):
        for k, v in cfg.items_ex(resolve=resolve):
            if isinstance(v, DictConfig):
                ret.extend(handle_dict(k, v, resolve=resolve))
            elif isinstance(v, ListConfig):
                ret.extend(handle_list(k, v, resolve=resolve))
            else:
                ret.append((str(k), v))
    elif isinstance(cfg, ListConfig):
        for idx, v in enumerate(cfg._iter_ex(resolve=resolve)):
            if isinstance(v, DictConfig):
                ret.extend(handle_dict(idx, v, resolve=resolve))
            elif isinstance(v, ListConfig):
                ret.extend(handle_list(idx, v, resolve=resolve))
            else:
                ret.append((str(idx), v))
    else:
        assert False

    return ret


@mark.parametrize(
    ("cfg", "expected"),
    [
        # root dict
        param({}, [], id="dict:empty"),
        param(
            {"a": 10, "b": 20},
            [("a", 10), ("b", 20)],
            id="dict:simple",
        ),
        param(
            {"a": 10, "b": {}},
            [("a", 10)],
            id="dict:with_empty_dict",
        ),
        param(
            {
                "a": 10,
                "b": {"c": 20},
            },
            [
                ("a", 10),
                ("b.c", 20),
            ],
            id="dict:with_nested_dict",
        ),
        param(
            {
                "a": 10,
                "b": {
                    "c": 20,
                    "d": {"e": 30},
                },
            },
            [
                ("a", 10),
                ("b.c", 20),
                ("b.d.e", 30),
            ],
            id="dict:with_nested_dict",
        ),
        param(
            {
                "a": 10,
                "b": ["x", "y"],
            },
            [
                ("a", 10),
                ("b.0", "x"),
                ("b.1", "y"),
            ],
            id="dict:with_nested_list",
        ),
        # root list
        param([], [], id="list:empty"),
        param(["a", "b"], [("0", "a"), ("1", "b")], id="list:simple"),
        param(["a", ["b"]], [("0", "a"), ("1.0", "b")], id="list:nested_list"),
        param(["a", {"b": 10}], [("0", "a"), ("1.b", 10)], id="list:nested_dict"),
    ],
)
def test_flatten(cfg: Any, expected: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    flattened = flatten(cfg)
    assert flattened == expected


@mark.parametrize(
    ("cfg", "expected"),
    [
        # root dict
        param({}, [], id="dict:empty"),
        param({"a": 10, "b": 20}, [("a", 10), ("b", 20)], id="dict:simple"),
        param(
            {"a": 10, "b": {"c": 20}},
            [("a", 10), ("b.c", 20)],
            id="dict:with_nested_dict",
        ),
        param(
            {"a": 10, "b": {"c": 20, "d": {"e": 30}}},
            [("a", 10), ("b.c", 20), ("b.d.e", 30)],
            id="dict:with_nested_dict",
        ),
    ],
)
def test_dict_roundtrip(cfg: Any, expected: Any) -> Any:
    cfg = OmegaConf.create(cfg)
    flattened = flatten(cfg)
    assert flattened == expected
    assert dict_from_flatten(flattened) == cfg


@mark.parametrize(
    ("cfg", "flattened_resolved", "flattened"),
    [
        param(
            {"a": "${b}", "b": 20},
            [("a", 20), ("b", 20)],
            [("a", "${b}"), ("b", 20)],
            id="dict",
        ),
    ],
)
def test_flatten_with_interpolation(
    cfg: Any, flattened_resolved: Any, flattened: Any
) -> Any:
    cfg = OmegaConf.create(cfg)
    flattened = flatten(cfg, resolve=True)
    assert flattened == flattened_resolved
    flattened = flatten(cfg, flattened)
    assert flattened == flattened
