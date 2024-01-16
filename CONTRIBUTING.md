### Setup development

#### Essentials

We recomend using Conda or pyenv to create a new environment.

Example with Conda: `conda create -n omegaconf38 python=3.8 -qy`

Activate your new conda environment: `conda activate omegaconf38`

Install development dependencies: `pip install -r requirements/dev.txt -e .`

Optionally install commit hooks: `pre-commit install`

pre-commit will verify your code lints cleanly when you commit. You can use `git commit -n` to skip the pre-commit hook for a specific commit.

##### Mac
OmegaConf is compatible with Python 3.8 and newer.

One way to install multiple Python versions on Mac to to use pyenv.
The instructions [here](https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/MAC_SETUP.md)
will provide full details. It shows how to use pyenv on Mac to install multiple versions of Python and have
pyenv make specific versions available in specific directories automatically.
This plays well with Conda, which supports a single Python version. Pyenv will provide the versions not installed by Conda (which are used when running nox).

#### Testing
Run tests directly with `pytest`.

Run all CI tests with nox:

```
$ nox -l
Sessions defined in /home/omry/dev/omegaconf/noxfile.py:
* omegaconf-3.8
* omegaconf-3.9
* omegaconf-3.10
* docs
* coverage-3.8
* coverage-3.9
* coverage-3.10
* lint-3.8
* lint-3.9
* lint-3.10
* test_jupyter_notebook-3.8
* test_jupyter_notebook-3.9
* test_jupyter_notebook-3.10
```

To run a specific session use `-s`, for example `nox -s lint` will run linting


OmegaConf is formatted with black, to format your code automatically use `black .`

Imports are sorted using isort, use `isort .` to sort all imports prior to pushing.

To build the docs execute `nox -s docs` or `make`(inside docs folder). Make gives you different options, for example, you can build the docs as html files with `make html`. Once the docs are built you can open `index.html` in the build directory to view the generated docs with your browser.

#### Modifying the Jupyter notebook

In order to change the Jupyter notebook you first need to open it with `jupyter notebook`.
Change the cell you want and then, execute it so the expected output is shown.
Note that the output after you execute the cell is saved as expected ouput for further
testing.

In case that the in[number] of cells aren't in order you should go to the
kernel in the toolbar and restart it.

#### Releasing a version

```
rm -rf dist/ omegaconf.egg-info/
python setup.py sdist bdist_wheel
twine upload dist/*
```
