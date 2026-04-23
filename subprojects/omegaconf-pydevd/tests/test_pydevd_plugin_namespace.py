import json
import os
import subprocess
import sys
from pathlib import Path


OLD_NAMESPACE_INIT = """import pkgutil

__path__ = pkgutil.extend_path(__path__, __name__)
"""


FAKE_PKG_RESOURCES = """_namespaces = set()


def _package_paths(name):
    import os
    import sys

    relpath = os.path.join(*name.split("."))
    paths = []
    for entry in sys.path:
        if not entry:
            continue
        candidate = os.path.join(entry, relpath)
        if os.path.isdir(candidate):
            paths.append(candidate)
    return paths


def declare_namespace(name):
    import sys

    _namespaces.add(name)
    sys.modules[name].__path__ = _package_paths(name)


def fixup_namespace_packages(_):
    import sys

    for name in _namespaces:
        module = sys.modules.get(name)
        if module is not None:
            module.__path__ = _package_paths(name)
"""


DISCOVERY_SCRIPT = """import importlib
import json
import os
import pkgutil
import sys

import pydevd_plugins.extensions as extensions
import pkg_resources

plugin_root = os.environ["OMEGACONF_PYDEVD_PLUGIN_ROOT"]
sys.path.insert(0, plugin_root)
importlib.invalidate_caches()
pkg_resources.fixup_namespace_packages(plugin_root)

print(
    json.dumps(
        sorted(
            name
            for _, name, _ in pkgutil.walk_packages(
                extensions.__path__, extensions.__name__ + "."
            )
        )
    )
)
"""


EDITABLE_DISCOVERY_SCRIPT = """import importlib
import json
import os
import pkgutil
import sys
from importlib.machinery import ModuleSpec, PathFinder
from importlib.util import spec_from_file_location
from pathlib import Path

import pkg_resources


class EditableFinder:
    @classmethod
    def find_spec(cls, fullname, path=None, target=None):
        plugin_root = Path(os.environ["OMEGACONF_PYDEVD_PLUGIN_ROOT"])
        mapping = {
            "pydevd_plugins": plugin_root / "pydevd_plugins",
            "pydevd_plugins.extensions": plugin_root / "pydevd_plugins" / "extensions",
        }
        candidate = mapping.get(fullname)
        if candidate is not None:
            return spec_from_file_location(fullname, candidate / "__init__.py")

        parent, _, _ = fullname.rpartition(".")
        if parent in mapping:
            return PathFinder.find_spec(fullname, path=[str(mapping[parent])])
        return None


def install_namespace_path(fullname, path_entry):
    module = sys.modules.get(fullname)
    if module is None:
        module = importlib.import_module(fullname)
    module_path = module.__dict__.setdefault("__path__", [])
    if path_entry not in module_path:
        module_path.append(path_entry)


sys.meta_path.append(EditableFinder)

if os.environ.get("OMEGACONF_PYDEVD_INSTALL_NAMESPACE_PATHS") == "1":
    plugin_root = Path(os.environ["OMEGACONF_PYDEVD_PLUGIN_ROOT"])
    install_namespace_path("pydevd_plugins", str(plugin_root / "pydevd_plugins"))
    install_namespace_path(
        "pydevd_plugins.extensions",
        str(plugin_root / "pydevd_plugins" / "extensions"),
    )

import pydevd_plugins.extensions as extensions
pkg_resources.fixup_namespace_packages(os.environ["OMEGACONF_PYDEVD_PLUGIN_ROOT"])

print(
    json.dumps(
        sorted(
            name
            for _, name, _ in pkgutil.walk_packages(
                extensions.__path__, extensions.__name__ + "."
            )
        )
    )
)
"""


def _write_namespace_package(root: Path, init_text: str) -> None:
    extensions_dir = root / "pydevd_plugins" / "extensions"
    extensions_dir.mkdir(parents=True)
    (root / "pydevd_plugins" / "__init__.py").write_text(init_text)
    (extensions_dir / "__init__.py").write_text(init_text)


def _build_project(tmp_path: Path, init_text: str) -> tuple[Path, Path, Path]:
    project_root = tmp_path / "project"
    support_root = project_root / "support"
    bundled_root = project_root / "bundled"
    plugin_root = project_root / "plugin"

    support_root.mkdir(parents=True)
    (support_root / "pkg_resources.py").write_text(FAKE_PKG_RESOURCES)

    _write_namespace_package(bundled_root, init_text)
    _write_namespace_package(plugin_root, init_text)
    (
        bundled_root / "pydevd_plugins" / "extensions" / "pydevd_plugin_builtin.py"
    ).write_text("X = 1\n")
    (
        plugin_root / "pydevd_plugins" / "extensions" / "pydevd_plugin_omegaconf.py"
    ).write_text("Y = 1\n")

    return project_root, support_root, bundled_root


def _discover_extensions_from_editable_install(
    tmp_path: Path,
    *,
    install_namespace_paths: bool,
) -> list[str]:
    project_root, support_root, bundled_root = _build_project(tmp_path, OLD_NAMESPACE_INIT)
    plugin_root = project_root / "plugin"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(support_root), str(bundled_root)])
    env["OMEGACONF_PYDEVD_PLUGIN_ROOT"] = str(plugin_root)
    if install_namespace_paths:
        env["OMEGACONF_PYDEVD_INSTALL_NAMESPACE_PATHS"] = "1"
    result = subprocess.run(
        [sys.executable, "-S", "-c", EDITABLE_DISCOVERY_SCRIPT],
        check=True,
        capture_output=True,
        cwd=project_root,
        env=env,
        text=True,
    )
    return json.loads(result.stdout)


def _discover_extensions(tmp_path: Path, init_text: str) -> list[str]:
    project_root, support_root, bundled_root = _build_project(tmp_path, init_text)
    plugin_root = project_root / "plugin"
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join([str(support_root), str(bundled_root)])
    env["OMEGACONF_PYDEVD_PLUGIN_ROOT"] = str(plugin_root)
    result = subprocess.run(
        [sys.executable, "-S", "-c", DISCOVERY_SCRIPT],
        check=True,
        capture_output=True,
        cwd=project_root,
        env=env,
        text=True,
    )
    return json.loads(result.stdout)


def test_current_namespace_init_supports_late_plugin_discovery(tmp_path: Path) -> None:
    init_text = (
        Path(__file__).resolve().parents[1] / "pydevd_plugins" / "__init__.py"
    ).read_text()
    discovered = _discover_extensions(tmp_path, init_text)
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" in discovered


def test_old_namespace_init_does_not_support_late_plugin_discovery(
    tmp_path: Path,
) -> None:
    discovered = _discover_extensions(tmp_path, OLD_NAMESPACE_INIT)
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" not in discovered


def test_editable_install_without_namespace_paths_is_not_discovered(
    tmp_path: Path,
) -> None:
    discovered = _discover_extensions_from_editable_install(
        tmp_path,
        install_namespace_paths=False,
    )
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" not in discovered


def test_editable_install_with_namespace_paths_is_discovered(
    tmp_path: Path,
) -> None:
    discovered = _discover_extensions_from_editable_install(
        tmp_path,
        install_namespace_paths=True,
    )
    assert "pydevd_plugins.extensions.pydevd_plugin_omegaconf" in discovered
