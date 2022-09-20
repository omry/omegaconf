=========
Resolvers
=========

.. contents::

.. testsetup:: *

    from omegaconf import OmegaConf, DictConfig
    import os
    import pytest
    os.environ['USER'] = 'omry'

    def show(x):
      print(f"type: {type(x).__name__}, value: {repr(x)}")

.. _custom_resolvers:

Custom resolvers
----------------

You can add additional interpolation types by registering custom resolvers with ``OmegaConf.register_new_resolver()``:

.. code-block:: python

    def register_new_resolver(
        name: str,
        resolver: Resolver,
        *,
        replace: bool = False,
        use_cache: bool = False,
    ) -> None

Attempting to register the same resolver twice will raise a ``ValueError`` unless using ``replace=True``.

The example below creates a resolver that adds ``10`` to the given value.

.. doctest::

    >>> OmegaConf.register_new_resolver("plus_10", lambda x: x + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000

Custom resolvers support variadic argument lists in the form of a comma-separated list of zero or more values.
In a variadic argument list, whitespace is stripped from the ends of each value ("foo,bar" gives the same result as "foo, bar ").
You can use literal commas and spaces anywhere by escaping (``\,`` and :code:`\ `), or
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

    >>> OmegaConf.register_new_resolver("sum", lambda x, y: x + y)
    >>> c = OmegaConf.create({"a": 1,
    ...                       "b": 2,
    ...                       "a_plus_b": "${sum:${a},${b}}"})
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


By default a custom resolver is called on every access, but it is possible to cache its output
by registering it with ``use_cache=True``.
This may be useful either for performance reasons or to ensure the same value is always returned.
Note that the cache is based on the string literals representing the resolver's inputs, not on
the inputs themselves:

.. doctest::

    >>> import random
    >>> random.seed(1234)
    >>> OmegaConf.register_new_resolver(
    ...    "cached", random.randint, use_cache=True
    ... )
    >>> OmegaConf.register_new_resolver("uncached", random.randint)
    >>> c = OmegaConf.create(
    ...     {
    ...         "uncached": "${uncached:0,10000}",
    ...         "cached_1": "${cached:0,10000}",
    ...         "cached_2": "${cached:0, 10000}",
    ...         "cached_3": "${cached:0,${uncached}}",
    ...     }
    ... )
    >>> # not the same since the cache is disabled by default
    >>> assert c.uncached != c.uncached
    >>> # same value on repeated access thanks to the cache
    >>> assert c.cached_1 == c.cached_1 == 122
    >>> # same input as `cached_1` => same value
    >>> assert c.cached_2 == c.cached_1 == 122
    >>> # same string literal "${uncached}" => same value
    >>> assert c.cached_3 == c.cached_3 == 1192


Custom interpolations can also receive the following special parameters:

- ``_parent_``: The parent node of an interpolation.
- ``_root_``: The config root.

This can be achieved by adding the special parameters to the resolver signature.
Note that special parameters must be defined as named keywords (after the ``*``).

In the example below, we use ``_parent_`` to implement a sum function that defaults to ``0`` if the node does not exist.
This is in contrast to the sum we defined earlier where accessing an invalid key, e.g. ``"a_plus_z": ${sum:${a}, ${z}}``, would result in an error.

.. doctest::

    >>> def sum2(a, b, *, _parent_):
    ...     return _parent_.get(a, 0) + _parent_.get(b, 0)
    >>> OmegaConf.register_new_resolver("sum2", sum2)
    >>> cfg = OmegaConf.create(
    ...     {
    ...         "node": {
    ...             "a": 1,
    ...             "b": 2,
    ...             "a_plus_b": "${sum2:a,b}",
    ...             "a_plus_z": "${sum2:a,z}",
    ...         },
    ...     }
    ... )
    >>> cfg.node.a_plus_b
    3
    >>> cfg.node.a_plus_z
    1


Built-in resolvers
------------------

.. _oc.env:

oc.env
^^^^^^

Access to environment variables is supported using ``oc.env``:

Input YAML file:

.. include:: env_interpolation.yaml
   :code: yaml

.. doctest::

    >>> conf = OmegaConf.load('source/env_interpolation.yaml')
    >>> conf.user.name
    'omry'
    >>> conf.user.home
    '/home/omry'

You can specify a default value to use in case the environment variable is not set.
In such a case, the default value is converted to a string using ``str(default)``,
unless it is ``null`` (representing Python ``None``) - in which case ``None`` is returned.

The following example falls back to default passwords when ``DB_PASSWORD`` is not defined:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...     {
    ...         "database": {
    ...             "password1": "${oc.env:DB_PASSWORD,password}",
    ...             "password2": "${oc.env:DB_PASSWORD,12345}",
    ...             "password3": "${oc.env:DB_PASSWORD,null}",
    ...         },
    ...     }
    ... )
    >>> # default is already a string
    >>> show(cfg.database.password1)
    type: str, value: 'password'
    >>> # default is converted to a string automatically
    >>> show(cfg.database.password2)
    type: str, value: '12345'
    >>> # unless it's None
    >>> show(cfg.database.password3)
    type: NoneType, value: None


