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

    >>> conf = OmegaConf.from_filename('source/interpolation.yaml')
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

    >>> conf = OmegaConf.from_filename('source/interpolation2.yaml')
    >>> conf.experiment.path
    '/var/experiments/fire_the_nuke'

Environment variables interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to resolving using other parts of the config, OmegaConf also support using environment variables with the
env: prefix in the interpolated value.


.. include:: interpolation3.yaml
   :code: yaml

Let's test it:

.. doctest::

    >>> os.environ['user'] = 'omry'
    >>> conf = OmegaConf.from_filename('source/interpolation3.yaml')
    >>> conf.experiment.path
    '/var/experiments/omry'


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
