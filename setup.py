"""
OmegaConf setup
    Instructions:
    # Build:
    rm -rf dist/ omegaconf.egg-info/
    python3 setup.py sdist bdist_wheel
    # Upload:
    python3 -m twine upload dist/*
"""
import setuptools

with open("README.md", "r") as fh:
    LONG_DESC = fh.read()
    setuptools.setup(
        name="omegaconf",
        version="1.3.0",
        author="Omry Yadan",
        author_email="omry@yadan.net",
        description="A flexible configuration library",
        long_description=LONG_DESC,
        long_description_content_type="text/markdown",
        setup_requires=["pytest-runner"],
        tests_require=["pytest"],
        url="https://github.com/omry/omegaconf",
        keywords='yaml configuration config',
        packages=['omegaconf'],
        classifiers=[
            "Programming Language :: Python :: 2.7",
            "Programming Language :: Python :: 3.5",
            "Programming Language :: Python :: 3.6",
            "Programming Language :: Python :: 3.7",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=['six', 'PyYAML'],
        # Install development dependencies with
        # pip install -e ".[dev]"
        extras_require={
            "dev": [
                "nox",
                "pre-commit",
                "pytest",
                "twine",
                "coveralls",
                "black",
                "flake8",
            ],
            "coverage": [
                "coveralls",
            ],
            "lint": [
                "black",
                "flake8",
            ]
        },
    )