.. _oc.create:

oc.create
^^^^^^^^^

``oc.create`` may be used for dynamic generation of config nodes
(typically from Python ``dict`` / ``list`` objects or YAML strings, similar to :ref:`OmegaConf.create<creating>`).

.. doctest::


    >>> OmegaConf.register_new_resolver("make_dict", lambda: {"a": 10})
    >>> cfg = OmegaConf.create(
    ...     {
    ...         "plain_dict": "${make_dict:}",
    ...         "dict_config": "${oc.create:${make_dict:}}",
    ...         "dict_config_env": "${oc.create:${oc.env:YAML_ENV}}",
    ...     }
    ... )
    >>> os.environ["YAML_ENV"] = "A: 10\nb: 20\nC: ${.A}"
    >>> show(cfg.plain_dict)  # `make_dict` returns a Python dict
    type: dict, value: {'a': 10}
    >>> show(cfg.dict_config)  # `oc.create` converts it to DictConfig
    type: DictConfig, value: {'a': 10}
    >>> show(cfg.dict_config_env)  # YAML string to DictConfig
    type: DictConfig, value: {'A': 10, 'b': 20, 'C': '${.A}'}
    >>> cfg.dict_config_env.C  # interpolations work in a DictConfig
    10


.. _oc.deprecated:

oc.deprecated
^^^^^^^^^^^^^
``oc.deprecated`` enables you to deprecate a config node.
It takes two parameters:

- ``key``: An interpolation key representing the new key you are migrating to. This parameter is required.
- ``message``: A message to use as the warning when the config node is being accessed. The default message is
  ``'$OLD_KEY' is deprecated. Change your code and config to use '$NEW_KEY'``.

.. doctest::

    >>> conf = OmegaConf.create({
    ...   "rusty_key": "${oc.deprecated:shiny_key}",
    ...   "custom_msg": "${oc.deprecated:shiny_key, 'Use $NEW_KEY'}",
    ...   "shiny_key": 10
    ... })
    >>> # Accessing rusty_key will issue a deprecation warning
    >>> # and return the new value automatically
    >>> warning = "'rusty_key' is deprecated. Change your" \
    ...           " code and config to use 'shiny_key'"
    >>> with pytest.warns(UserWarning, match=warning):
    ...   assert conf.rusty_key == 10
    >>> with pytest.warns(UserWarning, match="Use shiny_key"):
    ...   assert conf.custom_msg == 10

.. _oc.decode:

oc.decode
^^^^^^^^^

With ``oc.decode``, strings can be converted into their corresponding data types using
the :ref:`"element" parser rule of the OmegaConf grammar<element-types>`.
This grammar recognizes typical data types like ``bool``, ``int``, ``float``, ``bytes``, ``dict`` and ``list``,
e.g. ``"true"``, ``"1"``, ``"1e-3"``, ``b"123"``, ``"{a: b}"``, ``"[a, b, c]"``.

Note that:

- In most cases input strings provided to ``oc.decode`` should be quoted, since only a subset of the characters is allowed in unquoted strings.
- ``None`` (written as ``null`` in the grammar) is the only valid non-string input to ``oc.decode`` (returning ``None`` in that case).

This resolver can be useful for instance to parse environment variables:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...     {
    ...         "database": {
    ...             "port": '${oc.decode:${oc.env:DB_PORT}}',
    ...             "nodes": '${oc.decode:${oc.env:DB_NODES}}',
    ...             "timeout": '${oc.decode:${oc.env:DB_TIMEOUT,null}}',
    ...         }
    ...     }
    ... )
    >>> os.environ["DB_PORT"] = "3308"
    >>> show(cfg.database.port)  # converted to int
    type: int, value: 3308
    >>> os.environ["DB_NODES"] = "[host1, host2, host3]"
    >>> show(cfg.database.nodes)  # converted to a Python list
    type: list, value: ['host1', 'host2', 'host3']
    >>> show(cfg.database.timeout)  # keeping `None` as is
    type: NoneType, value: None
    >>> os.environ["DB_TIMEOUT"] = "${.port}"
    >>> show(cfg.database.timeout)  # resolving interpolation
    type: int, value: 3308


.. _oc.select:

oc.select
^^^^^^^^^
``oc.select`` enables selection similar to that performed with node interpolation, but is a bit more flexible.
Using ``oc.select``, you can provide a default value to use in case the primary interpolation key is not found.
The following example uses "/tmp" as the default value for the node output:

