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
import pathlib
import re

import setuptools

from build_helpers.build_helpers import (
    ANTLRCommand,
    BuildPyCommand,
    CleanCommand,
    DevelopCommand,
    SDistCommand,
    find_version,
)


def parse_requirements(requirements_file: pathlib.Path) -> list[str]:
    """
    Parse a requirements.txt file and return a list of requirement strings.

    This replaces pkg_resources.parse_requirements(), which was removed from
    setuptools 82+. pkg_resources simply strips each line and skips empty
    lines and comments -- the same behavior as this function.
    """
    requirements = []
    for line in requirements_file.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            # Strip trailing comments (e.g. "requests # comment")
            line = re.split(r"\s+#", line)[0].strip()
            requirements.append(line)
    return requirements


with pathlib.Path("requirements/base.txt").open() as requirements_txt:
    install_requires = parse_requirements(requirements_txt)


def find_vendored_packages(path):
    """Add all the packages in the `vendor` directory"""
    return [
        root.replace(os.path.sep, ".")
        for root, dirs, files in os.walk(path)
        if "__pycache__" not in root
    ]


vendored_packages = find_vendored_packages("omegaconf/vendor")

with open("README.md", "r") as fh:
    LONG_DESC = fh.read()
    setuptools.setup(
        cmdclass={
            "antlr": ANTLRCommand,
            "clean": CleanCommand,
            "sdist": SDistCommand,
            "build_py": BuildPyCommand,
            "develop": DevelopCommand,
        },
        name="omegaconf",
        version=find_version("omegaconf", "version.py"),
        author="Omry Yadan",
        author_email="omry@yadan.net",
        description="A flexible configuration library",
        long_description=LONG_DESC,
        long_description_content_type="text/markdown",
        url="https://github.com/omry/omegaconf",
        keywords="yaml configuration config",
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
        python_requires=">=3.9",
        classifiers=[
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3.14",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=install_requires,
        package_data={"omegaconf": ["py.typed"]},
    )
