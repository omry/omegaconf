# type: ignore
import os
import pathlib
from typing import Any, cast

import setuptools

from build_helpers.build_helpers import (
    ANTLRCommand,
    BuildPyCommand,
    CleanCommand,
    DevelopCommand,
    SDistCommand,
    find_version,
)


def read_requirements(path):
    requirements = []
    req_path = pathlib.Path(path)
    with req_path.open() as requirements_txt:
        for line in requirements_txt:
            requirement = line.split("#")[0].strip()
            if not requirement:
                continue
            if requirement.startswith("-r "):
                requirements.extend(
                    read_requirements(req_path.parent / requirement[3:])
                )
            else:
                requirements.append(requirement)
    return requirements


install_requires = read_requirements("requirements/base.txt")


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
        ]
        + vendored_packages,
        python_requires=">=3.10",
        classifiers=[
            "Programming Language :: Python :: 3.10",
            "Programming Language :: Python :: 3.11",
            "Programming Language :: Python :: 3.12",
            "Programming Language :: Python :: 3.13",
            "Programming Language :: Python :: 3.14",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=install_requires,
        extras_require={"dev": read_requirements("requirements/dev.txt")},
        package_data=cast(Any, {"omegaconf": ["py.typed"]}),
    )
