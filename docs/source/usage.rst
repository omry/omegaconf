.. testsetup:: *

    from omegaconf import OmegaConf

.. testsetup:: loaded

    from omegaconf import OmegaConf
    conf = OmegaConf.from_filename('source/example.yaml')

Usage
=====

Installation
^^^^^^^^^^^^
Just pip install::

    pip install omegaconf


Basic example
^^^^^^^^^^^^^
We will use this simple **example.yaml** file in the example below.

.. include:: example.yaml
   :code: yaml

Creating:
---------
.. doctest::

    >>> from omegaconf import OmegaConf
    >>>
    >>> # Empty config
    >>> conf = OmegaConf.create()
    >>> conf
    {}

    >>> # from dictionary
    >>> conf = OmegaConf.create(dict(key='value'))
    >>> print(conf.pretty())
    key: value
    <BLANKLINE>
    >>> # from list
    >>> conf = OmegaConf.create([1,2,3])
    >>> print(conf.pretty())
    - 1
    - 2
    - 3
    <BLANKLINE>
    >>> # From a yaml file:
    >>> conf = OmegaConf.load('source/example.yaml')
    >>> print(conf.pretty())
    log:
      file: log.txt
      rotation: 3600
    server:
      port: 80
    <BLANKLINE>


Creating from CLI arguments
---------------------------
OmegaConf support creating a configuration tree from a dot separated list.
This is typically used to override values from the command line arguments.
from_cli() will parse anything in sys.argv.
Note that if you want to use this with a CLI parser, it will have to clear anything it already parsed from
sys.argv before you initialize the conf from_cli().

.. doctest::

    >>> dot_list = ['server.port=82', 'log.file=log2.txt']
    >>> conf = OmegaConf.from_cli(dot_list)
    >>> print(conf.pretty())
    log:
      file: log2.txt
    server:
      port: 82
    <BLANKLINE>


Reading:
---------------

.. doctest:: loaded

    >>> # Object style access
    >>> conf.server.port
    80

    >>> # Map style access
    >>> conf['log']
    {'file': 'log.txt', 'rotation': 3600}

    >>> # with default value
    >>> conf.missing_key or 'a default value'
    'a default value'

    >>> # another style for default value
    >>> conf.get('missing_key', 'a default value')
    'a default value'


Changing:
--------------------

.. doctest:: loaded

    >>> # Changing existing keys
    >>> conf.server.port = 81
    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"
    >>> # Or new sections
    >>> conf.database = {'hostname': 'database01', 'port': 3306}






