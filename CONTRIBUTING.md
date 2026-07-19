### Setup development

#### Essentials

Use a repo-local virtual environment in `.venv`.

Create the environment:

```bash
python3 -m venv .venv
```

Activate it:

```bash
source .venv/bin/activate
```

Install development dependencies:

```bash
python -m pip install --upgrade pip setuptools
python -m pip install -r requirements/dev.txt -e .
```

The optional `omegaconf-pydevd` debugger plugin lives in
`subprojects/omegaconf-pydevd/` and has its own packaging and tests.

Optionally install commit hooks: `pre-commit install`

pre-commit will verify your code lints cleanly when you commit. You can use `git commit -n` to skip the pre-commit hook for a specific commit.

##### Mac
OmegaConf is compatible with Python 3.8 and newer.

One way to install multiple Python versions on Mac is to use pyenv.
The instructions [here](https://github.com/GoogleCloudPlatform/python-docs-samples/blob/master/MAC_SETUP.md)
will provide full details. It shows how to use pyenv on Mac to install multiple versions of Python and have
pyenv make specific versions available in specific directories automatically.
After selecting the Python version for this checkout, create `.venv` with that interpreter.

#### Testing
Run tests directly with `pytest`.

Run all CI tests with nox:

```
$ nox -l
Sessions defined in /home/omry/dev/omegaconf/noxfile.py:
* omegaconf-3.10
* docs
* coverage-3.10
* lint-3.10
* test_jupyter_notebook-3.10
```

To run a specific session use `-s`, for example `nox -s lint` will run linting.

OmegaConf uses Ruff for formatting, linting, and import sorting. Run
`ruff format .` to format code and `ruff check .` to lint it. Use
`ruff check --fix .` to apply safe fixes, including import sorting.

To build the docs execute `nox -s docs` or `make`(inside docs folder). Make gives you different options, for example, you can build the docs as html files with `make html`. Once the docs are built you can open `index.html` in the build directory to view the generated docs with your browser.

#### Submitting a PR

We welcome your pull requests.

When submitting a PR please ensure that it includes:
- automated tests for any new feature or bugfix
- documentation for any user-facing change
- a one-line news fragment under the `news` folder for any non-trivial
  user-visible change. Use the issue or pull request number as the filename,
  with one of these extensions: `.feature`, `.bugfix`, `.api_change`, `.docs`,
  `.misc` (for example, `news/1234.bugfix`).

Developer-only tooling, repository maintenance, and CI-only changes do not need
a news fragment unless they affect the shipped product experience.

For any non-trivial change, please open an issue or design discussion and wait
for maintainer feedback before starting substantial implementation work. Pull
requests in these areas should link to the issue or discussion where the
direction was agreed. Pull requests without prior design alignment may be
redirected to discussion before implementation review.

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
   - Repeat for the `omegaconf-pydevd` PyPI project if you want the plugin
     package published by the same workflow.

2. Configure Trusted Publisher for dev releases on PyPI (project maintainers only):
   - Add GitHub as a trusted publisher with:
     - Owner: `omry` (or your organization)
     - Repository name: `omegaconf`
     - Workflow name: `publish_dev.yml`
     - Environment name: `pypi-publish-dev`
   - Repeat for the `omegaconf-pydevd` PyPI project if you want dev plugin
     releases published too.

3. Create the `pypi-publish` environment in GitHub repository settings (optional but recommended):
   - Add protection rules (e.g., require manual approval)

4. Create the `pypi-publish-dev` environment in GitHub repository settings:
   - Allow publishing from the development branch you use for dev releases
     (for example `main`)
   - Add protection rules (e.g., require manual approval)

**Official release process:**
1. Bump the version with `bump-my-version`, for example:
   - `bump-my-version bump patch`
   - `bump-my-version bump minor`
   - `bump-my-version bump --new-version X.Y.Z`
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
- Building source distribution and wheel for both `omegaconf` and
  `omegaconf-pydevd`
- Verifying artifacts for both packages with `twine check`
- Publishing to PyPI via Trusted Publishers (no API tokens needed)

**Development release process:**
1. Ensure the dev version to publish is committed and pushed to the branch you
   use for dev releases.
2. Run the `Publish dev release to PyPI` workflow manually from GitHub Actions,
   or run `gh workflow run publish_dev.yml --ref <branch>`.
3. Approve the `pypi-publish-dev` environment if required.
4. After the release publishes successfully, advance to the next dev version
   with `bump-my-version bump pre_n`.
5. Commit and push the version bump.

**Manual release (fallback):**
If you need to publish manually:
```bash
rm -rf dist/ omegaconf.egg-info/
python -m build
python -m build subprojects/omegaconf-pydevd
twine check dist/* subprojects/omegaconf-pydevd/dist/*
twine upload dist/* subprojects/omegaconf-pydevd/dist/*
```
