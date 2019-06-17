.. testsetup:: *

    from omegaconf import OmegaConf
    import os
    os.environ['user'] = 'omry'

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

Or a config from a dictionary:

.. doctest::

    >>> conf = OmegaConf.create(dict(k='v',list=[1,dict(a='1',b='2')]))
    >>> print(conf.pretty())
    k: v
    list:
    - 1
    - a: '1'
      b: '2'
    <BLANKLINE>

Or a config from a list:

.. doctest::

    >>> conf = OmegaConf.create([1, dict(a=10, b=dict(a=10))])
    >>> # Output is identical to the yaml file
    >>> print(conf.pretty())
    - 1
    - a: 10
      b:
        a: 10
    <BLANKLINE>

Or from from a yaml file:

.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> print(conf.pretty())
    log:
      file: ???
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

OmegaConf supports creating a configuration tree from a dot separated list:

This is typically used to override values using command line arguments.
from_cli() will parse anything in sys.argv.
Note that if you want to use this with a CLI parser, it will have to clear anything it already parsed from
sys.argv before you initialize the conf from_cli().

.. doctest::

    >>> dot_list = ['server.port=82', 'log.file=log2.txt']
    >>> cli_conf = OmegaConf.from_cli(dot_list)
    >>> print(cli_conf.pretty())
    log:
      file: log2.txt
    server:
      port: 82
    <BLANKLINE>


Access and manipulation
-----------------------

Input yaml file:

.. literalinclude:: example.yaml
   :language: yaml

.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> # object style access of dictionary elements
    >>> conf.server.port
    80

    >>> # dictionary style access
    >>> conf['log'].rotation
    3600

    >>> # items in list
    >>> conf.users[0]
    'user1'

    >>> # Changing existing keys
    >>> conf.server.port = 81

    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"

    >>> # Adding a new dictionary
    >>> conf.database = {'hostname': 'database01', 'port': 3306}

    >>> # providing default values
    >>> conf.missing_key or 'a default value'
    'a default value'
    >>> conf.get('missing_key', 'a default value')
    'a default value'

Accessing fields with the value *???* will cause a MissingMandatoryValue exception.
Use this to indicate that the value must be set before accessing.


String interpolation
--------------------
Built-in resolvers
^^^^^^^^^^^^^^^^^^
OmegaConf supports string interpolation.
The basic form supports referencing other nodes in the configuration tree.
Additionally, environment variable interpolation is supported.

Input yaml file:

.. include:: interpolation.yaml
   :code: yaml


Interpolations are evaluated lazily on field access.

.. doctest::

    >>> conf = OmegaConf.load('source/interpolation.yaml')

    >>> # Primitive interpolations type is inherited from the referenced value
    >>> # Composite interpolations type is always string
    >>> conf.client.server_port
    80
    >>> conf.client.url
    'http://localhost:80/'

    >>> conf.user.name
    'omry'
    >>> conf.user.home
    '/home/omry'

Plugable resolvers
^^^^^^^^^^^^^^^^^^^
You can add additional interpolation types using custom resolvers.
This example creates a resolver that adds 10 the the given value.

.. doctest::

    >>> OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000


Merging configurations
----------------------
Merging configurations enables the use of logical components instead of a single config file for each
variation of your task.

Machine learning experiment example:

   OmegaConf.merge(base_config, model_config, optimizer_config, dataset_config)

Web server configuration example:

   OmegaConf.merge(server_config, plugin1_config, site1_config, site2_config)

Later configurations may add new values, override previous values, or even append to lists.

**example.yaml** file:

.. include:: example.yaml
   :code: yaml

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> import sys
    >>> conf = OmegaConf.load('source/example2.yaml')
    >>> # Simulate command line arguments
    >>> sys.argv = ['program.py', 'server.port=82']
    >>> cli = OmegaConf.from_cli()
    >>> # Overlay cli on top of conf
    >>> conf = OmegaConf.merge(conf, cli)
    >>> conf.server.port
    82
    >>> # TODO: list merge example


