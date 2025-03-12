# type: ignore
"""
OmegaConf setup
    Instructions:
    # Build:
    rm -rf dist/ omegaconf.egg-info/
    python -m build
    # Upload:
    twine upload dist/*
"""

import os
import sys

# Add the repository root to sys.path so that local modules like build_helpers are importable.
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))
import setuptools  # noqa: E402

from build_helpers.build_helpers import (  # noqa: E402
    ANTLRCommand,
    BuildPyCommand,
    CleanCommand,
    DevelopCommand,
    SDistCommand,
)


def find_vendored_packages(path: str) -> list[str]:
    """Add all the packages in the `vendor` directory."""
    return [
        root.replace(os.path.sep, ".")
        for root, dirs, files in os.walk(path)
        if "__pycache__" not in root
    ]


vendored_packages = find_vendored_packages("omegaconf/vendor")

setuptools.setup(
    cmdclass={
        "antlr": ANTLRCommand,
        "clean": CleanCommand,
        "sdist": SDistCommand,
        "build_py": BuildPyCommand,
        "develop": DevelopCommand,
    },
    # Metadata is now defined in pyproject.toml under [project].
    packages=[
        "omegaconf",
        "omegaconf.grammar",
        "omegaconf.grammar.gen",
        "omegaconf.resolvers",
        "omegaconf.resolvers.oc",
        "pydevd_plugins",
        "pydevd_plugins.extensions",
    ]
    + vendored_packages,
)
