import codecs
import distutils.log
import errno
import os
import re
import shutil
import subprocess
import sys
from functools import partial
from pathlib import Path
from typing import List, Optional

from setuptools import Command
from setuptools.command import build_py, develop, sdist


class ANTLRCommand(Command):  # type: ignore  # pragma: no cover
    """Generate parsers using ANTLR."""

    description = "Run ANTLR"
    user_options: List[str] = []

    def run(self) -> None:
        """Run command."""
        build_dir = Path(__file__).parent.absolute()
        project_root = build_dir.parent
        for grammar in [
            "OmegaConfGrammarLexer.g4",
            "OmegaConfGrammarParser.g4",
        ]:
            command = [
                "java",
                "-jar",
                str(build_dir / "bin" / "antlr-4.11.1-complete.jar"),
                "-Dlanguage=Python3",
                "-o",
                str(project_root / "omegaconf" / "grammar" / "gen"),
                "-Xexact-output-dir",
                "-visitor",
                str(project_root / "omegaconf" / "grammar" / grammar),
            ]

            self.announce(
                f"Generating parser for Python3: {command}",
                level=distutils.log.INFO,
            )

            subprocess.check_call(command)

            self.announce(
                "Fixing imports for generated parsers",
                level=distutils.log.INFO,
            )
            self._fix_imports()

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass

    def _fix_imports(self) -> None:
        """Fix imports from the generated parsers to use the vendored antlr4 instead"""
        build_dir = Path(__file__).parent.absolute()
        project_root = build_dir.parent
        lib = "antlr4"
        pkgname = 'omegaconf.vendor'

        replacements = [
            partial(  # import antlr4 -> import omegaconf.vendor.antlr4
                re.compile(r'(^\s*)import {}\n'.format(lib), flags=re.M).sub,
                r'\1from {} import {}\n'.format(pkgname, lib)
            ),
            partial(  # from antlr4 -> from fomegaconf.vendor.antlr4
                re.compile(r'(^\s*)from {}(\.|\s+)'.format(lib), flags=re.M).sub,
                r'\1from {}.{}\2'.format(pkgname, lib)
            ),
        ]

        path = project_root / "omegaconf" / "grammar" / "gen"
        for item in path.iterdir():
            if item.is_file() and item.name.endswith(".py"):
                text = item.read_text('utf8')
                for replacement in replacements:
                    text = replacement(text)
                item.write_text(text, 'utf8')


class BuildPyCommand(build_py.build_py):  # pragma: no cover
    def run(self) -> None:
        if not self.dry_run:
            self.run_command("clean")
            run_antlr(self)
        build_py.build_py.run(self)


class CleanCommand(Command):  # type: ignore  # pragma: no cover
    """
    Our custom command to clean out junk files.
    """

    description = "Cleans out generated and junk files we don't want in the repo"
    dry_run: bool
    user_options: List[str] = []

    def run(self) -> None:
        root = Path(__file__).parent.parent.absolute()
        files = find(
            root=root,
            include_files=["^omegaconf/grammar/gen/.*"],
            include_dirs=[
                "^omegaconf\\.egg-info$",
                "\\.eggs$",
                "^\\.mypy_cache$",
                "^\\.pytest_cache$",
                ".*/__pycache__$",
                "^__pycache__$",
                "^build$",
            ],
            scan_exclude=["^.git$", "^.nox/.*$"],
            excludes=[".*\\.gitignore$", ".*/__init__.py"],
        )

        if self.dry_run:
            print("Dry run! Would clean up the following files and dirs:")
            print("\n".join(sorted(map(str, files))))
        else:
            for f in files:
                if f.exists():
                    if f.is_dir():
                        shutil.rmtree(f, ignore_errors=True)
                    else:
                        f.unlink()

    def initialize_options(self) -> None:
        pass

    def finalize_options(self) -> None:
        pass


class DevelopCommand(develop.develop):  # pragma: no cover
    def run(self) -> None:  # type: ignore
        if not self.dry_run:
            run_antlr(self)
        develop.develop.run(self)


class SDistCommand(sdist.sdist):  # pragma: no cover
    def run(self) -> None:
        if not self.dry_run:  # type: ignore
            self.run_command("clean")
            run_antlr(self)
        sdist.sdist.run(self)


def find(
    root: Path,
    include_files: List[str],
    include_dirs: List[str],
    excludes: List[str],
    rbase: Optional[Path] = None,
    scan_exclude: Optional[List[str]] = None,
) -> List[Path]:
    if rbase is None:
        rbase = Path()
    if scan_exclude is None:
        scan_exclude = []
    files = []
    scan_root = root / rbase
    for entry in scan_root.iterdir():
        path = rbase / entry.name
        if matches(scan_exclude, path):
            continue

        if entry.is_dir():
            if matches(include_dirs, path):
                if not matches(excludes, path):
                    files.append(path)
            else:
                ret = find(
                    root=root,
                    include_files=include_files,
                    include_dirs=include_dirs,
                    excludes=excludes,
                    rbase=path,
                    scan_exclude=scan_exclude,
                )
                files.extend(ret)
        else:
            if matches(include_files, path) and not matches(excludes, path):
                files.append(path)

    return files


def find_version(*file_paths: str) -> str:
    root = Path(__file__).parent.parent.absolute()
    with codecs.open(root / Path(*file_paths), "r") as fp:  # type: ignore
        version_file = fp.read()
    version_match = re.search(r"^__version__ = ['\"]([^'\"]*)['\"]", version_file, re.M)
    if version_match:
        return version_match.group(1)
    raise RuntimeError("Unable to find version string.")  # pragma: no cover


def matches(patterns: List[str], path: Path) -> bool:
    string = str(path).replace(os.sep, "/")  # for Windows
    for pattern in patterns:
        if re.match(pattern, string):
            return True
    return False


def run_antlr(cmd: Command) -> None:  # pragma: no cover
    try:
        cmd.announce("Generating parsers with antlr4", level=distutils.log.INFO)
        cmd.run_command("antlr")
    except OSError as e:
        if e.errno == errno.ENOENT:
            msg = f"| Unable to generate parsers: {e} |"
            msg = "=" * len(msg) + "\n" + msg + "\n" + "=" * len(msg)
            cmd.announce(f"{msg}", level=distutils.log.FATAL)
            sys.exit(1)
        else:
            raise
