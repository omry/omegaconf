.. testsetup:: *

    from omegaconf import OmegaConf

Usage
=====

Installation
^^^^^^^^^^^^
Just pip install::

    pip install omegaconf


Basic example
^^^^^^^^^^^^^
Let's say we have an example.yaml file:

.. include:: example.yaml
   :code: yaml


The following program would load it:

.. testcode::

    from omegaconf import OmegaConf

    conf = OmegaConf.from_filename('source/example.yaml')
    print(conf.server.port)
    print(conf['log'])


Output:

.. testoutput::

    8080
    {'file': 'log.txt', 'rotation': 3600}


Overriding configuration
^^^^^^^^^^^^^^^^^^^^^^^^
OmegaConf supports overriding configuraitons easily, let's say you have a file with the perfect
configuration, you want to use that but you want to make just a few small changes.

.. testcode::

    conf = OmegaConf.from_filename('source/example.yaml')
    conf.update('server.port', 8081)
    print(conf.server.port)

Output:

.. testoutput::

    8081

You could also merge whole config files:

Base file, example.yaml:

.. include:: example.yaml
   :code: yaml

Overriding file example2.yaml:

.. include:: example2.yaml
   :code: yaml

.. testcode::

    conf1 = OmegaConf.from_filename('source/example.yaml')
    conf2 = OmegaConf.from_filename('source/example2.yaml')
    conf = OmegaConf.merge(conf1, conf2)
    print(conf.server.port)
    print(conf.log.file)
    print(conf.log.rotation)

Output:

.. testoutput::

    8081
    /tmp/log.txt
    3600
