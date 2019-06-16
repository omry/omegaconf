.. testsetup:: *

    import os
    from omegaconf import OmegaConf

Interpolation
=============

OmegaConf supports interpolation of strings using either parts of the config and using environment variables.

String interpolation
^^^^^^^^^^^^^^^^^^^^

We will use this simple **interpolation.yaml** file in the example:

.. include:: interpolation.yaml
   :code: yaml

Let's load it and take a look:

.. doctest::

    >>> conf = OmegaConf.load('source/interpolation.yaml')
    >>> conf.database_client.server_port
    1234

If you pretty print you get the source yaml file, but when you access a field it resolves at runtime.

.. doctest::

    >>> print(conf.pretty())
    database_client:
      server_port: ${database_server.port}
    database_server:
      port: 1234
    <BLANKLINE>

Interpolation can also construct complex strings:

.. include:: interpolation2.yaml
   :code: yaml


.. doctest::

    >>> conf = OmegaConf.load('source/interpolation2.yaml')
    >>> conf.experiment.path
    '/var/experiments/fire_the_nuke'

Standard resolvers library
==========================

The following resolvers are supported:

Environment variable resolver
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
.. include:: interpolation3.yaml
   :code: yaml

Let's test it:

.. doctest::

    >>> os.environ['user'] = 'omry'
    >>> conf = OmegaConf.load('source/interpolation3.yaml')
    >>> conf.experiment.path
    '/var/experiments/omry'

Plugable resolves
^^^^^^^^^^^^^^^^^
You can add easily add your own resolvers:
let's say we want a resolver that adds 10 the the given value.
The value 999 will be passed to the plus_10 lambda, and the int 1000 will be returned.

.. doctest::

    >>> OmegaConf.register_resolver("plus_10", lambda x: int(x) + 10)
    >>> c = OmegaConf.create({'key': '${plus_10:990}'})
    >>> c.key
    1000

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
