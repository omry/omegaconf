.. testsetup:: *

    from omegaconf import OmegaConf

.. testsetup:: loaded

    from omegaconf import OmegaConf
    conf = OmegaConf.from_filename('source/example.yaml')

Usage
=====

Installation
^^^^^^^^^^^^
Just pip install::

    pip install omegaconf


Basic example
^^^^^^^^^^^^^
We will use this simple **example.yaml** file:

.. include:: example.yaml
   :code: yaml

Loading:
--------

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> conf = OmegaConf.from_filename('source/example.yaml')
    >>> conf
    {'server': {'port': 80}, 'log': {'file': 'log.txt', 'rotation': 3600}}

Reading values:
---------------

.. doctest:: loaded

    >>> # Object style access
    >>> conf.server.port
    80
    >>> # Map style access
    >>> conf['log']
    {'file': 'log.txt', 'rotation': 3600}

Reading with default values:
----------------------------

.. doctest:: loaded

    >>> conf.missing_key or 'a default value'
    'a default value'
    >>> conf.get('missing_key', 'a default value')
    'a default value'

Manipulating config:
--------------------

.. doctest:: loaded

    >>> # Changing existing keys
    >>> conf.server.port = 81
    >>> # Adding new keys
    >>> conf.server.hostname = "localhost"
    >>> # Or new sections
    >>> conf.database = {'hostname': 'database01', 'port': 3306}






