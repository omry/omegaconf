# Vendored dependencies

This folder contains libraries that are vendored from third party packages.
To add or modify a vendored library, just add or edit the corresponding dependency
in `vendor.txt`, and then run the `build_helpers/get_vendored.py` script.

**NOTE** all files in this folder apart from `__init__.py`, `vendor.txt`  and `README.txt` are
dynamically generated; any manual modifications will be lost when running the `get_vendored` script
