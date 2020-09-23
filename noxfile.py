# type: ignore
import os

import nox

DEFAULT_PYTHON_VERSIONS = ["3.6", "3.7", "3.8"]

PYTHON_VERSIONS = os.environ.get(
    "NOX_PYTHON_VERSIONS", ",".join(DEFAULT_PYTHON_VERSIONS)
).split(",")


def deps(session, local_install):
    session.install("--upgrade", "setuptools", "pip")
    extra_flags = ["-e"] if local_install else []
    session.install("-r", "requirements/dev.txt", *extra_flags, ".", silent=True)


@nox.session(python=PYTHON_VERSIONS)
def omegaconf(session):
    deps(session, local_install=False)  # ensure we test the installed version
    session.run("pytest")


@nox.session
def docs(session):
    deps(session, local_install=True)
    session.chdir("docs")
    session.run("sphinx-build", "-W", "-b", "doctest", "source", "build")
    session.run("sphinx-build", "-W", "-b", "html", "source", "build")


@nox.session(python=PYTHON_VERSIONS)
def coverage(session):
    # For coverage, we must use the local installation because
    # `coverage run -m pytest` prepends `sys.path` with "." (the current
    # folder), so that the local code will be used in tests even if we set
    # `local_install=False`. This would cause problems due to potentially
    # missing the generated grammar files.
    deps(session, local_install=True)
    session.run("coverage", "erase")
    session.run("coverage", "run", "--append", "-m", "pytest", silent=True)
    session.run("coverage", "report", "--fail-under=100")
    # report to coveralls
    session.run("coveralls", success_codes=[0, 1])

    session.run("coverage", "erase")


@nox.session(python=PYTHON_VERSIONS)
def lint(session):
    deps(session, local_install=True)
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
    deps(session, local_install=False)
    session.install("jupyter", "nbval")
    session.run("pytest", "--nbval", "docs/notebook/Tutorial.ipynb", silent=True)
