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

#### Submitting a PR

When submitting a PR please ensure that it includes:
- automated tests for any new feature or bugfix
- documentation for any user-facing change
- a one-line news fragment under the `news` folder (valid extensions are: `.feature`, `.bugfix`, `.api_change`, `.docs`, `.misc`)

#### Modifying the Jupyter notebook

In order to change the Jupyter notebook you first need to open it with `jupyter notebook`.
Change the cell you want and then, execute it so the expected output is shown.
Note that the output after you execute the cell is saved as expected ouput for further
testing.

In case that the in[number] of cells aren't in order you should go to the
kernel in the toolbar and restart it.

#### Releasing a version

OmegaConf uses GitHub Actions with PyPI Trusted Publishers for automated releases.

**Prerequisites (one-time setup):**
1. Configure Trusted Publisher on PyPI (project maintainers only):
   - Go to https://pypi.org/manage/project/omegaconf/settings/publishing/
   - Add GitHub as a trusted publisher with:
     - Owner: `omry` (or your organization)
     - Repository name: `omegaconf`
     - Workflow name: `publish.yml`
     - Environment name: `pypi-publish`

2. Create the `pypi-publish` environment in GitHub repository settings (optional but recommended):
   - Add protection rules (e.g., require manual approval)

**Release process:**
1. Update version in `omegaconf/version.py`
2. Update `NEWS.md` with release notes (use `towncrier build --version X.Y.Z`)
3. Commit changes and push to main branch
4. Create a new release on GitHub:
   - Go to https://github.com/omry/omegaconf/releases/new
   - Create a new tag (e.g., `v2.4.0`)
   - Add release notes
   - Publish release
5. GitHub Actions will automatically build and publish to PyPI

The workflow handles:
- Installing Java (required for ANTLR parser generation)
- Building source distribution and wheel
- Verifying artifacts with `twine check`
- Publishing to PyPI via Trusted Publishers (no API tokens needed)

**Manual release (fallback):**
If you need to publish manually:
```bash
rm -rf dist/ omegaconf.egg-info/
python -m build
twine check dist/*
twine upload dist/*
```
