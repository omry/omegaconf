# type: ignore
"""
OmegaConf pydevd plugin setup.

Build:
    rm -rf dist/ omegaconf_pydevd.egg-info/
    python setup_pydevd.py sdist bdist_wheel
"""

import pathlib

import setuptools

from build_helpers.build_helpers import (
    PydevdEggInfoCommand,
    PydevdSDistCommand,
    find_version,
)

ROOT = pathlib.Path(__file__).parent
VERSION = find_version("omegaconf", "version.py")

with (ROOT / "README-pydevd.md").open("r", encoding="utf-8") as fh:
    LONG_DESC = fh.read()

setuptools.setup(
    cmdclass={"egg_info": PydevdEggInfoCommand, "sdist": PydevdSDistCommand},
    name="omegaconf-pydevd",
    version=VERSION,
    author="Omry Yadan",
    author_email="omry@yadan.net",
    description="pydevd debugger plugin for OmegaConf",
    long_description=LONG_DESC,
    long_description_content_type="text/markdown",
    url="https://github.com/omry/omegaconf",
    keywords="omegaconf pydevd debugpy debugger",
    packages=[
        "pydevd_plugins",
        "pydevd_plugins.extensions",
    ],
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
    install_requires=[f"omegaconf=={VERSION}"],
    options={"build": {"build_base": "build_pydevd"}},
)
