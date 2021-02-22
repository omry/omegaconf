.. testsetup:: *

    from omegaconf import OmegaConf, DictConfig, open_dict, read_write
    import os
    import sys
    import tempfile
    import pickle
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
    >>> print(OmegaConf.to_yaml(conf))
    {}
    <BLANKLINE>

From a dictionary
^^^^^^^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.create({"k" : "v", "list" : [1, {"a": "1", "b": "2", 3: "c"}]})
    >>> print(OmegaConf.to_yaml(conf))
    k: v
    list:
    - 1
    - a: '1'
      b: '2'
      3: c
    <BLANKLINE>

Here is an example of various supported key types:

.. doctest::

    >>> from enum import Enum
    >>> class Color(Enum):
    ...   RED = 1
    ...   BLUE = 2
    >>> 
    >>> conf = OmegaConf.create(
    ...   {"key": "str", 123: "int", True: "bool", 3.14: "float", Color.RED: "Color"}
    ... )
    >>> 
    >>> print(conf)
    {'key': 'str', 123: 'int', True: 'bool', 3.14: 'float', <Color.RED: 1>: 'Color'}

OmegaConf supports `str`, `int`, `bool`, `float` and Enums as dictionary key types.

From a list
^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.create([1, {"a":10, "b": {"a":10, 123: "int_key"}}])
    >>> print(OmegaConf.to_yaml(conf))
    - 1
    - a: 10
      b:
        a: 10
        123: int_key
    <BLANKLINE>

Tuples are supported as an valid option too.

From a YAML file
^^^^^^^^^^^^^^^^

.. doctest::

    >>> conf = OmegaConf.load('source/example.yaml')
    >>> # Output is identical to the YAML file
    >>> print(OmegaConf.to_yaml(conf))
    server:
      port: 80
    log:
      file: ???
      rotation: 3600
    users:
    - user1
    - user2
    <BLANKLINE>


From a YAML string
^^^^^^^^^^^^^^^^^^

.. doctest::

    >>> s = """
    ... a: b
    ... b: c
    ... list:
    ... - item1
    ... - item2
    ... 123: 456
    ... """
    >>> conf = OmegaConf.create(s)
    >>> print(OmegaConf.to_yaml(conf))
    a: b
    b: c
    list:
    - item1
    - item2
    123: 456
    <BLANKLINE>

From a dot-list
^^^^^^^^^^^^^^^^

.. doctest::

    >>> dot_list = ["a.aa.aaa=1", "a.aa.bbb=2", "a.bb.aaa=3", "a.bb.bbb=4"]
    >>> conf = OmegaConf.from_dotlist(dot_list)
    >>> print(OmegaConf.to_yaml(conf))
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
    >>> print(OmegaConf.to_yaml(conf))
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
    >>> print(OmegaConf.to_yaml(conf))
    port: 80
    host: localhost
    <BLANKLINE>

You can use an object to initialize the config as well:

.. doctest::

    >>> conf = OmegaConf.structured(MyConfig(port=443))
    >>> print(OmegaConf.to_yaml(conf))
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

Input YAML file for this section:

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


Serialization
-------------
OmegaConf objects can be saved and loaded with OmegaConf.save() and OmegaConf.load().
The created file is in YAML format.
Save and load can operate on file-names, Paths and file objects.

Save/Load YAML file
^^^^^^^^^^^^^^^^^^^

.. doctest:: loaded

    >>> conf = OmegaConf.create({"foo": 10, "bar": 20, 123: 456})
    >>> with tempfile.NamedTemporaryFile() as fp:
    ...     OmegaConf.save(config=conf, f=fp.name)
    ...     loaded = OmegaConf.load(fp.name)
    ...     assert conf == loaded

Note that this does not retain type information.

Save/Load pickle file
^^^^^^^^^^^^^^^^^^^^^
Use pickle to save and load while retaining the type information.
Note that the saved file may be incompatible across different major versions of OmegaConf.

