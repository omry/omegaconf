# type: ignore
"""
OmegaConf setup
    Instructions:
    # Build:
    rm -rf dist/ omegaconf.egg-info/
    python setup.py sdist bdist_wheel
    # Upload:
    twine upload dist/*
"""
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
        setup_requires=["pytest-runner"],
        tests_require=["pytest"],
        url="https://github.com/omry/omegaconf",
        keywords="yaml configuration config",
        packages=["omegaconf", "omegaconf.grammar", "omegaconf.grammar.gen"],
        python_requires=">=3.6",
        classifiers=[
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "Programming Language :: Python :: 3.9",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=install_requires,
        package_data={"omegaconf": ["py.typed"]},
    )
