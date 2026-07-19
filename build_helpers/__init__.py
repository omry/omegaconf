# ruff: noqa: F401, I001

# Order of imports is important (see warning otherwise when running tests)
import setuptools

# distutils is deprecated since Python 3.10 and removed in 3.12.
# setuptools provides a vendored compatibility layer, so guard the import.
try:
    import distutils  # noqa: F401
except ImportError:
    pass
