=====
Usage
=====

.. contents::
   :local:

.. testsetup:: *

    from omegaconf import OmegaConf, DictConfig, ListConfig, open_dict, read_write
    import os
    import sys
    import tempfile
    import pickle
    # ensures that DB_TIMEOUT is not set in the doc.
    os.environ.pop('DB_TIMEOUT', None)

.. testsetup:: loaded

    from omegaconf import OmegaConf
    conf = OmegaConf.load('source/example.yaml')

Installation
------------

Just pip install::

    pip install omegaconf

OmegaConf requires Python 3.8 or newer.

.. _creating:

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
    ...   {"key": "str", 123: "int", True: "bool", 3.14: "float", Color.RED: "Color", b"123": "bytes"}
    ... )
    >>> 
    >>> print(conf)
    {'key': 'str', 123: 'int', True: 'bool', 3.14: 'float', <Color.RED: 1>: 'Color', b'123': 'bytes'}

OmegaConf supports ``str``, ``int``, ``bool``, ``float`` ``bytes``, and ``Enum`` as dictionary key types.

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

Tuples are supported as a valid option too.

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

OmegaConf objects constructed from Structured classes provide runtime type safety:

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
Use the value ``"???"`` to indicate parameters that need to be set prior to access

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

.. _save_and_load_pickle_file:

Save/Load pickle file
^^^^^^^^^^^^^^^^^^^^^
Use pickle to save and load while retaining the type information.
Note that the saved file may be incompatible across different versions of OmegaConf.

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

.. _config-node-interpolation:

Config node interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^
The interpolated variable can be the path to another node in the configuration, and in that case
the value will be the value of that node.
This path may use either dot-notation (``foo.1``), brackets (``[foo][1]``) or a mix of both (``foo[1]``, ``[foo].1``).

Interpolations are absolute by default. Relative interpolation are prefixed by one or more dots:
The first dot denotes the level of the node itself and additional dots are going up the parent hierarchy.
e.g. ``${..foo}`` points to the ``foo`` sibling of the parent of the current node.

NOTE: Interpolations may cause config cycles. Such cycles are forbidden and may cause undefined behavior.

Input YAML file:

.. include:: config_interpolation.yaml
   :code: yaml


Example:

.. doctest::

    >>> conf = OmegaConf.load('source/config_interpolation.yaml')
    >>> def show(x):
    ...     print(f"type: {type(x).__name__}, value: {repr(x)}")
    >>> # Primitive interpolation types are inherited from the reference
    >>> show(conf.client.server_port)
    type: int, value: 80
    >>> # String interpolations concatenate fragments into a string
    >>> show(conf.client.url)
    type: str, value: 'http://localhost:80/'
    >>> # Relative interpolation example
    >>> show(conf.client.description)
    type: str, value: 'Client of http://localhost:80/'

.. _nested-interpolation:

Nested interpolation
~~~~~~~~~~~~~~~~~~~~

