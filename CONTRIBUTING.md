### Setup development

#### Essentials

We reccomend using conda or pyenv to create a new environment. You can skip to install python 
if you prefer. We'll use conda as an example:

`conda create -n myenv python=3.8`

Now that you created a new environment you can select it with:

`conda activate myenv`

Install python (if you didn't follow the previous steps)

`pip install -r requirements/dev.txt -e .`

Install commit hooks:

`pre-commit install`

pre-commit will verify your code lints cleanly when you commit. You can use `git commit -n` to skip the pre-commit hook for a specific commit.

#### Testing
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

To build the docs execute `nox -s docs` or `make`(inside docs folder). Make gives you different options, for example, you can build the docs as html files with `make html`. Once the docs are built you can open `index.html` in the build directory to view the generated docs with your browser.


#### Building the package

`python setup.py install`
