from importlib import import_module
from typing import Any, Dict, List

import pytest

from omegaconf import MISSING, DictConfig, ListConfig, OmegaConf, ValidationError
from tests import User


@pytest.mark.parametrize(
    "class_type",
    [
        "tests.structured_conf.data.dataclasses",
        "tests.structured_conf.data.attr_classes",
    ],
)
class TestConfigs:
    @pytest.mark.parametrize(
        "class_name,value,node",
        [
            ("ContainerInList", [{"user": 20}], "list_with_dict"),
            ("ContainerInList", [{"user": 20}], "list_with_dict"),
            ("ContainerInList", [[1, 2], [3, 4]], "list_with_list"),
            ("ContainerInList", [MISSING], "list_with_list"),
            ("ContainerInDict", {"users": {"default": 1}}, "dict_with_dict"),
            ("ContainerInDict", {"users": MISSING}, "dict_with_dict"),
            ("ContainerInDict", {"users": [1, 2]}, "dict_with_list"),
            ("ContainerInDict", {"users": MISSING}, "dict_with_list"),
            ("ContainerInListWithUser", [[User()], [MISSING]], "list_with_list"),
            ("ContainerInListWithUser", [{"foo": User()}], "list_with_dict"),
            ("ContainerInDictWithUser", {"users": [User(), User()]}, "dict_with_list"),
            ("ContainerInDictWithUser", {"users": {"foo": User()}}, "dict_with_dict"),
            ("ComplexList", [[{"number": 1}]], "list"),
            ("ComplexDict", {"users": {"data": [1, 2]}}, "dict"),
        ],
    )
    def test_container_as_element_type_valid(
        self, class_type: str, class_name: str, value: Any, node: str
    ) -> None:
        module: Any = import_module(class_type)
        class_ = getattr(module, class_name)
        cfg = OmegaConf.structured(class_)
        cfg[node] = value
        assert cfg[node] == value

    @pytest.mark.parametrize(
        "class_name,value,node",
        [
            ("ContainerInList", [{"user": True}], "list_with_dict"),
            ("ContainerInList", [{"user": User()}], "list_with_dict"),
            ("ContainerInList", [[1, 2], [True, 4]], "list_with_list"),
            ("ContainerInList", [[1, 2], [User(), 4]], "list_with_list"),
            ("ContainerInDict", {"users": {"default": True}}, "dict_with_dict"),
            ("ContainerInDict", {"users": {"default": User()}}, "dict_with_dict"),
            ("ContainerInDict", {"users": [1, True]}, "dict_with_list"),
            ("ContainerInDict", {"users": [1, User()]}, "dict_with_list"),
            ("ContainerInListWithUser", [[1, 2], [4, "invalid"]], "list_with_list"),
            ("ContainerInListWithUser", [{"foo": False}], "list_with_dict"),
            ("ContainerInDictWithUser", {"users": [1, 2]}, "dict_with_list"),
            (
                "ContainerInDictWithUser",
                {"users": {"foo": "invalid"}},
                "dict_with_dict",
            ),
            ("ComplexList", [[{"number": True}]], "list"),
            ("ComplexList", [[{"number": User()}]], "list"),
            ("ComplexDict", {"users": {"data": True}}, "dict"),
            ("ComplexDict", {"users": {"data": User()}}, "dict"),
        ],
    )
    def test_container_as_element_type_invalid(
        self, class_type: str, class_name: str, value: Any, node: str
    ) -> None:
        module: Any = import_module(class_type)
        class_ = getattr(module, class_name)
        cfg = OmegaConf.structured(class_)
        with pytest.raises(ValidationError):
            cfg[node] = value

    @pytest.mark.parametrize(
        "class_name,obj2,expected",
        [
            (
                "ContainerInList",
                {"list_with_list": [[4, 5]], "list_with_dict": [{"foo": 4}]},
                {"list_with_list": [[4, 5]], "list_with_dict": [{"foo": 4}]},
            ),
            (
                "ContainerInListWithUser",
                {"list_with_list": [[User()]], "list_with_dict": [{"foo": User()}]},
                {"list_with_list": [[User()]], "list_with_dict": [{"foo": User()}]},
            ),
            (
                "ContainerInDict",
                {
                    "dict_with_list": {"foo": [3, 4]},
                    "dict_with_dict": {"foo": {"var": 4}},
                },
                {
                    "dict_with_list": {"foo": [3, 4]},
                    "dict_with_dict": {"foo": {"var": 4}},
                },
            ),
            (
                "ContainerInDictWithUser",
                {
                    "dict_with_list": {"foo": [User()]},
                    "dict_with_dict": {"foo": {"var": User()}},
                },
                {
                    "dict_with_list": {"foo": [User()]},
                    "dict_with_dict": {"foo": {"var": User()}},
                },
            ),
            (
                "ComplexList",
                {"list": [[{"foo": 13}]]},
                {"list": [[{"foo": 13}]]},
            ),
            (
                "ComplexDict",
                {"dict": {"foo2": {"var2": [3, 4]}}},
                {"dict": {"foo": {"var": [1, 2]}, "foo2": {"var2": [3, 4]}}},
            ),
        ],
    )
    def test_container_as_element_type_merge(
        self, class_type: str, class_name: str, obj2: Any, expected: Any
    ) -> None:
        module: Any = import_module(class_type)
        class_ = getattr(module, class_name)
        cfg = OmegaConf.structured(class_)
        res = OmegaConf.merge(cfg, obj2)
        assert res == expected

    @pytest.mark.parametrize(
        "class_name,obj2",
        [
            (
                "ContainerInList",
                {
                    "list_with_list": [[4, "invalid_value"]],
                    "list_with_dict": [{"foo": 4}],
                },
            ),
            (
                "ContainerInList",
                {"list_with_list": [[4, User()]], "list_with_dict": [{"foo": 4}]},
            ),
            (
                "ContainerInList",
                {
                    "list_with_list": [[4, 5]],
                    "list_with_dict": [{"foo": "invalid_value"}],
                },
            ),
            (
                "ContainerInList",
                {"list_with_list": [[4, 5]], "list_with_dict": [{"foo": User()}]},
            ),
            (
                "ContainerInListWithUser",
                {
                    "list_with_list": [[User(), User()], [User()]],
                    "list_with_dict": [{"foo": "invalid"}],
                },
            ),
            (
                "ContainerInListWithUser",
                {"list_with_list": [[4, 5]], "list_with_dict": [{"foo": User()}]},
            ),
            (
                "ContainerInDict",
                {
                    "dict_with_list": {"foo": [3, "invalid_value"]},
                    "dict_with_dict": {"foo": {"var": 4}},
                },
            ),
            (
                "ContainerInDict",
                {
                    "dict_with_list": {"foo": [3, User()]},
                    "dict_with_dict": {"foo": {"var": 4}},
                },
            ),
            (
                "ContainerInDict",
                {
                    "dict_with_list": {"foo": [3, 4]},
                    "dict_with_dict": {"foo": {"var": "invalid_value"}},
                },
            ),
            (
                "ContainerInDict",
                {
                    "dict_with_list": {"foo": [3, 4]},
                    "dict_with_dict": {"foo": {"var": User()}},
                },
            ),
            (
                "ContainerInDictWithUser",
                {
                    "dict_with_list": {"foo": ["invalid", "invalid2"]},
                    "dict_with_dict": {"foo": {"var": User()}},
                },
            ),
            (
                "ContainerInDictWithUser",
                {
                    "dict_with_list": {"foo": [User()]},
                    "dict_with_dict": {"foo": {"var": "invalid"}},
                },
            ),
            (
                "ComplexList",
                {"list": [[{"foo": "invalid"}]]},
            ),
            (
                "ComplexList",
                {"list": [[{"foo": User()}]]},
            ),
            (
                "ComplexList",
                {
                    "list": ListConfig(
                        content=[[{"foo": "var"}]],
                        ref_type=List[List[Dict[str, str]]],
                        element_type=List[Dict[str, str]],
                    )
                },
            ),
            (
                "ComplexDict",
                {"dict": {"foo2": {"var2": ["invalid", 4]}}},
            ),
            (
                "ComplexDict",
                {
                    "dict": DictConfig(
                        content={"foo2": {"var2": ["invalid"]}},
                        ref_type=Dict[str, Dict[str, List[str]]],
                        key_type=str,
                        element_type=Dict[str, List[str]],
                    )
                },
            ),
        ],
    )
    def test_container_as_element_type_invalid_merge(
        self, class_type: str, class_name: str, obj2: Any
    ) -> None:
        module: Any = import_module(class_type)
        class_ = getattr(module, class_name)
        cfg = OmegaConf.structured(class_)
        cfg2 = OmegaConf.create(obj2)
        with pytest.raises(ValidationError):
            OmegaConf.merge(cfg, cfg2)
