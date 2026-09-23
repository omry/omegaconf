# OmegaConf

> [!IMPORTANT]
> **OmegaConf project transition:** OmegaConf moved from the `omry` GitHub account
> to [`hydra-ecosystem`](https://github.com/hydra-ecosystem). The repository moved
> with its history, issues, and pull requests intact. OmegaConf remains BSD
> 3-Clause licensed. No action is required from OmegaConf users. Contributors
> should use the [new repository](https://github.com/hydra-ecosystem/omegaconf)
> for issues and pull requests.

|  | Description |
| --- | --- |
| Project | [![PyPI version](https://badge.fury.io/py/omegaconf.svg)](https://badge.fury.io/py/omegaconf)[![Downloads](https://pepy.tech/badge/omegaconf/month)](https://pepy.tech/project/omegaconf)![Python](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13%20%7C%203.14-blue) |
| Code quality| [![CircleCI](https://dl.circleci.com/status-badge/img/gh/hydra-ecosystem/omegaconf/tree/main.svg?style=svg)](https://app.circleci.com/pipelines/github/hydra-ecosystem/omegaconf?branch=main)[![Coverage Status](https://coveralls.io/repos/github/hydra-ecosystem/omegaconf/badge.svg)](https://coveralls.io/github/hydra-ecosystem/omegaconf)|
| Docs, support, and ecosystem |[![Documentation Status](https://readthedocs.org/projects/omegaconf/badge/?version=2.0_branch)](https://omegaconf.readthedocs.io/en/2.3_branch/)[![Binder](https://mybinder.org/badge_logo.svg)](https://mybinder.org/v2/gh/hydra-ecosystem/omegaconf/main?filepath=docs%2Fnotebook%2FTutorial.ipynb)[![Zulip chat](https://img.shields.io/badge/chat-Zulip-2e77d0?logo=zulip)](https://hydra-framework.zulipchat.com/)[![ecosystem: cli.dev](https://cli.dev/img/badges/cli-dev-ecosystem.svg)](https://cli.dev)|
| Backlog | [![Backlog Atlas dashboard](https://omry.github.io/backlog-atlas/badge.svg)](https://omry.github.io/backlog-atlas/) |


OmegaConf is a hierarchical configuration system, with support for merging configurations from multiple sources (YAML config files, dataclasses/objects and CLI arguments)
providing a consistent API regardless of how the configuration was created.

## Optional subprojects

- [`omegaconf-pydevd`](./subprojects/omegaconf-pydevd/README.md): optional `pydevd` debugger plugin for inspecting OmegaConf objects in supported debuggers.

## Releases

### Upcoming (2.4.0.dev)
OmegaConf 2.4.0.dev is the upcoming development version.
* [Documentation](https://omegaconf.readthedocs.io/en/latest/)
* [Source code](https://github.com/hydra-ecosystem/omegaconf/tree/main)

Install with `pip install --upgrade --pre omegaconf`

### Stable (2.3)
OmegaConf 2.3 is the current stable version.
* [What's new](https://github.com/hydra-ecosystem/omegaconf/releases/tag/v2.3.0)
* [Documentation](https://omegaconf.readthedocs.io/en/2.3_branch/)
* [Source code](https://github.com/hydra-ecosystem/omegaconf/tree/2.3_branch)

Install with `pip install --upgrade omegaconf`