Interpolations may be nested, enabling more advanced behavior like dynamically selecting a sub-config:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...    {
    ...        "plans": {
    ...            "A": "plan A",
    ...            "B": "plan B",
    ...        },
    ...        "selected_plan": "A",
    ...        "plan": "${plans[${selected_plan}]}",
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

.. _resolvers:

Resolvers
^^^^^^^^^
Add new interpolation types by registering resolvers using ``OmegaConf.register_new_resolver()``.
Such resolvers are called when the config node is accessed.
The minimal example below shows its most basic usage, see :doc:`custom_resolvers` for more details.

.. doctest::

    >>> OmegaConf.register_new_resolver(
    ...     "add", lambda *numbers: sum(numbers)
    ... )
    >>> c = OmegaConf.create({'total': '${add:1,2,3}'})
    >>> c.total
    6

Built-in resolvers
^^^^^^^^^^^^^^^^^^
OmegaConf comes with a set of built-in custom resolvers:

* :ref:`oc.create`: Dynamically generating config nodes
* :ref:`oc.decode`: Parsing an input string using interpolation grammar
* :ref:`oc.deprecated`: Deprecate a key in your config
* :ref:`oc.env`: Accessing environment variables
* :ref:`oc.select`: Selecting an interpolation key, similar to interpolation but more flexible
* :ref:`oc.dict.{keys,values}`: Viewing the keys or the values of a dictionary as a list


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
Note how the port changes to 82.

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

By default, ``merge()`` is replacing the target list with the source list.
Use ``list_merge_mode`` to control the merge behavior for lists.
This Enum is defined in ``omegaconf.ListMergeMode`` and defines the following modes:
* ``REPLACE``: Replaces the target list with the new one (default)
* ``EXTEND``: Extends the target list with the new one
* ``EXTEND_UNIQUE``: Extends the target list items with items not present in it

**example2.yaml** file:

.. include:: example2.yaml
   :code: yaml

**example4.yaml** file:

.. include:: example4.yaml
   :code: yaml

If you load them and merge them with ``list_merge_mode=ListMergeMode.EXTEND_UNIQUE`` you will get this:

.. doctest::

    >>> from omegaconf import OmegaConf, ListMergeMode
    >>>
    >>> cfg_1 = OmegaConf.load('source/example2.yaml')
    >>> cfg_2 = OmegaConf.load('source/example4.yaml')
    >>> 
    >>> mode = ListMergeMode.EXTEND_UNIQUE
    >>> conf = OmegaConf.merge(cfg_1, cfg_2, list_merge_mode=mode)
    >>> print(OmegaConf.to_yaml(conf))
    server:
      port: 80
    users:
    - user1
    - user2
    - user3
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
Configuration flags can be set on any configuration node (Sequence or Mapping). If a configuration flag is not set
it inherits the value from the parent of the node.
The default value inherited from the root node is always false.
To avoid this inhertence and set a flag explicitly to all children nodes, specify the option `recursive=True`.

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

Example using `recursive=True`:

.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"b": 10}})
    >>> OmegaConf.set_readonly(conf.a, True)
    >>> OmegaConf.set_readonly(conf, False, recursive = True)
    >>> conf.a.b = 20
    >>> conf.a.b
    20

.. _struct-flag:

Struct flag
^^^^^^^^^^^
By default, OmegaConf dictionaries allow write access to unknown fields.
If a field does not exist, writing it will create the field, and attempting to
access the field before creation will raise an exception (either ``ConfigKeyError``
or ``ConfigAttributeError``, depending on the mode of access).
It's sometime useful to change this behavior.  Using ``OmegaConf.set_struct``,
it is possible to prevent the creation of fields that do not exist:


.. doctest:: loaded

    >>> conf = OmegaConf.create({"a": {"aa": 10, "bb": 20}})
    >>> OmegaConf.set_struct(conf, True)
    >>> conf.a.cc = 30
    Traceback (most recent call last):
    ...
    omegaconf.errors.ConfigAttributeError: Error setting cc=30 : Key 'cc' is not in struct
        full_key: a.cc
        reference_type=Any
        object_type=dict


You can temporarily remove the struct flag from a config object:

.. doctest:: loaded

    >>> from omegaconf import open_dict
    >>> conf = OmegaConf.create({"a": {"aa": 10, "bb": 20}})
    >>> OmegaConf.set_struct(conf, True)
    >>> with open_dict(conf):
    ...   conf.a.cc = 30
    >>> conf.a.cc
    30

Utility functions
-----------------

OmegaConf.to_container
^^^^^^^^^^^^^^^^^^^^^^
OmegaConf config objects looks very similar to python dict and list, but in fact are not.
Use ``OmegaConf.to_container(cfg: Container, resolve: bool)`` to convert to a primitive container.
If ``resolve`` is set to ``True``, interpolations will be resolved during conversion.

.. doctest::

    >>> conf = OmegaConf.create({"foo": "bar", "foo2": "${foo}"})
    >>> assert type(conf) == DictConfig
    >>> primitive = OmegaConf.to_container(conf)
    >>> show(primitive)
    type: dict, value: {'foo': 'bar', 'foo2': '${foo}'}
    >>> resolved = OmegaConf.to_container(conf, resolve=True)
    >>> show(resolved)
    type: dict, value: {'foo': 'bar', 'foo2': 'bar'}


