import tarfile
import zipfile
from pathlib import Path

import pytest

from build_helpers.check_package_artifacts import (
    assert_contains_plugin,
    normalized_members,
)


def write_tar_gz(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tarfile.open(path, "w:gz") as tf:
        for name, data in members.items():
            info = tarfile.TarInfo(name)
            info.size = len(data)
            tf.addfile(info, fileobj=__import__("io").BytesIO(data))


def write_wheel(path: Path, members: dict[str, bytes]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path, "w") as zf:
        for name, data in members.items():
            zf.writestr(name, data)


def test_normalized_members_strip_sdist_root(tmp_path: Path) -> None:
    artifact = tmp_path / "omegaconf_pydevd-1.0.0.tar.gz"
    write_tar_gz(
        artifact,
        {
            "omegaconf_pydevd-1.0.0/README-pydevd.md": b"",
            "omegaconf_pydevd-1.0.0/pydevd_plugins/__init__.py": b"",
        },
    )

    assert normalized_members(artifact) == [
        "README-pydevd.md",
        "pydevd_plugins/__init__.py",
    ]


def test_assert_contains_plugin_accepts_expected_pydevd_layout(tmp_path: Path) -> None:
    artifact = tmp_path / "omegaconf_pydevd-1.0.0.tar.gz"
    write_tar_gz(
        artifact,
        {
            "omegaconf_pydevd-1.0.0/LICENSE": b"",
            "omegaconf_pydevd-1.0.0/README-pydevd.md": b"",
            "omegaconf_pydevd-1.0.0/build_helpers/__init__.py": b"",
            "omegaconf_pydevd-1.0.0/build_helpers/build_helpers.py": b"",
            "omegaconf_pydevd-1.0.0/omegaconf/version.py": b"__version__ = '1.0.0'\n",
            "omegaconf_pydevd-1.0.0/pydevd_plugins/__init__.py": b"",
            "omegaconf_pydevd-1.0.0/pydevd_plugins/extensions/__init__.py": b"",
            "omegaconf_pydevd-1.0.0/pydevd_plugins/extensions/pydevd_plugin_omegaconf.py": b"",
            "omegaconf_pydevd-1.0.0/pyproject.toml": b"",
            "omegaconf_pydevd-1.0.0/setup.cfg": b"",
            "omegaconf_pydevd-1.0.0/setup_pydevd.py": b"",
        },
    )

    assert_contains_plugin(artifact)


def test_assert_contains_plugin_rejects_unexpected_pydevd_members(
    tmp_path: Path,
) -> None:
    artifact = tmp_path / "omegaconf_pydevd-1.0.0-py3-none-any.whl"
    write_wheel(
        artifact,
        {
            "LICENSE": b"",
            "README-pydevd.md": b"",
            "pydevd_plugins/__init__.py": b"",
            "pydevd_plugins/extensions/__init__.py": b"",
            "pydevd_plugins/extensions/pydevd_plugin_omegaconf.py": b"",
            "tests/test_pydev_resolver_plugin.py": b"",
            "omegaconf_pydevd-1.0.0.dist-info/METADATA": b"",
        },
    )

    with pytest.raises(AssertionError, match="unexpected members"):
        assert_contains_plugin(artifact)
