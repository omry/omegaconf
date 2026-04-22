import sys
import tarfile
import zipfile
from pathlib import Path
from typing import Iterable, List

PYDEV_PLUGIN = "pydevd_plugins/extensions/pydevd_plugin_omegaconf.py"
OMEGACONF_PACKAGE = "omegaconf/"
PYDEVD_ARTIFACT_PREFIX = "omegaconf_pydevd-"
ALLOWED_PYDEVD_EXACT_MEMBERS = {
    "LICENSE",
    "MANIFEST-pydevd.in",
    "PKG-INFO",
    "README-pydevd.md",
    "build_helpers/__init__.py",
    "build_helpers/build_helpers.py",
    "omegaconf/version.py",
    "pyproject.toml",
    "setup.cfg",
    "setup_pydevd.py",
}
ALLOWED_PYDEVD_PREFIXES = (
    "pydevd_plugins/",
    "omegaconf_pydevd.egg-info/",
)


def list_archive_members(path: Path) -> List[str]:
    if path.suffix == ".whl":
        with zipfile.ZipFile(path) as zf:
            return [name for name in zf.namelist() if not name.endswith("/")]
    if path.suffixes[-2:] == [".tar", ".gz"]:
        with tarfile.open(path, "r:gz") as tf:
            return [member.name for member in tf.getmembers() if member.isfile()]
    raise ValueError(f"Unsupported artifact type: {path}")


def contains_plugin(members: Iterable[str]) -> bool:
    return any(member.endswith(PYDEV_PLUGIN) for member in members)


def normalized_members(path: Path) -> List[str]:
    members = list_archive_members(path)
    if path.suffixes[-2:] != [".tar", ".gz"]:
        return members

    normalized = []
    for member in members:
        _, _, remainder = member.partition("/")
        normalized.append(remainder or member)
    return normalized


def is_allowed_pydevd_member(member: str) -> bool:
    if member in ALLOWED_PYDEVD_EXACT_MEMBERS:
        return True
    if any(member.startswith(prefix) for prefix in ALLOWED_PYDEVD_PREFIXES):
        return True
    return ".dist-info/" in member


def assert_contains_plugin(path: Path) -> None:
    members = normalized_members(path)
    if not contains_plugin(members):
        raise AssertionError(f"{path.name} does not contain {PYDEV_PLUGIN}")
    unexpected_omegaconf_members = sorted(
        member
        for member in members
        if member.startswith(OMEGACONF_PACKAGE)
        and member not in ALLOWED_PYDEVD_EXACT_MEMBERS
    )
    if unexpected_omegaconf_members:
        raise AssertionError(f"{path.name} unexpectedly contains {OMEGACONF_PACKAGE}")
    unexpected_members = sorted(
        member for member in members if not is_allowed_pydevd_member(member)
    )
    if unexpected_members:
        formatted = ", ".join(unexpected_members[:5])
        raise AssertionError(f"{path.name} contains unexpected members: {formatted}")


def assert_excludes_plugin(path: Path) -> None:
    members = normalized_members(path)
    if contains_plugin(members):
        raise AssertionError(f"{path.name} unexpectedly contains {PYDEV_PLUGIN}")


def main() -> int:
    dist_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist")
    artifacts = sorted(path for path in dist_dir.iterdir() if path.is_file())

    main_artifacts = [p for p in artifacts if p.name.startswith("omegaconf-")]
    pydev_artifacts = [
        p for p in artifacts if p.name.startswith(PYDEVD_ARTIFACT_PREFIX)
    ]

    assert main_artifacts, "No omegaconf artifacts found"
    assert pydev_artifacts, "No omegaconf-pydevd artifacts found"

    for artifact in main_artifacts:
        assert_excludes_plugin(artifact)
    for artifact in pydev_artifacts:
        assert_contains_plugin(artifact)

    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
