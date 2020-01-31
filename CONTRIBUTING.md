It is recommended that you develop OmegaConf is a virtualenv or similar (pyenv, conda).
To set up for development:

`pip install -r requirements/dev.txt -e .`

Install commit hooks:

`pre-commit install`

Run tests directly with `pytest`.
Run all CI tests with nox:

```
$ nox -l
Sessions defined in /home/omry/dev/omegaconf/noxfile.py:
* docs
* omegaconf-2.7
* omegaconf-3.5
* omegaconf-3.6
* omegaconf-3.7
* coverage
* lint
```
To run a specific session use `-s`, for example `nox -s lint` will run linting

OmegaConf is formatted with black, to format your code automatically use `black .`

Imports are sorted using isort, use `isort -y` to sort all imports prior to pushing.