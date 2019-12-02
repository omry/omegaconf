import sys

__version__ = "1.5.0rc1"

if sys.version_info < (3, 6):
    raise ImportError(
        """OmegaConf 1.5 and above is compatible with Python 3.6 and newer.
You have the following options:
1. Upgrade to Python 3.6 or newer.
   This is highly recommended. new features will not be added to OmegaConf 1.4.
2. Continue using OmegaConf 1.4:
    You can pip install 'OmegaConf<1.5' to do that.
"""
    )
