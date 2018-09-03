import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()
'''
Instructions:
# Build:
rm -rf dist/ omegaconf.egg-info/
python3 setup.py sdist bdist_wheel
# Upload:
twine upload dist/*
'''
setuptools.setup(
    name="omegaconf",
    version="1.0.1",
    author="Omry Yadan",
    author_email="omry@yadan.net",
    description="A flexible configuration library",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/omry/omegaconf",
    packages=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
    ],
)
