=============
How-To Guides
=============

.. contents::
   :local:

How to Perform Arithmetic Using ``eval`` as a Resolver
------------------------------------------------------

Sometimes it is necessary to perform arithmetic based on settings from your app's config.
You can register Python's `builtins.eval`_ function as a :ref:`resolver<resolvers>`
to perform simple computations.

.. _builtins.eval: https://docs.python.org/3/library/functions.html#eval

First, register the ``builtins.eval`` function as a new resolver:

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> OmegaConf.register_new_resolver("eval", eval)

Now, define a config and perform some arithmetic using the ``eval`` resolver:

.. tabs::

    .. tab:: yaml

        .. doctest::

            >>> yaml_data = """
            ... ten_squared: ${eval:'10 ** 2'}
            ... """
            >>> cfg = OmegaConf.create(yaml_data)
            >>> assert cfg.ten_squared == 100

    .. tab:: python

        .. doctest::

            >>> cfg = OmegaConf.create({
            ...     "ten_squared": "${eval:'10 ** 2'}",
            ... })
            >>> assert cfg.ten_squared == 100

You can use :ref:`nested interpolation<nested-interpolation>` to perform computation that involves other values from your config:

.. tabs::

    .. tab:: yaml

        .. doctest::

            >>> yaml_data = """
            ... side_1: 5
            ... side_2: 6
            ... rectangle_area: ${eval:'${side_1} * ${side_2}'}
            ... """
            >>> cfg = OmegaConf.create(yaml_data)
            >>> assert cfg.rectangle_area == 30

    .. tab:: python

        .. doctest::

            >>> cfg = OmegaConf.create({
            ...     "side_1": 5,
            ...     "side_2": 6,
            ...     "rectangle_area": "${eval:'${side_1} * ${side_2}'}",
            ... })
            >>> assert cfg.rectangle_area == 30

To pass string data to ``eval``, you'll need to use a nested pair of quotes:

.. tabs::

    .. tab:: yaml

        .. doctest::

            >>> yaml_data = """
            ... cow_say: moo
            ... three_cows: ${eval:'3 * "${cow_say}"'}
            ... """
            >>> cfg = OmegaConf.create(yaml_data)
            >>> assert cfg.three_cows == "moomoomoo"

    .. tab:: python

        .. doctest::

            >>> cfg = OmegaConf.create({
            ...   "cow_say": "moo",
            ...   "three_cows": """${eval:'3 * "${cow_say}"'}"""
            ... })
            >>> assert cfg.three_cows == "moomoomoo"

The double quotes around ``"${cow_say}"`` guarantee that ``eval`` will
interpret ``"moo"`` as a string instead of as a variable ``moo``. See
:ref:`escaping-in-interpolation-strings` for more information.

For more complicated logic, you should consider defining a specialized resolver
to encapsulate the computation, rather than relying on the general capabilities
of ``eval``. Follow the examples from the :ref:`custom_resolvers` docs.
