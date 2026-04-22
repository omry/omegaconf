from contextlib import contextmanager
import os
import pkgutil
import sys
from types import ModuleType
from pathlib import Path
from typing import Iterator

import pytest


OLD_NAMESPACE_INIT = """import pkgutil

__path__ = pkgutil.extend_path(__path__, __name__)
"""


@contextmanager
def _clear_pydevd_plugin_modules() -> Iterator[None]:
    saved = {
        name: module
        for name, module in sys.modules.items()
        if name == "pydevd_plugins" or name.startswith("pydevd_plugins.")
    }
    try:
        for name in saved:
            sys.modules.pop(name, None)
        yield
    finally:
        for name in list(sys.modules):
            if name == "pydevd_plugins" or name.startswith("pydevd_plugins."):
                sys.modules.pop(name, None)
        sys.modules.update(saved)


def _write_namespace_package(root: Path, init_text: str) -> None:
    extensions_dir = root / "pydevd_plugins" / "extensions"
    extensions_dir.mkdir(parents=True)
    (root / "pydevd_plugins" / "__init__.py").write_text(init_text)
    (extensions_dir / "__init__.py").write_text(init_text)


def _make_fake_pkg_resources() -> ModuleType:
    module = ModuleType("pkg_resources")
    namespaces: set[str] = set()

    def _package_paths(name: str) -> list[str]:
        relpath = os.path.join(*name.split("."))
        paths = []
        for entry in sys.path:
            if not entry:
                continue
            candidate = os.path.join(entry, relpath)
            if os.path.isdir(candidate):
                paths.append(candidate)
        return paths

    def declare_namespace(name: str) -> None:
        namespaces.add(name)
        mod = sys.modules[name]
        mod.__path__ = _package_paths(name)

    def fixup_namespace_packages(_: str) -> None:
        for name in namespaces:
            mod = sys.modules.get(name)
            if mod is not None:
                mod.__path__ = _package_paths(name)

    module.declare_namespace = declare_namespace  # type: ignore[attr-defined]
    module.fixup_namespace_packages = fixup_namespace_packages  # type: ignore[attr-defined]
    return module


def _discover_extensions(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    init_text: str,
) -> list[str]:
    repo_root = Path(__file__).resolve().parents[1]
    bundled_root = tmp_path / "bundled"
    plugin_root = tmp_path / "plugin"
    _write_namespace_package(bundled_root, init_text)
    _write_namespace_package(plugin_root, init_text)
    (
        bundled_root
        / "pydevd_plugins"
        / "extensions"
        / "pydevd_plugin_builtin.py"
    ).write_text("X = 1\n")
    (
        plugin_root
        / "pydevd_plugins"
        / "extensions"
        / "pydevd_plugin_omegaconf.py"
    ).write_text("Y = 1\n")

    filtered_path = [
        path
        for path in sys.path
        if Path(path or ".").resolve() != repo_root
    ]
    monkeypatch.setattr(sys, "path", filtered_path[:])
    monkeypatch.syspath_prepend(str(bundled_root))
    monkeypatch.setitem(sys.modules, "pkg_resources", _make_fake_pkg_resources())

    import pkg_resources

    with _clear_pydevd_plugin_modules():
        import pydevd_plugins.extensions as extensions

        monkeypatch.syspath_prepend(str(plugin_root))
        pkg_resources.fixup_namespace_packages(str(plugin_root))
        return [
            name
            for _, name, _ in pkgutil.walk_packages(
                extensions.__path__, extensions.__name__ + "."
            )
        ]


def test_current_namespace_init_supports_late_plugin_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    init_text = (
        Path(__file__).resolve().parents[1] / "pydevd_plugins" / "__init__.py"
    ).read_text()
    discovered = _discover_extensions(monkeypatch, tmp_path, init_text)
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" in discovered


def test_old_namespace_init_does_not_support_late_plugin_discovery(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    discovered = _discover_extensions(monkeypatch, tmp_path, OLD_NAMESPACE_INIT)
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" not in discovered
