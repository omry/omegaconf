import nox
import os

DEFAULT_PYTHON_VERSIONS = ["2.7", "3.5", "3.6", "3.7"]

PYTHON_VERSIONS = os.environ.get(
    "NOX_PYTHON_VERSIONS", ",".join(DEFAULT_PYTHON_VERSIONS)
).split(",")


@nox.session(python="3.7")
def docs(session):
    session.install("sphinx")
    session.install(".")
    session.chdir("docs")
    session.run("sphinx-build", "-W", "-b", "doctest", "source", "build")
    session.run("sphinx-build", "-W", "-b", "html", "source", "build")


@nox.session(python=PYTHON_VERSIONS)
def omegaconf(session):
    session.install("--upgrade", "setuptools", "pip")
    session.install(".")
    session.install("pytest")
    session.run("pytest")


# code coverage runs with python 3.6
@nox.session(python="3.6")
def coverage(session):
    session.install("--upgrade", "setuptools", "pip")
    session.install("coverage", "pytest")
    session.run("pip", "install", ".[coverage]", silent=True)
    session.run("coverage", "erase")
    session.run("coverage", "run", "--append", "-m", "pytest", silent=True)
    # Increase the fail_under as coverage improves
    session.run("coverage", "report", "--fail-under=95")
    session.run("coverage", "erase")

    # report to coveralls
    session.run("coveralls", success_codes=[0, 1])


@nox.session(python="3.6")
def lint(session):
    session.install("--upgrade", "setuptools", "pip")
    session.run("pip", "install", ".[lint]", silent=True)
    session.run("flake8")

    session.install("black")
    # if this fails you need to format your code with black
    session.run("black", "--check", ".")