Using ``throw_on_missing``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can control how missing values are handled by ``OmegaConf.to_container()``
using the ``throw_on_missing`` keyword argument.

.. doctest::

    >>> conf = OmegaConf.create({"foo": "bar", "missing": "???"})
    >>> has_missing = OmegaConf.to_container(conf, throw_on_missing=False)
    >>> show(has_missing)
    type: dict, value: {'foo': 'bar', 'missing': '???'}
    >>> OmegaConf.to_container(conf, throw_on_missing=True)
    Traceback (most recent call last):
    ...
    omegaconf.errors.MissingMandatoryValue: Missing mandatory value: missing
        full_key: missing
        object_type=dict


By default, ``throw_on_missing=False``.
Setting ``throw_on_missing=True`` can be useful if you want your program to
fail fast when there are missing values in the config.



Using ``structured_config_mode``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~
You can customize the treatment of ``OmegaConf.to_container()`` for
Structured Config nodes using the ``structured_config_mode`` option.
The default, ``structured_config_mode=SCMode.DICT``, converts Structured Config nodes to plain dict.

Using ``structured_config_mode=SCMode.DICT_CONFIG`` causes such nodes to remain
as ``DictConfig``, allowing attribute style access on the resulting node.

Using ``structured_config_mode=SCMode.INSTANTIATE``, Structured Config nodes
are converted to instances of the backing dataclass or attrs class. Note that
when ``structured_config_mode=SCMode.INSTANTIATE``, interpolations nested within
a structured config node will be resolved, even if ``OmegaConf.to_container`` is called
with the the keyword argument ``resolve=False``, so that interpolations are resolved before
being used to instantiate dataclass/attr class instances. Interpolations within
non-structured parent nodes will be resolved (or not) as usual, according to
the ``resolve`` keyword arg.

.. doctest::

    >>> from omegaconf import SCMode
    >>> conf = OmegaConf.create({"structured_config": MyConfig})
    >>> container = OmegaConf.to_container(conf,
    ...     structured_config_mode=SCMode.DICT_CONFIG)
    >>> show(container)
    type: dict, value: {'structured_config': {'port': 80, 'host': 'localhost'}}
    >>> show(container["structured_config"])
    type: DictConfig, value: {'port': 80, 'host': 'localhost'}

OmegaConf.to_object
^^^^^^^^^^^^^^^^^^^^^^
The ``OmegaConf.to_object`` method recursively converts ``DictConfig`` and ``ListConfig`` objects
into plain Python dicts and lists, with the exception that Structured Config objects are
converted into instances of the backing dataclass or attr class.  Interpolations in the config are always resolved by ``OmegaConf.to_object``.

.. doctest::

    >>> container = OmegaConf.to_object(conf)
    >>> show(container)
    type: dict, value: {'structured_config': MyConfig(port=80, host='localhost')}
    >>> show(container["structured_config"])
    type: MyConfig, value: MyConfig(port=80, host='localhost')

Note that here, ``container["structured_config"]`` is actually an instance of
``MyConfig``, whereas in the previous examples we had a ``dict`` or a
``DictConfig`` object that was duck-typed to look like an instance of
``MyConfig``.

The call ``OmegaConf.to_object(conf)`` is equivalent to
``OmegaConf.to_container(conf, resolve=True, throw_on_missing=True,
structured_config_mode=SCMode.INSTANTIATE)``.

OmegaConf.resolve
^^^^^^^^^^^^^^^^^
.. code-block:: python

    def resolve(cfg: Container) -> None:
        """
        Resolves all interpolations in the given config object in-place.
        :param cfg: An OmegaConf container (DictConfig, ListConfig)
                    Raises a ValueError if the input object is not an OmegaConf container.
        """

Normally interpolations are resolved lazily, at access time. 
This function eagerly resolves all interpolations in the given config object in-place.
Example:

.. doctest::

    >>> cfg = OmegaConf.create({"a": 10, "b": "${a}"})
    >>> show(cfg)
    type: DictConfig, value: {'a': 10, 'b': '${a}'}
    >>> assert cfg.a == cfg.b == 10 # lazily resolving interpolation
    >>> OmegaConf.resolve(cfg)
    >>> show(cfg)
    type: DictConfig, value: {'a': 10, 'b': 10}