.. doctest::

    >>> cfg = OmegaConf.create({
    ...  "a": "Saving output to ${oc.select:output,/tmp}"
    ... })
    >>> print(cfg.a)
    Saving output to /tmp
    >>> cfg.output = "/etc/config"
    >>> print(cfg.a)
    Saving output to /etc/config

``oc.select`` can also be used to select keys that are otherwise illegal interpolation keys.
The following example has a key with a colon. Such a key looks like a custom resolver and therefore
cannot be accessed using a regular interpolation:

.. doctest::

    >>> cfg = OmegaConf.create({
    ...    # yes, there is a : in this key
    ...    "a:b": 10,
    ...    "bad": "${a:b}",
    ...    "good": "${oc.select:'a:b'}",
    ... })
    >>> print(cfg.bad)
    Traceback (most recent call last):
    ...
    UnsupportedInterpolationType: Unsupported interpolation type a
    >>> print(cfg.good)
    10

Another scenario where ``oc.select`` can be useful is if you want to select a missing value.

.. doctest::

    >>> cfg = OmegaConf.create({
    ...         "missing": "???",
    ...         "interpolation": "${missing}",
    ...         "select": "${oc.select:missing}",
    ...         "with_default": "${oc.select:missing,default value}",
    ...     }
    ... )
    ...
    >>> print(cfg.interpolation)
    Traceback (most recent call last):
    ...
    InterpolationToMissingValueError: MissingMandatoryValue while ...
    >>> print(cfg.select)
    None
    >>> print(cfg.with_default)
    default value

.. _oc.dict.{keys,values}:

oc.dict.{keys,value}
^^^^^^^^^^^^^^^^^^^^

Some config options that are stored as a ``DictConfig`` may sometimes be easier to manipulate as lists,
when we care only about the keys or the associated values.

The resolvers ``oc.dict.keys`` and ``oc.dict.values`` simplify such operations by offering an alternative
view of a ``DictConfig``'s keys or values as a list,
with behavior analogous to the ``dict.keys`` and ``dict.values`` methods in plain Python dictionaries.
These resolvers take as input a string that is the path to another config node (using the same syntax
as interpolations), and they return a ``ListConfig`` that contains keys or values of the node whose path was given.

.. doctest::

    >>> cfg = OmegaConf.create(
    ...     {
    ...         "workers": {
    ...             "node3": "10.0.0.2",
    ...             "node7": "10.0.0.9",
    ...         },
    ...         "nodes": "${oc.dict.keys: workers}",
    ...         "ips": "${oc.dict.values: workers}",
    ...     }
    ... )
    >>> # Keys are copied from the DictConfig:
    >>> show(cfg.nodes)
    type: ListConfig, value: ['node3', 'node7']
    >>> # Values are dynamically fetched through interpolations:
    >>> show(cfg.ips)
    type: ListConfig, value: ['${workers.node3}', '${workers.node7}']
    >>> assert cfg.ips == ["10.0.0.2", "10.0.0.9"]

.. _clearing_resolvers:

Clearing/removing resolvers
---------------------------

.. _clear_resolvers:

clear_resolvers
^^^^^^^^^^^^^^^

Use ``OmegaConf.clear_resolvers()`` to remove all resolvers except the built-in resolvers (like ``oc.env`` etc).

.. code-block:: python

    def clear_resolvers() -> None

In the following example, first we register a new custom resolver ``str.lower``, and then clear all
custom resolvers.

.. doctest::

    >>> # register a new resolver: str.lower
    >>> OmegaConf.register_new_resolver(
    ...     name='str.lower',
    ...     resolver=lambda x: str(x).lower(),
    ... )
    >>> # check if resolver exists (after adding, before removal)
    >>> OmegaConf.has_resolver("str.lower")
    True
    >>> # clear all custom-resolvers
    >>> OmegaConf.clear_resolvers()
    >>> # check if resolver exists (after removal)
    >>> OmegaConf.has_resolver("str.lower")
    False
    >>> # default resolvers are not affected
    >>> OmegaConf.has_resolver("oc.env")
    True

.. _clear_resolver:

clear_resolver
^^^^^^^^^^^^^^

Use ``OmegaConf.clear_resolver()`` to remove a single resolver (including built-in resolvers).

.. code-block:: python

    def clear_resolver(name: str) -> bool


``OmegaConf.clear_resolver()`` returns True if the resolver was found and removed, and False otherwise.

Here is an example.

.. doctest::

    >>> OmegaConf.has_resolver("oc.env")
    True
    >>> # This will remove the default resolver: oc.env
    >>> OmegaConf.clear_resolver("oc.env")
    True
    >>> OmegaConf.has_resolver("oc.env")
    False
