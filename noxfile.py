# type: ignore
import os

import nox

DEFAULT_PYTHON_VERSIONS = ["3.6", "3.7", "3.8", "3.9"]

PYTHON_VERSIONS = os.environ.get(
    "NOX_PYTHON_VERSIONS", ",".join(DEFAULT_PYTHON_VERSIONS)
).split(",")


def deps(session, editable_installl):
    session.install("--upgrade", "setuptools", "pip")
    extra_flags = ["-e"] if editable_installl else []
    session.install("-r", "requirements/dev.txt", *extra_flags, ".", silent=True)


@nox.session(python=PYTHON_VERSIONS)
def omegaconf(session):
    deps(session, editable_installl=False)  # ensure we test the regular install
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)
def benchmark(session):
    deps(session, editable_installl=True)
    session.run("pytest", "benchmark/benchmark.py")


@nox.session
def docs(session):
    deps(session, editable_installl=True)
    session.chdir("docs")
    session.run("sphinx-build", "-W", "-b", "doctest", "source", "build")
    session.run("sphinx-build", "-W", "-b", "html", "source", "build")


@nox.session(python=PYTHON_VERSIONS)
def coverage(session):
    # For coverage, we must use the editable installation because
    # `coverage run -m pytest` prepends `sys.path` with "." (the current
    # folder), so that the local code will be used in tests even if we set
    # `editable_installl=False`. This would cause problems due to potentially
    # missing the generated grammar files.
    deps(session, editable_installl=True)
    session.run("coverage", "erase")
    session.run("coverage", "run", "--append", "-m", "pytest", silent=True)
    session.run("coverage", "report", "--fail-under=100")
    # report to coveralls
    session.run("coveralls", success_codes=[0, 1])

    session.run("coverage", "erase")


@nox.session(python=PYTHON_VERSIONS)
def lint(session):
    deps(session, editable_installl=True)
    session.run("mypy", ".", "--strict", silent=True)
    session.run("isort", ".", "--check", silent=True)
    session.run("black", "--check", ".", silent=True)
    session.run("flake8")


@nox.session(python=PYTHON_VERSIONS)
def test_jupyter_notebook(session):
    if session.python not in DEFAULT_PYTHON_VERSIONS:
        session.skip(
            "Not testing Jupyter notebook on Python {}, supports [{}]".format(
                session.python, ",".join(DEFAULT_PYTHON_VERSIONS)
            )
        )
    deps(session, editable_installl=False)
    session.install("jupyter", "nbval")
    session.run("pytest", "--nbval", "docs/notebook/Tutorial.ipynb", silent=True)
