.. testsetup:: *

    from omegaconf import OmegaConf
    import os

Installation
------------

Just pip install::

    pip install omegaconf


Creating
--------
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

OmegaConf support creating a configuration tree from a dot separated list.
This is typically used to override values using command line arguments.
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


Access and manipulation
-----------------------

For dictionary nodes, you can use object style or map style access.
For lists you can use subscript:
.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> conf.server.port
    80
    >>> conf['log'].rotation
    3600
    >>> # items in list
    >>> conf.users[0]
    user1
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

String interpolation
--------------------
Built-in types
^^^^^^^^^^^^^^
OmegaConf supports string interpolation.
The basic form supports referencing other nodes in the configuration tree.
Additionally, environment variable interpolation is supported.

.. include:: interpolation.yaml
   :code: yaml

Let's load it and take a look:

.. doctest::

    >>> conf = OmegaConf.load('source/interpolation.yaml')
    >>> # client.server_port type is int, just like server.port
    >>> conf.client.server_port
    80
    >>> # client.url type is string because we are constructing a string
    >>> conf.client.url
    'http://localhost:80/'
    >>> os.environ['user'] = 'omry'
    >>> conf.user.name
    'omry'
    >>> conf.user.home
    '/home/omry'

Plugable resolves
^^^^^^^^^^^^^^^^^
You can add easily add your own resolvers to add additional interpolation types.
let's say we want a resolver that adds 10 the the given value.
The value 990 will be passed to the plus_10 lambda, and the int 1000 will be returned.

.. doctest::

    >>> OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000


Merging configurations
----------------------
You can merge configurations, here are a few examples where you might want to do that:

- Override values in your in your configuration from another file and/or command line arguments
- Composing your configuration dynamically, based on user provided inputs, and access it through a single object.

Now let's try overriding conf1 above with parameters from the command line:
We will simulate command line arguments by setting sys.argv.

**example.yaml** file:

.. include:: example.yaml
   :code: yaml

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> import sys
    >>> conf = OmegaConf.load('source/example.yaml')
    >>> # Simulate command line arguments
    >>> sys.argv = ['program.py', 'server.port=82', 'users.0=omry']
    >>> cli = OmegaConf.from_cli()
    >>> conf = OmegaConf.merge(conf, cli)
    >>> conf.server.port
    82
    >>> conf.users
    ['omry', 'user2']

OmegaConf.merge() can merge one or more configuration objects.