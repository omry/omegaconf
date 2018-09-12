Merging
=======
Configuration can be created from various sources, like YAML files, CLI arguments and more.

see :doc:`creation` for more details.

You can combine configurations, regardless of their source.

Here are a few examples where you might want to merge different configurations:

- You want to use more than one configuration file but access them uniformly through the same object
- You want to override some configuration in a file with that from another file
- You want to override configuration using command line arguments or environment variables

Merging two files
-----------------

We will use two config files:

**example.yaml** file:

.. include:: example.yaml
   :code: yaml


**example2.yaml** file:

.. include:: example2.yaml
   :code: yaml


.. doctest::

    >>> from omegaconf import OmegaConf
    >>> conf1 = OmegaConf.from_filename('source/example.yaml')
    >>> conf2 = OmegaConf.from_filename('source/example2.yaml')
    >>> conf = OmegaConf.merge(conf1, conf2)
    >>> conf.server.port
    81
    >>> conf.database
    {'port': 3306, 'host': 'dbhost'}

Merging file with CLI args
--------------------------
Now let's try overriding conf1 above with parameters from the command line:
For simplicity, we will simulate command line arguments by setting sys.argv.

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> import sys
    >>> conf1 = OmegaConf.from_filename('source/example.yaml')
    >>> # Simulate command line arguments
    >>> sys.argv = ['program.py', 'server.port=82', 'log.file=log2.txt']
    >>> cli = OmegaConf.from_cli()
    >>> conf = OmegaConf.merge(conf1, cli)
    >>> conf.server.port
    82
    >>> conf.log.file
    'log2.txt'


Putting it all together
-----------------------
Let's say you want the following structure:
A file acting as a base configuration, environment variables overriding that file, and command line arguments overriding both.

.. doctest::

    >>> from omegaconf import OmegaConf
    >>> conf = OmegaConf.from_filename('source/example.yaml')
    >>> cli = OmegaConf.from_cli()
    >>> # Note that for environment we need a whitelist
    >>> # specifying what can be overridden
    >>> env = OmegaConf.from_env(whitelist=['server.port'])
    >>> conf = OmegaConf.merge(conf, env, cli)




