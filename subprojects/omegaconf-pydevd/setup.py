# type: ignore
import pathlib
import re

import setuptools

ROOT = pathlib.Path(__file__).parent.resolve()


def find_version(*file_paths: str) -> str:
    with open(ROOT / pathlib.Path(*file_paths), "r", encoding="utf-8") as fp:
        version_file = fp.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")


VERSION = find_version("version.py")
VERSION_MAJOR, VERSION_MINOR = VERSION.split(".", 2)[:2]
NEXT_MINOR = int(VERSION_MINOR) + 1
OMEGACONF_REQUIREMENT = (
    f"omegaconf>={VERSION_MAJOR}.{VERSION_MINOR}.0.dev0,"
    f"<{VERSION_MAJOR}.{NEXT_MINOR}.0"
)

with (ROOT / "README.md").open("r", encoding="utf-8") as fh:
    LONG_DESC = fh.read()

setuptools.setup(
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
    namespace_packages=[
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
    install_requires=[OMEGACONF_REQUIREMENT],
)
