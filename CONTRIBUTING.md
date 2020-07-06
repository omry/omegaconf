### Setup development

#### Essentials

We recomend using Conda or pyenv to create a new environment.

Example with Conda: `conda create -n omegaconf38 python=3.8`

Activate your new conda environment: `conda activate omegaconf38`

Install development dependencies: `pip install -r requirements/dev.txt -e .`

Optionally install commit hooks: `pre-commit install`

pre-commit will verify your code lints cleanly when you commit. You can use `git commit -n` to skip the pre-commit hook for a specific commit.

#### Testing
Run tests directly with `pytest`.

Run all CI tests with nox:

```
$ nox -l
Sessions defined in /home/omry/dev/omegaconf/noxfile.py:
* omegaconf-3.6
* omegaconf-3.7
* omegaconf-3.8
* docs
* coverage-3.6
* coverage-3.7
* coverage-3.8
* lint-3.6
* lint-3.7
* lint-3.8
* test_jupyter_notebook-3.6
* test_jupyter_notebook-3.7
* test_jupyter_notebook-3.8
```
To run a specific session use `-s`, for example `nox -s lint` will run linting


OmegaConf is formatted with black, to format your code automatically use `black .`

Imports are sorted using isort, use `isort .` to sort all imports prior to pushing.  

To build the docs execute `nox -s docs` or `make`(inside docs folder). Make gives you different options, for example, you can build the docs as html files with `make html`. Once the docs are built you can open `index.html` in the build directory to view the generated docs with your browser.


#### Releasing a version

```
rm -rf dist/ omegaconf.egg-info/
python setup.py sdist bdist_wheel
twine upload dist/*
```
