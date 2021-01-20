# type: ignore
import os

import nox

DEFAULT_PYTHON_VERSIONS = ["3.6", "3.7", "3.8", "3.9"]

PYTHON_VERSIONS = os.environ.get(
    "NOX_PYTHON_VERSIONS", ",".join(DEFAULT_PYTHON_VERSIONS)
).split(",")


def deps(session):
    session.install("--upgrade", "setuptools", "pip")
    session.install("-r", "requirements/dev.txt", ".", silent=True)


@nox.session(python=PYTHON_VERSIONS)
def omegaconf(session):
    deps(session)
    session.run("pytest")


@nox.session(python=PYTHON_VERSIONS)
def benchmark(session):
    deps(session)
    session.run("pytest", "benchmark/benchmark.py")


@nox.session
def docs(session):
    deps(session)
    session.chdir("docs")
    session.run("sphinx-build", "-W", "-b", "doctest", "source", "build")
    session.run("sphinx-build", "-W", "-b", "html", "source", "build")


@nox.session(python=PYTHON_VERSIONS)
def coverage(session):
    deps(session)
    session.run("coverage", "erase")
    session.run("coverage", "run", "--append", "-m", "pytest", silent=True)
    session.run("coverage", "report", "--fail-under=100")
    # report to coveralls
    session.run("coveralls", success_codes=[0, 1])

    session.run("coverage", "erase")


@nox.session(python=PYTHON_VERSIONS)
def lint(session):
    deps(session)
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
    deps(session)
    session.install("jupyter", "nbval")
    session.run("pytest", "--nbval", "docs/notebook/Tutorial.ipynb", silent=True)
