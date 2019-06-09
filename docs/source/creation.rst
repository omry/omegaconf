.. _creation:

Creating
========

.. testsetup:: *

    from omegaconf import OmegaConf
    import io
    import os

Empty config
------------
.. doctest::

    >>> conf = OmegaConf.empty()
    >>> conf.a = {'key' :'value'}
    >>> conf
    {'a': {'key': 'value'}}


From a dictionary
-----------------
.. doctest::

    >>> conf1 = OmegaConf.from_dict({'a':2, 'b':1})
    >>> conf1
    {'a': 2, 'b': 1}
    >>> conf2 = OmegaConf.from_dict(dict(a=2, b=1))
    >>> conf2
    {'a': 2, 'b': 1}


From filename
-------------
.. doctest::

    >>> conf = OmegaConf.from_filename('source/example.yaml')

From file
---------


.. doctest::

    >>> file = io.open('source/example.yaml', 'r')
    >>> conf = OmegaConf.from_file(file)


From CLI arguments
------------------
from_cli() will parse anything in sys.argv.
Note that if you want to use this with a CLI parser, it will have to clear anything it already parsed from
sys.argv before you initialize the conf from_cli().

.. doctest::

    >>> conf = OmegaConf.from_cli()

