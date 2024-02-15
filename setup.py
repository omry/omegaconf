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
import pathlib

import pkg_resources
import setuptools

from build_helpers.build_helpers import (
    ANTLRCommand,
    BuildPyCommand,
    CleanCommand,
    DevelopCommand,
    SDistCommand,
    find_version,
)

with pathlib.Path("requirements/base.txt").open() as requirements_txt:
    install_requires = [
        str(requirement)
        for requirement in pkg_resources.parse_requirements(requirements_txt)
    ]


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
        python_requires=">=3.8",
        classifiers=[
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=install_requires,
        package_data={"omegaconf": ["py.typed"]},
    )
