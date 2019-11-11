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
        version=find_version("omegaconf", "__init__.py"),
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
        classifiers=[
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=["six", "PyYAML"],
        # Install development dependencies with
        # pip install -e ".[dev]"
        extras_require={
            # Python 3+ dependencies
            "dev": [
                "black",
                "coveralls",
                "flake8",
                "pre-commit",
                "pytest",
                "nox",
                "towncrier",
                "twine",
            ],
            # Python 2.7 dependencies
            "dev27": ["nox", "pre-commit", "pytest", "twine", "coveralls", "flake8"],
            "coverage": ["coveralls"],
            "lint": ["black", "flake8"],
        },
    )
