import re
import shutil
import subprocess
from functools import partial
from itertools import chain
from pathlib import Path
from typing import Callable, FrozenSet, Generator, List, Set, Tuple, Union

WHITELIST = {'README.txt', '__init__.py', 'vendor.txt'}


def delete_all(*paths: Path, whitelist: Union[Set[str], FrozenSet[str]] = frozenset()) -> None:
    """Clear all the items in each of the indicated paths, except for elements listed
    in the whitelist"""
    for item in paths:
        if item.is_dir():
            shutil.rmtree(item, ignore_errors=True)
        elif item.is_file() and item.name not in whitelist:
            item.unlink()


def iter_subtree(path: Path, depth: int = 0) -> Generator[Tuple[Path, int], None, None]:
    """Recursively yield all files in a subtree, depth-first"""
    if not path.is_dir():
        if path.is_file():
            yield path, depth
        return
    for item in path.iterdir():
        if item.is_dir():
            yield from iter_subtree(item, depth + 1)
        elif item.is_file():
            yield item, depth + 1


def patch_vendor_imports(file: Path, replacements: List[Callable[[str], str]]) -> None:
    """Apply a list of replacements/patches to a given file"""
    text = file.read_text('utf8')
    for replacement in replacements:
        text = replacement(text)
    file.write_text(text, 'utf8')


def find_vendored_libs(vendor_dir: Path, whitelist: Set[str]) -> Tuple[List[str], List[Path]]:
    vendored_libs = []
    paths = []
    for item in vendor_dir.iterdir():
        if item.is_dir():
            vendored_libs.append(item.name)
        elif item.is_file() and item.name not in whitelist:
            vendored_libs.append(item.stem)  # without extension
        else:  # not a dir or a file not in the whilelist
            continue
        paths.append(item)
    return vendored_libs, paths


def vendor(vendor_dir: Path, relative_imports: bool = False) -> None:
    # target package is <parent>.<vendor_dir>; foo/vendor -> foo.vendor
    pkgname = f'{vendor_dir.parent.name}.{vendor_dir.name}'

    # remove everything
    delete_all(*vendor_dir.iterdir(), whitelist=WHITELIST)

    # install with pip
    subprocess.run([
        'pip', 'install', '-t', str(vendor_dir),
        '-r', str(vendor_dir / 'vendor.txt'),
        '--no-compile', '--no-deps'
    ])

    # delete stuff that's not needed
    delete_all(
        *vendor_dir.glob('*.dist-info'),
        *vendor_dir.glob('*.egg-info'),
        vendor_dir / 'bin')

    vendored_libs, paths = find_vendored_libs(vendor_dir, WHITELIST)

    if not relative_imports:
        replacements: List[Callable[[str], str]] = []
        for lib in vendored_libs:
            replacements += (
                partial(  # import bar -> import foo.vendor.bar
                    re.compile(r'(^\s*)import {}\n'.format(lib), flags=re.M).sub,
                    r'\1from {} import {}\n'.format(pkgname, lib)
                ),
                partial(  # from bar -> from foo.vendor.bar
                    re.compile(r'(^\s*)from {}(\.|\s+)'.format(lib), flags=re.M).sub,
                    r'\1from {}.{}\2'.format(pkgname, lib)
                ),
            )

    for file, depth in chain.from_iterable(map(iter_subtree, paths)):
        if relative_imports:
            pkgname = '.' * (depth - 1)
            replacements = []
            for lib in vendored_libs:
                replacements += (
                    partial(
                        re.compile(r'(^\s*)import {}\n'.format(lib), flags=re.M).sub,
                        r'\1from {} import {}\n'.format(pkgname, "")
                    ),
                    partial(
                        re.compile(r'^from {}(\s+)'.format(lib), flags=re.M).sub,
                        r'from .{}\1'.format(pkgname)
                    ),
                    partial(
                        re.compile(r'(^\s*)from {}(\.+)'.format(lib), flags=re.M).sub,
                        r'\1from {}\2'.format(pkgname)
                    ),
                )
        patch_vendor_imports(file, replacements)


if __name__ == '__main__':
    # this assumes this is a script in `build_helpers`
    here = Path('__file__').resolve().parent
    vendor_dir = here / 'omegaconf' / 'vendor'
    assert (vendor_dir / 'vendor.txt').exists(), 'omegaconf/vendor/vendor.txt file not found'
    assert (vendor_dir / '__init__.py').exists(), 'omegaconf/vendor/__init__.py file not found'
    vendor(vendor_dir, relative_imports=True)
