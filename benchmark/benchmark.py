from typing import Any, Dict, List

from pytest import lazy_fixture  # type: ignore
from pytest import fixture, mark, param

from omegaconf import OmegaConf
from omegaconf._utils import ValueKind, _is_missing_literal, get_value_kind


def build_dict(
    d: Dict[str, Any], depth: int, width: int, leaf_value: Any = 1
) -> Dict[str, Any]:
    if depth == 0:
        for i in range(width):
            d[f"key_{i}"] = leaf_value
    else:
        for i in range(width):
            c: Dict[str, Any] = {}
            d[f"key_{i}"] = c
            build_dict(c, depth - 1, width, leaf_value)

    return d


def build_list(length: int, val: Any = 1) -> List[int]:
    return [val] * length


@fixture(scope="module")
def large_dict() -> Any:
    return build_dict({}, 11, 2)


@fixture(scope="module")
def small_dict() -> Any:
    return build_dict({}, 5, 2)


@fixture(scope="module")
def dict_with_list_leaf() -> Any:
    return build_dict({}, 5, 2, leaf_value=[1, 2])


@fixture(scope="module")
def small_dict_config(small_dict: Any) -> Any:
    return OmegaConf.create(small_dict)


@fixture(scope="module")
def dict_config_with_list_leaf(dict_with_list_leaf: Any) -> Any:
    return OmegaConf.create(dict_with_list_leaf)


@fixture(scope="module")
def large_dict_config(large_dict: Any) -> Any:
    return OmegaConf.create(large_dict)


@fixture(scope="module")
def merge_data(small_dict: Any) -> Any:
    return [OmegaConf.create(small_dict) for _ in range(5)]


@fixture(scope="module")
def small_list() -> Any:
    return build_list(3, 1)


@fixture(scope="module")
def small_listconfig(small_list: Any) -> Any:
    return OmegaConf.create(small_list)


@mark.parametrize(
    "data",
    [
        lazy_fixture("small_dict"),
        lazy_fixture("large_dict"),
        lazy_fixture("small_dict_config"),
        lazy_fixture("large_dict_config"),
        lazy_fixture("dict_config_with_list_leaf"),
    ],
)
def test_omegaconf_create(data: Any, benchmark: Any) -> None:
    benchmark(OmegaConf.create, data)


@mark.parametrize(
    "merge_function",
    [
        param(OmegaConf.merge, id="merge"),
        param(OmegaConf.unsafe_merge, id="unsafe_merge"),
    ],
)
def test_omegaconf_merge(merge_function: Any, merge_data: Any, benchmark: Any) -> None:
    benchmark(merge_function, merge_data)


@mark.parametrize(
    "lst",
    [
        lazy_fixture("small_list"),
        lazy_fixture("small_listconfig"),
    ],
)
def test_list_in(lst: List[Any], benchmark: Any) -> None:
    benchmark(lambda seq, val: val in seq, lst, 10)


@mark.parametrize(
    "lst",
    [
        lazy_fixture("small_list"),
        lazy_fixture("small_listconfig"),
    ],
)
def test_list_iter(lst: List[Any], benchmark: Any) -> None:
    def iterate(seq: Any) -> None:
        for _ in seq:
            pass

    benchmark(iterate, lst)


@mark.parametrize(
    "strict_interpolation_validation",
    [True, False],
)
@mark.parametrize(
    ("value", "expected"),
    [
        ("simple", ValueKind.VALUE),
        ("${a}", ValueKind.INTERPOLATION),
        ("${a:b,c,d}", ValueKind.INTERPOLATION),
        ("${${b}}", ValueKind.INTERPOLATION),
        ("${a:${b}}", ValueKind.INTERPOLATION),
    ],
)
def test_get_value_kind(
    strict_interpolation_validation: bool, value: Any, expected: Any, benchmark: Any
) -> None:
    assert benchmark(get_value_kind, value, strict_interpolation_validation) == expected


def test_is_missing_literal(benchmark: Any) -> None:
    assert benchmark(_is_missing_literal, "???")