OmegaConf.select
^^^^^^^^^^^^^^^^
``OmegaConf.select()`` allows you to select a config node or value, using either a dot-notation or brackets to denote sub-keys.

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
    >>> assert OmegaConf.select(cfg, "foo.bar.zonk") == 10    # dots
    >>> assert OmegaConf.select(cfg, "foo[bar][zonk]") == 10  # brackets
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
``OmegaConf.update()`` allows you to update values in your config using either a dot-notation or brackets to denote sub-keys.

The merge flag controls the behavior if the input is a ``dict`` or a ``list``.
If ``merge=True`` true (the default), dicts and lists are merged instead of being assigned.
The ``force_add`` flag ensures that the path is created even if it will result in insertion of new values into struct nodes.

.. doctest::

    >>> cfg = OmegaConf.create({"foo" : {"bar": 10}})
    >>> OmegaConf.update(cfg, "foo.bar", 20)
    >>> assert cfg.foo.bar == 20
    >>> # Set dictionary value (using dot notation)
    >>> OmegaConf.update(cfg, "foo.bar", {"zonk" : 30}, merge=False)
    >>> assert cfg.foo.bar == {"zonk" : 30}
    >>> # Merge dictionary value (using bracket notation)
    >>> # note that merge is True by default, so you don't really need it here.
    >>> OmegaConf.update(cfg, "foo[bar]", {"oompa" : 40}, merge=True)
    >>> assert cfg.foo.bar == {"zonk" : 30, "oompa" : 40}
    >>> # force_add ignores nodes in struct mode or Structured Configs nodes 
    >>> # and updates anyway, inserting keys as needed.
    >>> OmegaConf.set_struct(cfg, True)
    >>> OmegaConf.update(cfg, "a.b.c.d", 10, force_add=True)
    >>> assert cfg.a.b.c.d == 10



OmegaConf.masked_copy
^^^^^^^^^^^^^^^^^^^^^
Creates a copy of a ``DictConfig`` that contains only specific keys.

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

OmegaConf.is_missing
^^^^^^^^^^^^^^^^^^^^

Tests if a value is missing (``"???"``).

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


OmegaConf.{is_config, is_dict, is_list}
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

``OmegaConf.is_config`` tests whether an object is an OmegaConf object (e.g. ``DictConfig`` or ``ListConfig``).
``OmegaConf.is_dict(cfg)`` is equivalent to ``isinstance(cfg, DictConfig)``,
and ``OmegaConf.is_list(cfg)`` is equivalent to ``isinstance(cfg, ListConfig)``.

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


OmegaConf.missing_keys
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
``OmegaConf.missing_keys(cfg)`` returns a set of missing keys present in the input ``cfg``.
Each missing key is represented as a ``str``, using a dotlist style.
This utility function can be used after creating a config object, after merging sources and so on,
to check for missing mandatory fields and aid in creating a proper error message.

.. doctest::

    >>> missings = OmegaConf.missing_keys({
    ...     "foo": {"bar": "???"},
    ...     "missing": "???",
    ...      "list": ["a", None, "???"]
    ... })
    >>> assert missings == {'list[2]', 'foo.bar', 'missing'}

The function raises a `ValueError` on input not representing a config.


Debugger integration
--------------------

OmegaConf is packaged with a PyDev.Debugger extension which enables better debugging experience in PyCharm, 
VSCode and other `PyDev.Debugger <https://github.com/fabioz/PyDev.Debugger>`_ powered IDEs.

The debugger extension enables OmegaConf-aware object inspection:
 - providing information about interpolations.
 - properly handling missing values (``"???"``).
 
The plugin comes in two flavors:
 - USER: Default behavior, useful when debugging your OmegaConf objects.
 - DEV: Useful when debugging OmegaConf itself, shows the exact data model of OmegaConf.

The default flavor is ``USER``. You can select which flavor to use using the environment variable ``OC_PYDEVD_RESOLVER``,
Which takes the possible values ``USER``, ``DEV`` and ``DISABLE``.
