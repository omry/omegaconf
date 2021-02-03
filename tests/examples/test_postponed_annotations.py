import sys

import pytest


@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7")
def test_simple_types_class_postponed() -> None:
    # import from a module which has `from __future__ import annotations`
    from tests.examples.dataclass_postponed_annotations import simple_types_class

    simple_types_class()


@pytest.mark.skipif(sys.version_info < (3, 7), reason="requires Python 3.7")
def test_conversions_postponed() -> None:
    # import from a module which has `from __future__ import annotations`
    from tests.examples.dataclass_postponed_annotations import conversions

    conversions()
