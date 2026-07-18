.. _tuple_migration_24:

Migrating tuple usage in OmegaConf 2.4
======================================

OmegaConf 2.4 changes how native Python tuples are represented. Earlier
versions converted tuples to mutable ``ListConfig`` objects. OmegaConf 2.4
preserves tuple identity by creating structurally immutable ``TupleConfig``
objects instead.

.. important::

    This is a breaking change. Code that assumes every OmegaConf sequence is a
    ``ListConfig``, or that mutates values created from Python tuples, may need
    to be updated.

What changed
------------

Given the following input:

.. code-block:: python

    cfg = OmegaConf.create({"coords": (1, 2)})

Earlier OmegaConf versions produced a ``ListConfig`` for ``cfg.coords`` and
allowed operations such as ``append()`` and item assignment. OmegaConf 2.4
produces a ``TupleConfig`` instead:

.. code-block:: python

    assert OmegaConf.is_tuple(cfg.coords)
    assert OmegaConf.is_sequence(cfg.coords)
    assert not OmegaConf.is_list(cfg.coords)

Like a native Python tuple, a ``TupleConfig`` does not allow elements to be
inserted, removed, or replaced. Nested mutable containers remain mutable.
``OmegaConf.to_container()`` also converts a ``TupleConfig`` back to a native
tuple rather than a list.

Choosing the intended sequence type
-----------------------------------

If the value should be mutable, use a list explicitly:

.. code-block:: python

    cfg = OmegaConf.create({"coords": list(source_tuple)})
    assert OmegaConf.is_list(cfg.coords)
    cfg.coords.append(3)

For Structured Configs, annotate mutable sequences as ``list[T]`` or
``typing.List[T]``.

If the value is conceptually a tuple, keep the tuple input or use a tuple
annotation. Treat the resulting ``TupleConfig`` as immutable and replace the
complete value through its mutable parent when an update is required:

.. code-block:: python

    cfg = OmegaConf.create({"coords": (1, 2)})
    cfg.coords = (1, 2, 3)

The untyped tuple in this example has the variadic type ``Tuple[Any, ...]``,
so its replacement may have a different arity. A fixed annotation such as
``tuple[int, int]`` requires replacements to contain exactly two elements,
while a variadic annotation such as ``tuple[int, ...]`` permits the arity to
change.

For Structured Configs, ``tuple[T1, T2]`` and ``typing.Tuple[T1, T2]`` define
fixed positional types, while ``tuple[T, ...]`` and ``typing.Tuple[T, ...]``
define a homogeneous tuple of arbitrary length.

Checking sequence types
-----------------------

Choose the helper that matches the behavior your code requires:

* Use ``OmegaConf.is_tuple(value)`` for tuple-specific behavior.
* Use ``OmegaConf.is_list(value)`` for mutable-list-specific behavior.
* Use ``OmegaConf.is_sequence(value)`` when either ``ListConfig`` or
  ``TupleConfig`` is accepted.

Code that previously used ``isinstance(value, ListConfig)`` or only
``OmegaConf.is_list(value)`` for general sequence handling should normally use
``OmegaConf.is_sequence(value)`` instead.

Migration checklist
-------------------

When upgrading to OmegaConf 2.4, review code that:

* accepts or recursively processes only ``list`` and ``ListConfig`` inputs;
* uses ``OmegaConf.is_list()`` for generic indexed traversal or other sequence
  behavior that should also apply to tuples;
* constructs sequences incrementally with operations such as ``append()`` or
  item assignment, which are not supported by ``TupleConfig``; or
* expects tuple-valued inputs to reach callables or tests as ``ListConfig`` or
  ``list``. They now remain ``TupleConfig`` unless converted, and conversion
  produces a native ``tuple``.

Tuple semantics are experimental in OmegaConf 2.4. Feedback is welcome on
`GitHub issue #392 <https://github.com/omry/omegaconf/issues/392>`_.
