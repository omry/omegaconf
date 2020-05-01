.. testsetup:: *

    from omegaconf import OmegaConf, DictConfig, open_dict, read_write
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

OmegaConf requires Python 3.6 and newer.

Creating
--------
You can create OmegaConf objects from multiple sources.

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

    >>> conf = OmegaConf.create({"k" : "v", "list" : [1, {"a": "1", "b": "2"}]})
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

    >>> conf = OmegaConf.create([1, {"a":10, "b": {"a":10}}])
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
    server:
      port: 80
    log:
      file: ???
      rotation: 3600
    users:
    - user1
    - user2
    <BLANKLINE>


From a yaml string
^^^^^^^^^^^^^^^^^^

.. doctest::

    >>> s = """
    ... a: b
    ... b: c
    ... list:
    ... - item1
    ... - item2
    ... """
    >>> conf = OmegaConf.create(s)
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
    server:
      port: 82
    log:
      file: log2.txt
    <BLANKLINE>

From structured config
^^^^^^^^^^^^^^^^^^^^^^
*New in OmegaConf 2.0, API Considered experimental and may change.*

You can create OmegaConf objects from structured config classes or objects. This provides static and runtime type safety.
See :doc:`structured_config` for more details, or keep reading for a minimal example.

.. doctest::

    >>> from dataclasses import dataclass
    >>> @dataclass
    ... class MyConfig:
    ...     port: int = 80
    ...     host: str = "localhost"
    >>> # For strict typing purposes, prefer OmegaConf.structured() when creating structured configs
    >>> conf = OmegaConf.structured(MyConfig)
    >>> print(conf.pretty())
    port: 80
    host: localhost
    <BLANKLINE>

You can use an object to initialize the config as well:

.. doctest::

    >>> conf = OmegaConf.structured(MyConfig(port=443))
    >>> print(conf.pretty())
    port: 443
    host: localhost
    <BLANKLINE>

OmegaConf objects constructed from Structured classes offers runtime type safety:

.. doctest::

    >>> conf.port = 42      # Ok, type matches
    >>> conf.port = "1080"  # Ok! "1080" can be converted to an int
    >>> conf.port = "oops"  # "oops" cannot be converted to an int
    Traceback (most recent call last):
    ...
    omegaconf.errors.ValidationError: Value 'oops' could not be converted to Integer

In addition, the config class can be used as type annotation for static type checkers or IDEs:

.. doctest::

    >>> def foo(conf: MyConfig):
    ...     print(conf.port) # passes static type checker
    ...     print(conf.pork) # fails static type checker

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

Default values
^^^^^^^^^^^^^^
You can provide default values directly in the accessing code:

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


Manipulation
^^^^^^^^^^^^
.. doctest:: loaded

    >>> # Changing existing keys
    >>> conf.server.port = 81

    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"

    >>> # Adding a new dictionary
    >>> conf.database = {'hostname': 'database01', 'port': 3306}

.. _interpolation:


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

You can specify a default value to use in case the environment variable is not defined.
The following example sets `12345` as the the default value for the `DB_PASSWORD` environment variable.

.. doctest::

    >>> cfg = OmegaConf.create({
    ...       'database': {'password': '${env:DB_PASSWORD,12345}'}
    ... })
    >>> print(cfg.database.password)
    12345
    >>> OmegaConf.clear_cache(cfg) # clear resolver cache
    >>> os.environ["DB_PASSWORD"] = 'secret'
    >>> print(cfg.database.password)
    secret

Custom interpolations
^^^^^^^^^^^^^^^^^^^^^
You can add additional interpolation types using custom resolvers.
This example creates a resolver that adds 10 the the given value.

.. doctest::

    >>> OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000


Custom resolvers support variadic argument lists in the form of a comma separated list of zero or more values.
Whitespaces are stripped from both ends of each value ("foo,bar" is the same as "foo, bar ").
You can use literal commas and spaces anywhere by escaping (:code:`\,` and :code:`\ `).
.. doctest::

    >>> OmegaConf.register_resolver("concat", lambda x,y: x+y)
    >>> c = OmegaConf.create({
    ...     'key1': '${concat:Hello,World}',
    ...     'key_trimmed': '${concat:Hello , World}',
    ...     'escape_whitespace': '${concat:Hello,\ World}',
    ... })
    >>> c.key1
    'HelloWorld'
    >>> c.key_trimmed
    'HelloWorld'
    >>> c.escape_whitespace
    'Hello World'



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

**example3.yaml** file:

.. include:: example3.yaml
   :code: yaml


.. doctest::

    >>> from omegaconf import OmegaConf
    >>> import sys
    >>>
    >>> # Simulate command line arguments
    >>> sys.argv = ['program.py', 'server.port=82']
    >>>
    >>> base_conf = OmegaConf.load('source/example2.yaml')
    >>> second_conf = OmegaConf.load('source/example3.yaml')
    >>> cli_conf = OmegaConf.from_cli()
    >>>
    >>> # merge them all
    >>> conf = OmegaConf.merge(base_conf, second_conf, cli_conf)
    >>> print(conf.pretty())
    server:
      port: 82
    users:
    - user1
    - user2
    log:
      file: log.txt
    <BLANKLINE>

Configuration flags
-------------------

