def test_simple_types_class_postponed() -> None:
    # import from a module which has `from __future__ import annotations`
    from tests.examples.dataclass_postponed_annotations import simple_types_class

    simple_types_class()


def test_conversions_postponed() -> None:
    # import from a module which has `from __future__ import annotations`
    from tests.examples.dataclass_postponed_annotations import conversions

    conversions()
