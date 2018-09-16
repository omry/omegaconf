.. _creation:

Creating
========

.. testsetup:: *

    from omegaconf import OmegaConf
    import io
    import os

Empty config
------------
.. doctest::

    >>> conf = OmegaConf.empty()
    >>> conf.a = {'key' :'value'}
    >>> conf
    {'a': {'key': 'value'}}

From filename
-------------
.. doctest::

    >>> conf = OmegaConf.from_filename('source/example.yaml')

From file
---------


.. doctest::

    >>> file = io.open('source/example.yaml', 'r')
    >>> conf = OmegaConf.from_file(file)


From CLI arguments
------------------
from_cli() will parse anything in sys.argv.
Note that if you want to use this with a CLI parser, it will have to clear anything it already parsed from
sys.argv before you initialize the conf from_cli().

.. doctest::

    >>> conf = OmegaConf.from_cli()


From environment
----------------
Environment keys are prefixed by default with "OC.", you can change the prefix.
This requires a whitelist of what you want to access through the environment.
The reason for the whitelist is that the environment contains unparseable YAML in many cases,
which cauases issues when trying to initialize this config.

.. doctest::

    >>> # Simulate environment variable
    >>> os.environ['OC.a.b'] = '1'
    >>> conf = OmegaConf.from_env()
    >>> conf.a.b
    1
