.. testsetup:: *

    from omegaconf import OmegaConf

Usage
=====

Installation
^^^^^^^^^^^^
Just pip install::

    pip install omegaconf


Creating:
---------
You can create an empty config:

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> conf = OmegaConf.create()
    >>> conf
    {}

Or a config from a dictionary

.. doctest::

    >>> conf = OmegaConf.create(dict(k='v',list=[1,2,dict(a='1',b='2')]))
    >>> print(conf.pretty())
    k: v
    list:
    - 1
    - 2
    - a: '1'
      b: '2'
    <BLANKLINE>

Or a config from a list

.. doctest::

    >>> conf = OmegaConf.create([1, 2, 3, dict(a=10, b=12, c=dict(d=10))])
    >>> print(conf.pretty())
    - 1
    - 2
    - 3
    - a: 10
      b: 12
      c:
        d: 10
    <BLANKLINE>

Or from from a yaml file:

.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> print(conf.pretty())
    log:
      file: log.txt
      rotation: 3600
    server:
      port: 80
    users:
    - user1
    - user2
    - user3
    <BLANKLINE>

Or even a yaml string:

.. doctest::

    >>> conf = OmegaConf.create("a: b\nb: c\nlist:\n- item1\n- item2\n")
    >>> print(conf.pretty())
    a: b
    b: c
    list:
    - item1
    - item2
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
    >>> cliconf = OmegaConf.from_cli(dot_list)
    >>> print(cliconf.pretty())
    log:
      file: log2.txt
    server:
      port: 82
    <BLANKLINE>


Accessing:
---------------

For dictionary nodes, you can use object style or map style access.
For lists you can use subscript:
.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> conf.server.port
    80
    >>> conf['log'].rotation
    3600
    >>> conf.missing_key or 'a default value'
    'a default value'
    >>> conf.get('missing_key', 'a default value')
    'a default value'
    >>> # Changing existing keys
    >>> conf.server.port = 81
    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"
    >>> # Or new sections
    >>> conf.database = {'hostname': 'database01', 'port': 3306}