.. doctest:: loaded

    >>> conf = OmegaConf.create({"foo": 10, "bar": 20, 123: 456})
    >>> with tempfile.TemporaryFile() as fp:
    ...     pickle.dump(conf, fp)
    ...     fp.flush()
    ...     assert fp.seek(0) == 0
    ...     loaded = pickle.load(fp)
    ...     assert conf == loaded


.. _interpolation:

Variable interpolation
----------------------

OmegaConf supports variable interpolation. Interpolations are evaluated lazily on access.

Config node interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^
The interpolated variable can be the dot-path to another node in the configuration, and in that case
the value will be the value of that node.

Interpolations are absolute by default. Relative interpolation are prefixed by one or more dots:
The first dot denotes the level of the node itself and additional dots are going up the parent hierarchy.
e.g. **${..foo}** points to the **foo** sibling of the parent of the current node.


Input YAML file:

.. include:: config_interpolation.yaml
   :code: yaml


Example:

.. doctest::

    >>> conf = OmegaConf.load('source/config_interpolation.yaml')
    >>> # Primitive interpolation types are inherited from the reference
    >>> conf.client.server_port
    80
    >>> type(conf.client.server_port).__name__
    'int'
    >>> conf.client.description
    'Client of http://localhost:80/'

    >>> # Composite interpolation types are always string
    >>> conf.client.url
    'http://localhost:80/'
    >>> type(conf.client.url).__name__
    'str'


Interpolations may be nested, enabling more advanced behavior like dynamically selecting a sub-config:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...    {
    ...        "plans": {
    ...            "A": "plan A",
    ...            "B": "plan B",
    ...        },
    ...        "selected_plan": "A",
    ...        "plan": "${plans.${selected_plan}}",
    ...    }
    ... )
    >>> cfg.plan # default plan
    'plan A'
    >>> cfg.selected_plan = "B"
    >>> cfg.plan # new plan
    'plan B'

Interpolated nodes can be any node in the config, not just leaf nodes:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...     {
    ...         "john": {"height": 180, "weight": 75},
    ...         "player": "${john}",
    ...     }
    ... )
    >>> (cfg.player.height, cfg.player.weight)
    (180, 75)


Environment variable interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Environment variable interpolation is also supported.

Input YAML file:

.. include:: env_interpolation.yaml
   :code: yaml

.. doctest::

    >>> conf = OmegaConf.load('source/env_interpolation.yaml')
    >>> conf.user.name
    'omry'
    >>> conf.user.home
    '/home/omry'

You can specify a default value to use in case the environment variable is not defined.
The following example sets `abc123` as the the default value when `DB_PASSWORD` is not defined.

.. doctest::

    >>> cfg = OmegaConf.create({
    ...       'database': {'password': '${env:DB_PASSWORD,abc123}'}
    ... })
    >>> cfg.database.password
    'abc123'

Environment variables are parsed when they are recognized as valid quantities that
may be evaluated (e.g., int, float, dict, list):

.. doctest::

    >>> cfg = OmegaConf.create({
    ...       'database': {'password': '${env:DB_PASSWORD,abc123}',
    ...                    'user': 'someuser',
    ...                    'port': '${env:DB_PORT,3306}',
    ...                    'nodes': '${env:DB_NODES,[]}'}
    ... })
    >>> os.environ["DB_PORT"] = '3308'
    >>> cfg.database.port  # converted to int
    3308
    >>> os.environ["DB_NODES"] = '[host1, host2, host3]'
    >>> cfg.database.nodes  # converted to list
    ['host1', 'host2', 'host3']
    >>> os.environ["DB_PASSWORD"] = 'a%#@~{}$*&^?/<'
    >>> cfg.database.password  # kept as a string
    'a%#@~{}$*&^?/<'


Custom interpolations
^^^^^^^^^^^^^^^^^^^^^

