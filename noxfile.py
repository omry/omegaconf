import os

import nox
from nox import Session

DEFAULT_PYTHON_VERSIONS = ["3.6", "3.7", "3.8", "3.9", "3.10", "3.11"]

PYTHON_VERSIONS = os.environ.get(
    "NOX_PYTHON_VERSIONS", ",".join(DEFAULT_PYTHON_VERSIONS)
).split(",")

nox.options.error_on_missing_interpreters = True


def deps(
    session: Session, editable_install: bool, requirements: str = "requirements/dev.txt"
) -> None:
    session.install(
        "--upgrade",
        "setuptools<=66",  # pinned due to DeprecationWarning, see https://github.com/omry/omegaconf/issues/1068
        "pip",
    )
    extra_flags = ["-e"] if editable_install else []
    session.install("-r", requirements, *extra_flags, ".", silent=True)


@nox.session(python=PYTHON_VERSIONS)  # type: ignore
def omegaconf(session: Session) -> None:
    deps(session, editable_install=False)  # ensure we test the regular install
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)  # type: ignore
def benchmark(session: Session) -> None:
    deps(session, editable_install=True)
    session.run("pytest", "benchmark/benchmark.py")


@nox.session  # type: ignore
def docs(session: Session) -> None:
    deps(session, False, "requirements/docs.txt")
    session.chdir("docs")
    session.run("sphinx-build", "-W", "-b", "html", "source", "build")
    session.install("pytest")  # required for `sphinx-build -b doctest`:
    session.run("sphinx-build", "-W", "-b", "doctest", "source", "build")


@nox.session(python=PYTHON_VERSIONS)  # type: ignore
def coverage(session: Session) -> None:
    # For coverage, we must use the editable installation because
    # `coverage run -m pytest` prepends `sys.path` with "." (the current
    # folder), so that the local code will be used in tests even if we set
    # `editable_install=False`. This would cause problems due to potentially
    # missing the generated grammar files.
    deps(session, editable_install=True)
    session.run("coverage", "erase")
    session.run("coverage", "run", "--append", "-m", "pytest", silent=True)
    session.run("coverage", "report", "--fail-under=100")
    # report to coveralls
    session.run("coveralls", success_codes=[0, 1])

    session.run("coverage", "erase")


@nox.session(python=PYTHON_VERSIONS)  # type: ignore
def lint(session: Session) -> None:
    deps(session, editable_install=True)
    session.run(
        "mypy", ".", "--strict", "--install-types", "--non-interactive", silent=True
    )
    session.run("isort", ".", "--check", silent=True)
    session.run("black", "--check", ".", silent=True)
    session.run("flake8")


@nox.session(python=PYTHON_VERSIONS)  # type: ignore
def test_jupyter_notebook(session: Session) -> None:
    if session.python not in DEFAULT_PYTHON_VERSIONS:
        session.skip(
            "Not testing Jupyter notebook on Python {}, supports [{}]".format(
                session.python, ",".join(DEFAULT_PYTHON_VERSIONS)
            )
        )
    deps(session, editable_install=False)
    session.install("jupyter", "nbval")
    extra_flags = ["-Wignore::ResourceWarning"]
    extra_flags.extend(
        [
            # Ignore deprecation warnings raised by jupyter_client in Python 3.10
            # https://github.com/jupyter/jupyter_client/issues/713
            "-Wdefault:There is no current event loop:DeprecationWarning",
            # Block warning issued by nbval
            # https://github.com/computationalmodelling/nbval/issues/180
            "-Wdefault::pytest.PytestRemovedIn8Warning",
        ]
    )
    session.run(
        "pytest", "--nbval", "docs/notebook/Tutorial.ipynb", *extra_flags, silent=True
    )
