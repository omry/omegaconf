"""
OmegaConf setup
    Instructions:
    # Build:
    rm -rf dist/ omegaconf.egg-info/
    python setup.py sdist bdist_wheel
    # Upload:
    twine upload dist/*
"""

import codecs
import os
import re

import setuptools

here = os.path.abspath(os.path.dirname(__file__))


def find_version(*file_paths):
    def read(*parts):
        with codecs.open(os.path.join(here, *parts), "r") as fp:
            return fp.read()

    version_file = read(*file_paths)
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


with open("README.md", "r") as fh:
    LONG_DESC = fh.read()
    setuptools.setup(
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
        packages=["omegaconf"],
        python_requires=">=3.6",
        classifiers=[
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "Programming Language :: Python :: 3.8",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=[
            "PyYAML",
            # Use dataclasses backport for Python 3.6.
            "dataclasses;python_version=='3.6'",
        ],
        # Install development dependencies with
        # pip install -e ".[dev]"
        extras_require={
            "dev": [
                "black",
                "coveralls",
                "flake8",
                "pre-commit",
                "pytest",
                "pytest-mock",
                "nox",
                "towncrier",
                "twine",
                "sphinx",
                "mypy",
                "isort",
            ],
            "coverage": ["coveralls"],
            "lint": ["pytest", "black", "flake8", "mypy", "isort"],
        },
    )
