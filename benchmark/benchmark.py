from typing import Any, Dict

from pytest import fixture

from omegaconf import OmegaConf


def build(
    d: Dict[str, Any], depth: int, width: int, leaf_value: Any = 1
) -> Dict[str, Any]:
    if depth == 0:
        for i in range(width):
            d[f"key_{i}"] = leaf_value
    else:
        for i in range(width):
            c: Dict[str, Any] = {}
            d[f"key_{i}"] = c
            build(c, depth - 1, width, leaf_value)

    return d


@fixture(scope="module")
def large_dict() -> Any:
    return build({}, 11, 2)


@fixture(scope="module")
def small_dict() -> Any:
    return build({}, 5, 2)


@fixture(scope="module")
def dict_with_list_leaf() -> Any:
    return build({}, 5, 2, leaf_value=[1, 2])


@fixture(scope="module")
def small_dict_config(small_dict: Any) -> Any:
    return OmegaConf.create(small_dict)


@fixture(scope="module")
def dict_config_with_list_leaf(dict_with_list_leaf: Any) -> Any:
    return OmegaConf.create(dict_with_list_leaf)


@fixture(scope="module")
def large_dict_config(large_dict: Any) -> Any:
    return OmegaConf.create(large_dict)


def test_create_large_dict(large_dict: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, large_dict)


def test_create_large_dictconfig(large_dict_config: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, large_dict_config)


def test_create_small_dict(small_dict: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, small_dict)


def test_create_small_dictconfig(small_dict_config: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, small_dict_config)


def test_create_dict_with_list_leaves(dict_with_list_leaf: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, dict_with_list_leaf)


def test_create_dict_config_with_list_leaves(
    dict_config_with_list_leaf: Any, benchmark: Any
) -> None:
    benchmark(OmegaConf.create, dict_config_with_list_leaf)