You can add additional interpolation types using custom resolvers.
The example below creates a resolver that adds 10 to the given value.

.. doctest::

    >>> OmegaConf.register_new_resolver("plus_10", lambda x: x + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000


Custom resolvers support variadic argument lists in the form of a comma separated list of zero or more values.
Whitespaces are stripped from both ends of each value ("foo,bar" is the same as "foo, bar ").
You can use literal commas and spaces anywhere by escaping (:code:`\,` and :code:`\ `), or
simply use quotes to bypass character limitations in strings.

.. doctest::

    >>> OmegaConf.register_new_resolver("concat", lambda x, y: x+y)
    >>> c = OmegaConf.create({
    ...     'key1': '${concat:Hello,World}',
    ...     'key_trimmed': '${concat:Hello , World}',
    ...     'escape_whitespace': '${concat:Hello,\ World}',
    ...     'quoted': '${concat:"Hello,", " World"}',
    ... })
    >>> c.key1
    'HelloWorld'
    >>> c.key_trimmed
    'HelloWorld'
    >>> c.escape_whitespace
    'Hello World'
    >>> c.quoted
    'Hello, World'


You can take advantage of nested interpolations to perform custom operations over variables:

.. doctest::

    >>> OmegaConf.register_new_resolver("plus", lambda x, y: x + y)
    >>> c = OmegaConf.create({"a": 1,
    ...                       "b": 2,
    ...                       "a_plus_b": "${plus:${a},${b}}"})
    >>> c.a_plus_b
    3


More advanced resolver naming features include the ability to prefix a resolver name with a
namespace, and to use interpolations in the name itself. The following example demonstrates both:

.. doctest::

    >>> OmegaConf.register_new_resolver("mylib.plus1", lambda x: x + 1)
    >>> c = OmegaConf.create(
    ...     {
    ...         "func": "plus1",
    ...         "x": "${mylib.${func}:3}",
    ...     }
    ... )
    >>> c.x
    4


By default a custom resolver's output is cached, so that when it is called with the same
inputs we always return the same value. This behavior may be disabled by setting ``use_cache=False``:

.. doctest::

    >>> import random
    >>> random.seed(1234)
    >>> OmegaConf.register_new_resolver("cached", random.randint)
    >>> OmegaConf.register_new_resolver(
    ...              "uncached", random.randint, use_cache=False)
    >>> c = OmegaConf.create({"cached": "${cached:0,10000}",
    ...                       "uncached": "${uncached:0,10000}"})
    >>> # same value on repeated access thanks to the cache
    >>> assert c.cached == c.cached == 7220
    >>> # not the same since the cache is disabled
    >>> assert c.uncached != c.uncached


Merging configurations
----------------------
Merging configurations enables the creation of reusable configuration files for each logical component
instead of a single config file for each variation of your task.

OmegaConf.merge()
^^^^^^^^^^^^^^^^^

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
    >>> print(OmegaConf.to_yaml(conf))
    server:
      port: 82
    users:
    - user1
    - user2
    log:
      file: log.txt
    <BLANKLINE>

OmegaConf.unsafe_merge()
^^^^^^^^^^^^^^^^^^^^^^^^

OmegaConf offers a second faster function to merge config objects:

.. code-block:: python

   conf = OmegaConf.unsafe_merge(base_cfg, model_cfg, optimizer_cfg, dataset_cfg)
   
Unlike OmegaConf.merge(), unsafe_merge() is destroying the input configs and they should no longer be used 
after this call. The upside is that it's substantially faster.

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

Tests if a value is missing ('???').

.. doctest::

    >>> cfg = OmegaConf.create({
    ...         "foo" : 10, 
    ...         "bar": "???"
    ...     })
    >>> assert not OmegaConf.is_missing(cfg, "foo")
    >>> assert OmegaConf.is_missing(cfg, "bar")

OmegaConf.is_interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^^

Tests if a value is an interpolation.

.. doctest::

    >>> cfg = OmegaConf.create({
    ...         "foo" : 10, 
    ...         "bar": "${foo}"
    ...     })
    >>> assert not OmegaConf.is_interpolation(cfg, "foo")
    >>> assert OmegaConf.is_interpolation(cfg, "bar")

OmegaConf.is_none
^^^^^^^^^^^^^^^^^

Tests if a value is None.

.. doctest::

    >>> cfg = OmegaConf.create({
    ...         "foo" : 10, 
    ...         "bar": None,
    ...     })
    >>> assert not OmegaConf.is_none(cfg, "foo")
    >>> assert OmegaConf.is_none(cfg, "bar")
    >>> # missing keys are interpreted as None
    >>> assert OmegaConf.is_none(cfg, "no_such_key")


OmegaConf.{is_config, is_dict, is_list}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Tests if an object is an OmegaConf object, or if it's representing a list or a dict.

.. doctest::

    >>> # dict:
    >>> d = OmegaConf.create({"foo": "bar"})
    >>> assert OmegaConf.is_config(d)
    >>> assert OmegaConf.is_dict(d)
    >>> assert not OmegaConf.is_list(d)
    >>> # list:
    >>> l = OmegaConf.create([1,2,3])
    >>> assert OmegaConf.is_config(l)
    >>> assert OmegaConf.is_list(l)
    >>> assert not OmegaConf.is_dict(l)

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

    >>> cfg = OmegaConf.create({
    ...     "foo" : {
    ...         "missing" : "???",
    ...         "bar": {
    ...             "zonk" : 10,
    ...         }
    ...     }
    ... })
    >>> assert OmegaConf.select(cfg, "foo") == {
    ...     "missing" : "???",    
    ...     "bar":  {
    ...         "zonk" : 10, 
    ...     }
    ... }
    >>> assert OmegaConf.select(cfg, "foo.bar") == {
    ...     "zonk" : 10, 
    ... }
    >>> assert OmegaConf.select(cfg, "foo.bar.zonk") == 10
    >>> assert OmegaConf.select(cfg, "no_such_key", default=99) == 99
    >>> assert OmegaConf.select(cfg, "foo.missing") is None
    >>> assert OmegaConf.select(cfg, "foo.missing", default=99) == 99
    >>> OmegaConf.select(cfg,
    ...     "foo.missing", 
    ...     throw_on_missing=True
    ... )
    Traceback (most recent call last):
    ...
    omegaconf.errors.MissingMandatoryValue: missing node selected
        full_key: foo.missing

OmegaConf.update
^^^^^^^^^^^^^^^^
OmegaConf.update() allow you to update values in your config using a dot-notation key.

The merge flag controls the behavior if the input is a dict or a list. If it's true, those are merged instead of
being assigned.

.. doctest::

    >>> cfg = OmegaConf.create({"foo" : {"bar": 10}})
    >>> OmegaConf.update(cfg, "foo.bar", 20, merge=True) # merge has no effect because the value is a primitive
    >>> assert cfg.foo.bar == 20
    >>> OmegaConf.update(cfg, "foo.bar", {"zonk" : 30}, merge=False) # set   
    >>> assert cfg.foo.bar == {"zonk" : 30}
    >>> OmegaConf.update(cfg, "foo.bar", {"oompa" : 40}, merge=True) # merge
    >>> assert cfg.foo.bar == {"zonk" : 30, "oompa" : 40}



OmegaConf.masked_copy
^^^^^^^^^^^^^^^^^^^^^
Creates a copy of a DictConfig that contains only specific keys.

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"b": 10}, "c":20})
    >>> print(OmegaConf.to_yaml(conf))
    a:
      b: 10
    c: 20
    <BLANKLINE>
    >>> c = OmegaConf.masked_copy(conf, ["a"])
    >>> print(OmegaConf.to_yaml(c))
    a:
      b: 10
    <BLANKLINE>
