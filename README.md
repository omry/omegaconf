
# OmegaConf
|  | Description |
| --- | --- |
| Project | [![PyPI version](https://badge.fury.io/py/omegaconf.svg)](https://badge.fury.io/py/omegaconf)[![downloads](https://img.shields.io/pypi/dm/omegaconf.svg)](https://pypistats.org/packages/omegaconf) ![PyPI - Python Version](https://img.shields.io/pypi/pyversions/omegaconf.svg) |
| Code quality| [![CircleCI](https://img.shields.io/circleci/build/github/omry/omegaconf?logo=s&token=5de2f8dc2a0dd78438520575431aa533150806e3)](https://circleci.com/gh/omry/omegaconf)[![Coverage Status](https://coveralls.io/repos/github/omry/omegaconf/badge.svg)](https://coveralls.io/github/omry/omegaconf)[![Total alerts](https://img.shields.io/lgtm/alerts/g/omry/omegaconf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/omry/omegaconf/alerts/)[![Language grade: Python](https://img.shields.io/lgtm/grade/python/g/omry/omegaconf.svg?logo=lgtm&logoWidth=18)](https://lgtm.com/projects/g/omry/omegaconf/context:python)|
| Docs and support |[![Documentation Status](https://readthedocs.org/projects/omegaconf/badge/?version=latest)](https://omegaconf.readthedocs.io/en/latest/?badge=latest)[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/omry/omegaconf/master?filepath=docs%2Fnotebook%2FTutorial.ipynb)[![](https://img.shields.io/badge/zulip-join_chat-brightgreen.svg)](https://hydra-framework.zulipchat.com)|


OmegaConf is a hierarchical configuration system, with support for merging configurations from multiple sources (YAML config files, dataclasses/objects and CLI arguments)
providing a consistent API regardless of how the configuration was created.

## Releases
### Release candidate (2.0)
OmegaConf 2.0 is coming, this is a real release candidate and you should feel free to use it.
Ths reason that this is still marked as release candidate is that this is a very big release and I want it to see some more use before officially releasing it.
No additional changes are planned for 2.0, please report any issues.

[What's new in OmegaConf 2.0](https://github.com/omry/omegaconf/releases/tag/2.0.0rc28).

[2.0 Documentation](https://omegaconf.readthedocs.io/en/latest/?badge=latest).

[Source code](https://github.com/omry/omegaconf/tree/master)

Install with `pip install --upgrade --pre omegaconf`

### Old stable (1.4)
This is the old stable version, despite it being stable - many bugs 1.4 have been fixed in 2.0.
Use this only if you cannot use 2.0 for some reason.

[1.4 Documentation](https://omegaconf.readthedocs.io/en/1.4_branch/).

[Source code](https://github.com/omry/omegaconf/tree/1.4_branch)

Install with `pip install omegaconf`

## Live tutorial
Run the live tutorial : [![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/omry/omegaconf/master?filepath=docs%2Fnotebook%2FTutorial.ipynb)
