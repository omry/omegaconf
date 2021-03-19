try:
    __import__("pkg_resources").declare_namespace(__name__)
except ImportError:  # pragma: no cover
    import pkgutil

    __path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore
