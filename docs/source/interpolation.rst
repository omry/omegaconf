.. testsetup:: *

    import os
    from omegaconf import OmegaConf

Interpolation
=============

While YAML supports anchors this does not work well for OmegaConf
as we are composing yaml files dynamically and such referencing should be delayed until we are done
composing the configuration.

OmegaConf supports interpolation using values from other part of the configuration tree.

String interpolation
^^^^^^^^^^^^^^^^^^^^


We will use this simple **interpolation.yaml** file in the example:

.. include:: interpolation.yaml
   :code: yaml


Let's load it and take a look:

.. doctest::

    >>> conf = OmegaConf.from_filename('source/interpolation.yaml')
    >>> print(conf.pretty())
    database_client:
      server_port: ${database_server.port}
    database_server:
      port: 1234
    <BLANKLINE>

Note that the client port is not resolved yet, this gives us a change to only do it when it gets it's final value.
For example, we may want to allow overriding things from the command line, and we should only resolve once everything
got it's final value.

.. doctest::

    >>> conf.resolve()
    >>> print(conf.pretty())
    database_client:
      server_port: 1234
    database_server:
      port: 1234
    <BLANKLINE>

OmegaConf supports full string interpolation, for example:

.. include:: interpolation2.yaml
   :code: yaml

.. doctest::

    >>> conf = OmegaConf.from_filename('source/interpolation2.yaml')
    >>> conf.resolve()
    >>> print(conf.pretty())
    experiment:
      name: fire_the_nuke
      path: /var/experiments/fire_the_nuke
    <BLANKLINE>


Environment variables interpolation
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

In addition to the above string interpolation, OmegaConf also support environment variable interpolation.


.. include:: interpolation3.yaml
   :code: yaml

We can test it by simulating an environment variable:

.. doctest::

    >>> os.environ['user'] = 'omry'
    >>> conf = OmegaConf.from_filename('source/interpolation3.yaml')
    >>> conf.resolve()
    >>> print(conf.pretty())
    experiment:
      path: /var/experiments/omry
    <BLANKLINE>


* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
