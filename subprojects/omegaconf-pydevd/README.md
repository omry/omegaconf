# OmegaConf pydevd Plugin

`omegaconf-pydevd` provides the optional `pydevd` plugin for OmegaConf objects.

This debugger integration is packaged separately from the main `omegaconf`
distribution so that the global `pydevd_plugins` namespace is only installed on
systems that explicitly opt into it.

## Installation

```bash
pip install omegaconf-pydevd
```

## Debugger Demo

Use [examples/debug_demo.py](./examples/debug_demo.py) to inspect OmegaConf
objects in the debugger with `omegaconf-pydevd` installed.

Set a breakpoint on `print(cfg)` and inspect:

- `cfg`
- `cfg.greeting`
- `cfg.subprojects`
- `cfg.project`

With `omegaconf-pydevd` installed:

- missing fields render as debugger values instead of surfacing a debugger-time
  exception while inspecting them
- interpolations are shown more clearly, including their resolved values

### Example Rendering

![OmegaConf pydevd debugger rendering](/subprojects/omegaconf-pydevd/docs/with-plugin.png "OmegaConf pydevd debugger rendering")

## Resolver Mode

Use the `OC_PYDEVD_RESOLVER` environment variable to select which resolver to
install:

- `USER`: default behavior, useful when debugging OmegaConf objects
- `DEV`: useful when debugging OmegaConf itself and inspecting its internal
  data model
- `DISABLE`: disable the OmegaConf resolver

Example:

```bash
OC_PYDEVD_RESOLVER=DEV python your_program.py
```

## Development

From this repository root:

```bash
pip install -r requirements/dev.txt -e .
pip install -e subprojects/omegaconf-pydevd
pytest subprojects/omegaconf-pydevd/tests
```
