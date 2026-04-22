# OmegaConf pydevd Plugin

`omegaconf-pydevd` provides the optional `pydevd` plugin for OmegaConf objects.

This debugger integration was split out of the main `omegaconf` package so that
installing OmegaConf no longer adds modules under the global `pydevd_plugins`
namespace by default.

The plugin improves debugger inspection of OmegaConf objects, including handling
of interpolations and missing values.

## Installation

```bash
pip install omegaconf-pydevd
```

This package depends on the matching `omegaconf` version and installs the
`pydevd_plugins.extensions.pydevd_plugin_omegaconf` module.

## Development From Source

From a local checkout, install OmegaConf itself in editable mode:

```bash
pip install -r requirements/dev.txt -e .
```

Then install the pydevd plugin package from this checkout:

```bash
python setup_pydevd.py develop
```