OmegaConf support several configuration flags.
Configuration flags can be set on any configuration node (Sequence or Mapping). if a configuration flag is not set
it inherits the value from the parent of the node.
The default value inherited from the root node is always false.

.. _read-only-flag:

Read-only flag
^^^^^^^^^^^^^^
A read-only configuration cannot be modified.
An attempt to modify it will result in omegaconf.ReadonlyConfigError exception

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"b": 10}})
    >>> OmegaConf.set_readonly(conf, True)
    >>> conf.a.b = 20
    Traceback (most recent call last):
    ...
    omegaconf.ReadonlyConfigError: a.b

You can temporarily remove the read only flag from a config object:

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"b": 10}})
    >>> OmegaConf.set_readonly(conf, True)
    >>> with read_write(conf):
    ...   conf.a.b = 20
    >>> conf.a.b
    20

.. _struct-flag:

Struct flag
^^^^^^^^^^^
By default, OmegaConf dictionaries allow read and write access to unknown fields.
If a field does not exist, accessing it will return None and writing it will create the field.
It's sometime useful to change this behavior.


.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"aa": 10, "bb": 20}})
    >>> OmegaConf.set_struct(conf, True)
    >>> conf.a.cc = 30
    Traceback (most recent call last):
    ...
    omegaconf.errors.ConfigAttributeError: Error setting cc=30 : Key 'cc' in not in struct
        full_key: a.cc
        reference_type=Any
        object_type=dict


You can temporarily remove the struct flag from a config object:

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"aa": 10, "bb": 20}})
    >>> OmegaConf.set_struct(conf, True)
    >>> with open_dict(conf):
    ...   conf.a.cc = 30
    >>> conf.a.cc
    30

Utility functions
-----------------

OmegaConf.is_missing
^^^^^^^^^^^^^^^^^^^^

Tests if a key is missing ('???')

.. doctest::

    >>> cfg = OmegaConf.create({"foo" : 10, "bar": "???"})
    >>> assert not OmegaConf.is_missing(cfg, "foo")
    >>> assert OmegaConf.is_missing(cfg, "bar")

OmegaConf.{is_config, is_dict, is_list}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tests if an object is an OmegaConf object, or if it's representing a list or a dict.

.. doctest::

    >>> list_cfg = OmegaConf.create([1,2,3])
    >>> dict_cfg = OmegaConf.create({"foo": "bar"})
    >>> assert OmegaConf.is_config(list_cfg) and OmegaConf.is_config(dict_cfg)
    >>> assert OmegaConf.is_dict(dict_cfg) and not OmegaConf.is_dict(list_cfg)
    >>> assert OmegaConf.is_list(list_cfg) and not OmegaConf.is_list(dict_cfg)

OmegaConf.to_container
^^^^^^^^^^^^^^^^^^^^^^
OmegaConf config objects looks very similar to python dict and list, but in fact are not.
Use OmegaConf.to_container(cfg : Container, resolve : bool) to convert to a primitive container.
If resolve is set to True, interpolations will be resolved during conversion.

.. doctest::

    >>> conf = OmegaConf.create({"foo": "bar", "foo2": "${foo}"})
    >>> assert type(conf) == DictConfig
    >>> primitive = OmegaConf.to_container(conf)
    >>> assert type(primitive) == dict
    >>> print(primitive)
    {'foo': 'bar', 'foo2': '${foo}'}
    >>> resolved = OmegaConf.to_container(conf, resolve=True)
    >>> print(resolved)
    {'foo': 'bar', 'foo2': 'bar'}


OmegaConf.select
^^^^^^^^^^^^^^^^
OmegaConf.select() allow you to select a config node or value using a dot-notation key.

.. doctest::

    >>> cfg = OmegaConf.create({"foo" : {"bar": {"zonk" : 10, "missing" : "???"}}})
    >>> assert OmegaConf.select(cfg, "foo") == {"bar": {"zonk" : 10, "missing" : "???"}}
    >>> assert OmegaConf.select(cfg, "foo.bar") == {"zonk" : 10, "missing" : "???"}
    >>> assert OmegaConf.select(cfg, "foo.bar.zonk") == 10
    >>> assert OmegaConf.select(cfg, "foo.bar.missing") is None
    >>> OmegaConf.select(cfg, "foo.bar.missing", throw_on_missing=True)
    Traceback (most recent call last):
    ...
    omegaconf.errors.MissingMandatoryValue: missing node selected
        full_key: foo.bar.missing

OmegaConf.update
^^^^^^^^^^^^^^^^
OmegaConf.update() allow you to update values in your config using a dot-notation key.

.. doctest::

    >>> cfg = OmegaConf.create({"foo" : {"bar": 10}})
    >>> OmegaConf.update(cfg, "foo.bar", 20)
    >>> assert cfg.foo.bar == 20
    >>> OmegaConf.update(cfg, "foo.bar", {"zonk" : 30})
    >>> assert cfg.foo.bar == {"zonk" : 30}



OmegaConf.masked_copy
^^^^^^^^^^^^^^^^^^^^^
Creates a copy of a DictConfig that contains only specific keys.

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"b": 10}, "c":20})
    >>> print(conf.pretty())
    a:
      b: 10
    c: 20
    <BLANKLINE>
    >>> c = OmegaConf.masked_copy(conf, ["a"])
    >>> print(c.pretty())
    a:
      b: 10
    <BLANKLINE>
