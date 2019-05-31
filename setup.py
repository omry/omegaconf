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
        version="1.0.14",
        author="Omry Yadan",
        author_email="omry@yadan.net",
        description="A flexible configuration library",
        long_description=LONG_DESC,
        long_description_content_type="text/markdown",
        url="https://github.com/omry/omegaconf",
        keywords='yaml configuration config',
        packages=setuptools.find_packages(),
        classifiers=[
            "Programming Language :: Python :: 3",
            "License :: OSI Approved :: BSD License",
            "Operating System :: OS Independent",
        ],
        install_requires=['six', 'PyYAML']
    )
