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
Note that the cache is based on the string literals representing the resolver's inputs, and not
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

- ``_parent_``: the parent node of an interpolation.
- ``_root_``: The config root.

This can be achieved by adding the special parameters to the resolver signature.
Note that special parameters must be defined as named keywords (after the `*`).

In the example below, we use ``_parent_`` to implement a sum function that defaults to 0 if the node does not exist.
(In contrast to the sum we defined earlier where accessing an invalid key, e.g. ``"a_plus_z": ${sum:${a}, ${z}}`` would result in an error).

.. doctest::

    >>> def sum2(a, b, *, _parent_):
    ...     return _parent_.get(a, 0) + _parent_.get(b, 0)
    >>> OmegaConf.register_new_resolver("sum2", sum2, use_cache=False)
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
In such a case, the default value is converted to a string using ``str(default)``, unless it is ``null`` (representing Python ``None``) - in which case ``None`` is returned. 

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
The following example combines ``oc.create`` with ``oc.decode`` and ``oc.env`` to generate
a sub-config from an environment variable:

.. doctest::

    >>> cfg = OmegaConf.create(
    ...     {
    ...         "model": "${oc.create:${oc.decode:${oc.env:MODEL}}}",
    ...     }
    ... )
    >>> os.environ["MODEL"] = "{name: my_model, layer_size: [100, 200]}"
    >>> show(cfg.model.layer_size)
    type: ListConfig, value: [100, 200]


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

With ``oc.decode``, strings can be converted into their corresponding data types using the OmegaConf grammar.
This grammar recognizes typical data types like ``bool``, ``int``, ``float``, ``dict`` and ``list``,
e.g. ``"true"``, ``"1"``, ``"1e-3"``, ``"{a: b}"``, ``"[a, b, c]"``.
It will also resolve interpolations like ``"${foo}"``, returning the corresponding value of the node.

Note that:

- When providing as input to ``oc.decode`` a string that is meant to be decoded into another string, in general
  the input string should be quoted (since only a subset of characters are allowed by the grammar in unquoted
  strings). For instance, a proper string interpolation could be: ``"'Hi! My name is: ${name}'"`` (with extra quotes).
- ``None`` (written as ``null`` in the grammar) is the only valid non-string input to ``oc.decode`` (returning ``None`` in that case)

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


.. _oc.dict.{keys,values}:

oc.dict.{keys,value}
^^^^^^^^^^^^^^^^^^^^

Some config options that are stored as a ``DictConfig`` may sometimes be easier to manipulate as lists,
when we care only about the keys or the associated values.

The resolvers ``oc.dict.keys`` and ``oc.dict.values`` simplify such operations by offering an alternative
view of a dictionary's keys or values as a list.
They take as input a string that is the path to another config node (using the same syntax
as interpolations) and return a ``ListConfig`` with its keys / values.

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
