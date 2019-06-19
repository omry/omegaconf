.. testsetup:: *

    from omegaconf import OmegaConf
    import os
    import sys
    os.environ['USER'] = 'omry'

.. testsetup:: loaded

    from omegaconf import OmegaConf
    conf = OmegaConf.load('source/example.yaml')

Installation
------------

Just pip install::

    pip install omegaconf

Creating
--------
Empty
^^^^^

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> conf = OmegaConf.create()
    >>> print(conf.pretty())
    {}
    <BLANKLINE>

From a dictionary
^^^^^^^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.create(dict(k='v',list=[1,dict(a='1',b='2')]))
    >>> print(conf.pretty())
    k: v
    list:
    - 1
    - a: '1'
      b: '2'
    <BLANKLINE>

From a list
^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.create([1, dict(a=10, b=dict(a=10))])
    >>> print(conf.pretty())
    - 1
    - a: 10
      b:
        a: 10
    <BLANKLINE>

From a yaml file
^^^^^^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> # Output is identical to the yaml file
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


From a yaml string
^^^^^^^^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.create("a: b\nb: c\nlist:\n- item1\n- item2\n")
    >>> print(conf.pretty())
    a: b
    b: c
    list:
    - item1
    - item2
    <BLANKLINE>

From a dot-list
^^^^^^^^^^^^^^^^

.. doctest::

    >>> dot_list = ["a.aa.aaa=1", "a.aa.bbb=2", "a.bb.aaa=3", "a.bb.bbb=4"]
    >>> conf = OmegaConf.from_dotlist(dot_list)
    >>> print(conf.pretty())
    a:
      aa:
        aaa: 1
        bbb: 2
      bb:
        aaa: 3
        bbb: 4
    <BLANKLINE>

From command line arguments
^^^^^^^^^^^^^^^^^^^^^^^^^^^

To parse the content of sys.arg:

.. doctest::

    >>> # Simulating command line arguments
    >>> sys.argv = ['your-program.py', 'server.port=82', 'log.file=log2.txt']
    >>> conf = OmegaConf.from_cli()
    >>> print(conf.pretty())
    log:
      file: log2.txt
    server:
      port: 82
    <BLANKLINE>


Access and manipulation
-----------------------

Input yaml file for this section:

.. literalinclude:: example.yaml
   :language: yaml

Access
^^^^^^

.. doctest:: loaded

    >>> # object style access of dictionary elements
    >>> conf.server.port
    80

    >>> # dictionary style access
    >>> conf['log']['rotation']
    3600

    >>> # items in list
    >>> conf.users[0]
    'user1'


Manipulation
^^^^^^^^^^^^
.. doctest:: loaded

    >>> # Changing existing keys
    >>> conf.server.port = 81

    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"

    >>> # Adding a new dictionary
    >>> conf.database = {'hostname': 'database01', 'port': 3306}


Default values
^^^^^^^^^^^^^^
You can provided default values directly in the accessing code:

.. doctest:: loaded

    >>> # providing default values
    >>> conf.missing_key or 'a default value'
    'a default value'

    >>> conf.get('missing_key', 'a default value')
    'a default value'

Mandatory values
^^^^^^^^^^^^^^^^
Use the value ??? to indicate parameters that need to be set prior to access

.. doctest:: loaded

    >>> conf.log.file
    Traceback (most recent call last):
    ...
    omegaconf.MissingMandatoryValue: log.file


Variable interpolation
----------------------

OmegaConf support variable interpolation, Interpolations are evaluated lazily on access.

Config node interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^
The interpolated variable can be the dot-path to another node in the configuration, and in that case
the value will be the value of that node.

Input yaml file:

.. include:: config_interpolation.yaml
   :code: yaml


Example:

.. doctest::

    >>> conf = OmegaConf.load('source/config_interpolation.yaml')
    >>> # Primitive interpolation types are inherited from the referenced value
    >>> print(conf.client.server_port)
    80
    >>> print(type(conf.client.server_port).__name__)
    int

    >>> # Composite interpolation types are always string
    >>> print(conf.client.url)
    http://localhost:80/
    >>> print(type(conf.client.url).__name__)
    str


Environment variable interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environment variable interpolation is also supported.

Input yaml file:

.. include:: env_interpolation.yaml
   :code: yaml

.. doctest::

    >>> conf = OmegaConf.load('source/env_interpolation.yaml')
    >>> print(conf.user.name)
    omry
    >>> print(conf.user.home)
    /home/omry


Custom interpolations
^^^^^^^^^^^^^^^^^^^^^
You can add additional interpolation types using custom resolvers.
This example creates a resolver that adds 10 the the given value.

.. doctest::

    >>> OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000


Merging configurations
----------------------
Merging configurations enables the creation of reusable configuration files for each logical component
instead of a single config file for each variation of your task.

Machine learning experiment example:

.. code-block:: python

   conf = OmegaConf.merge(base_cfg, model_cfg, optimizer_cfg, dataset_cfg)

Web server configuration example:

.. code-block:: python

   conf = OmegaConf.merge(server_cfg, plugin1_cfg, site1_cfg, site2_cfg)

The following example creates two configs from files, and one from the cli. It then combines them into a single object.
Note how the port changes to 82, and how the users lists are combined.

**example2.yaml** file:

.. include:: example2.yaml
   :code: yaml

**more_users.yaml** file:

.. include:: more_users.yaml
   :code: yaml


.. doctest::

    >>> from omegaconf import OmegaConf
    >>> import sys
    >>> base_conf = OmegaConf.load('source/example2.yaml')
    >>> users_conf = OmegaConf.load('source/more_users.yaml')

    >>> # Simulate command line arguments
    >>> sys.argv = ['program.py', 'server.port=82']
    >>> cli_conf = OmegaConf.from_cli()

    >>> # Merge configs:
    >>> conf = OmegaConf.merge(base_conf, users_conf, cli_conf)
    >>> print(conf.pretty())
    server:
      port: 82
    users:
    - user1
    - user2
    - user3
    <BLANKLINE>
