.. _structured_configs:

.. testsetup:: *

    from omegaconf import *
    from enum import Enum
    from dataclasses import dataclass, field
    import os
    import pathlib
    from pytest import raises
    from typing import Dict, Any
    import sys
    os.environ['USER'] = 'omry'

Structured configs
------------------
Structured configs are used to create OmegaConf configuration object with runtime type safety.
In addition, they can be used with tools like mypy or your IDE for static type checking.

Two types of structures classes are supported: dataclasses and attr classes.

- `dataclasses <https://docs.python.org/3.7/library/dataclasses.html>`_ are standard as of Python 3.7 or newer and are available in Python 3.6 via the `dataclasses` pip package.
- `attrs <https://github.com/python-attrs/attrs>`_  Offset slightly cleaner syntax in some cases but depends on the attrs pip package.

This documentation will use dataclasses, but you can use the annotation ``@attr.s(auto_attribs=True)`` from attrs instead of ``@dataclass``.

Basic usage involves passing in a structured config class or instance to ``OmegaConf.structured()``, which will return an OmegaConf config that matches
the values and types specified in the input. At runtine, OmegaConf will validate modifications to the created config object against the schema specified
in the input class.


Currently, type hints supported in OmegaConf’s structured configs include:
 - primitive types (``int``, ``float``, ``bool``, ``str``, ``Path``) and enum types
   (user-defined subclasses of ``enum.Enum``). See the :ref:`simple_types` section below.
 - unions of primitive/enum types, e.g. ``Union[float, bool, MyEnum]``.
   See :ref:`union_types` below.
 - structured config fields (i.e. MyConfig.x can have type hint MySubConfig).
   See the :ref:`nesting_structured_configs` section below.
 - dict and list types: ``typing.Dict[K, V]`` or ``typing.List[V]``, where K is
   primitive or enum, and where V is any of the above (including nested dicts
   or lists, e.g. ``Dict[str, List[int]]``).
   See the :ref:`lists` and :ref:`dictionaries` sections below.
 - optional types (any of the above can be wrapped in a ``typing.Optional[...]``
   annotation). See :ref:`other_special_features` below.

.. _simple_types:

Simple types
^^^^^^^^^^^^
Simple types include
 - ``int``: numeric integers
 - ``float``: numeric floating point values
 - ``bool``: boolean values (True, False, On, Off etc)
 - ``str``: any string
 - ``bytes``: an immutable sequence of numbers in [0, 255]
 - ``pathlib.Path``: filesystem paths as represented by python's standard library ``pathlib``
 - ``Enums``: User defined enums

The following class defines fields with all simple types:

.. doctest::

    >>> class Height(Enum):
    ...     SHORT = 0
    ...     TALL = 1

    >>> @dataclass
    ... class SimpleTypes:
    ...     num: int = 10
    ...     pi: float = 3.1415
    ...     is_awesome: bool = True
    ...     height: Height = Height.SHORT
    ...     description: str = "text"
    ...     data: bytes = b"bin_data"
    ...     path: pathlib.Path = pathlib.Path("hello.txt")

You can create a config based on the SimpleTypes class itself or an instance of it.
Those would be equivalent by default, but the Object variant allows you to set the values of specific
fields during construction.

.. doctest::

    >>> conf1 = OmegaConf.structured(SimpleTypes)
    >>> conf2 = OmegaConf.structured(SimpleTypes())
    >>> # The two configs are identical in this case
    >>> assert conf1 == conf2
    >>> # But the second form allow for easy customization of the values:
    >>> conf3 = OmegaConf.structured(
    ...   SimpleTypes(num=20,
    ...   height=Height.TALL))
    >>> print(OmegaConf.to_yaml(conf3))
    num: 20
    pi: 3.1415
    is_awesome: true
    height: TALL
    description: text
    data: !!binary |
      YmluX2RhdGE=
    path: !!python/object/apply:pathlib.PosixPath
    - hello.txt
    <BLANKLINE>

The resulting object is a regular OmegaConf ``DictConfig``, except that it will utilize the type information in the input class/object
and will validate the data at runtime.
The resulting object and will also rejects attempts to access or set fields that are not already defined
(similarly to configs with their to :ref:`struct-flag` set, but not recursive).

.. doctest::

    >>> conf = OmegaConf.structured(SimpleTypes)
    >>> with raises(AttributeError):
    ...    conf.does_not_exist


Static type checker support
^^^^^^^^^^^^^^^^^^^^^^^^^^^
Python type annotation can be used by static type checkers like Mypy/Pyre or by IDEs like PyCharm.

.. doctest::

    >>> conf: SimpleTypes = OmegaConf.structured(SimpleTypes)
    >>> # Passes static type checking
    >>> conf.description = "text"
    >>> # Fails static type checking (but will also raise a Validation error)
    >>> with raises(ValidationError):
    ...     conf.num = "foo"

This is duck-typing; the actual object type of ``conf`` is ``DictConfig``. You can access the underlying
type using ``OmegaConf.get_type()``:

.. doctest::
    
    >>> type(conf).__name__
    'DictConfig'

    >>> OmegaConf.get_type(conf).__name__
    'SimpleTypes'



Runtime type validation and conversion
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
OmegaConf supports merging configs together, as well as overriding from the command line.
This means some mistakes can not be identified by static type checkers, and runtime validation is required.

.. doctest::

    >>> # This is okay, the string "100" can be converted to an int
    >>> # Note that static type checkers will not like it and you should
    >>> # avoid such explicit mistyped assignments.
    >>> conf.num = "100"
    >>> assert conf.num == 100

    >>> with raises(ValidationError):
    ...     # This will fail at runtime because num is an int
    ...     # and foo cannot be converted to an int
    ...     # Note that the static type checker can't help here.
    ...     conf.merge_with_dotlist(["num=foo"])

Runtime validation and conversion works for all supported types, including Enums:

.. doctest::

    >>> conf.height = Height.TALL
    >>> assert conf.height == Height.TALL

    >>> # The name of Height.TALL is TALL
    >>> conf.height = "TALL"
    >>> assert conf.height == Height.TALL

    >>> # This works too
    >>> conf.height = "Height.TALL"
    >>> assert conf.height == Height.TALL

    >>> # The ordinal of Height.TALL is 1
    >>> conf.height = 1
    >>> assert conf.height == Height.TALL

.. _nesting_structured_configs:

Nesting structured configs
^^^^^^^^^^^^^^^^^^^^^^^^^^

Structured configs can be nested.

.. doctest::

    >>> @dataclass
    ... class User:
    ...     # A simple user class with two missing fields
    ...     name: str = MISSING
    ...     height: Height = MISSING
    >>>
    >>> @dataclass
    ... class DuperUser(User):
    ...     duper: bool = True
    ...
    >>> # Group class contains two instances of User.
    >>> @dataclass
    ... class Group:
    ...     name: str = MISSING
    ...     # data classes can be nested
    ...     admin: User = User()
    ...
    ...     # You can also specify different defaults for nested classes
    ...     manager: User = User(name="manager", height=Height.TALL)

    >>> conf: Group = OmegaConf.structured(Group)
    >>> print(OmegaConf.to_yaml(conf))
    name: ???
    admin:
      name: ???
      height: ???
    manager:
      name: manager
      height: TALL
    <BLANKLINE>

OmegaConf will validate that assignment of nested objects is of the correct type:

.. doctest::

    >>> with raises(ValidationError):
    ...     conf.manager = 10

You can assign subclasses:

.. doctest::

    >>> conf.manager = DuperUser()
    >>> assert conf.manager.duper == True


.. _lists:

Lists
^^^^^
Structured Config fields annotated with ``typing.List`` or ``typing.Tuple`` can hold any type
supported by OmegaConf (``int``, ``float``. ``bool``, ``str``, ``bytes``, ``pathlib.Path``, ``Enum`` or Structured configs).

.. doctest::

    >>> from dataclasses import dataclass, field
    >>> from typing import List, Tuple
    >>> @dataclass
    ... class User:
    ...     name: str = MISSING

    >>> @dataclass
    ... class ListsExample:
    ...     # Typed list can hold Any, int, float, bool, str,
    ...     # bytes, pathlib.Path and Enums as well as arbitrary Structured configs.
    ...     ints: List[int] = field(default_factory=lambda: [10, 20, 30])
    ...     bools: Tuple[bool, bool] = field(default_factory=lambda: (True, False))
    ...     users: List[User] = field(default_factory=lambda: [User(name="omry")])

OmegaConf verifies at runtime that your Lists contains only values of the correct type.
In the example below, the OmegaConf object ``conf`` (which is actually an instance of ``DictConfig``) is duck-typed as ``ListExample``.

.. doctest::

    >>> conf: ListsExample = OmegaConf.structured(ListsExample)

    >>> # Okay, 10 is an int
    >>> conf.ints.append(10)
    >>> # Okay, "20" can be converted to an int
    >>> conf.ints.append("20")

    >>> conf.bools.append(True)
    >>> conf.users.append(User(name="Joe"))
    >>> # Not okay, 10 cannot be converted to a User
    >>> with raises(ValidationError):
    ...     conf.users.append(10)

.. _dictionaries:

Dictionaries
^^^^^^^^^^^^
Dictionaries are supported via annotation of structured config fields with ``typing.Dict``.
Keys must be typed as one of ``str``, ``int``, ``Enum``, ``float``, ``bytes``, or ``bool``. Values can
be any of the types supported by OmegaConf (``Any``, ``int``, ``float``, ``bool``, ``bytes``,
``pathlib.Path``, ``str`` and ``Enum`` as well as arbitrary Structured configs)

.. doctest::

    >>> from dataclasses import dataclass, field
    >>> from typing import Dict
    >>> @dataclass
    ... class DictExample:
    ...     ints: Dict[str, int] = field(default_factory=lambda: {"a": 10, "b": 20, "c": 30})
    ...     bools: Dict[str, bool] = field(default_factory=lambda: {"Uno": True, "Zoro": False})
    ...     users: Dict[str, User] = field(default_factory=lambda: {"omry": User(name="omry")})

Like with Lists, the types of values contained in Dicts are verified at runtime.

.. doctest::

    >>> conf: DictExample = OmegaConf.structured(DictExample)

    >>> # Okay, correct type is assigned
    >>> conf.ints["d"] = 10
    >>> conf.bools["Dos"] = True
    >>> conf.users["James"] = User(name="Bond")

    >>> # Not okay, 10 cannot be assigned to a User
    >>> with raises(ValidationError):
    ...     conf.users["Joe"] = 10

.. _nested_dict_and_list_annotations:

Nested dict and list annotations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Dict and List annotations can be nested flexibly:

.. doctest::

    >>> @dataclass
    ... class NestedContainers:
    ...     dict_of_dict: Dict[str, Dict[str, int]]
    ...     list_of_list: List[List[int]] = field(default_factory=lambda: [[123]])
    ...     dict_of_list: Dict[str, List[int]] = MISSING
    ...     list_of_dict: List[Dict[str, int]] = MISSING
    ... 
    ... 
    >>> cfg = OmegaConf.structured(NestedContainers(dict_of_dict={"foo": {"bar": 123}}))
    >>> print(OmegaConf.to_yaml(cfg))
    dict_of_dict:
      foo:
        bar: 123
    list_of_list:
    - - 123
    dict_of_list: ???
    list_of_dict: ???
    <BLANKLINE>
    >>> with raises(ValidationError):
    ...     cfg.list_of_dict = [["whoops"]]  # not a list of dicts

.. _union_types:

Unions
^^^^^^

You can use `typing.Union <https://docs.python.org/3/library/typing.html#typing.Union>`_
to annotate unions of :ref:`simple_types`. 

.. doctest::

    >>> from typing import Union
    >>>
    >>> @dataclass
    ... class HasUnion:
    ...     u: Union[float, bool] = 10.1
    ...
    >>> cfg = OmegaConf.structured(HasUnion)
    >>> assert cfg.u == 10.1
    >>> cfg.u = True  # ok
    >>> cfg.u = b"binary"  # bytes not compatible with union
    Traceback (most recent call last):
    ...
    omegaconf.errors.ValidationError: Cannot assign 'b'binary'' of type 'bytes' to Union[float, bool]
        full_key: u
        object_type=HasUnion
    >>> OmegaConf.structured(HasUnion("abc"))  # str not compatible
    Traceback (most recent call last):
    ...
    omegaconf.errors.ValidationError: Cannot assign 'abc' of type 'str' to Union[float, bool]
        full_key: u
        object_type=None

If any argument of a ``Union`` type hint is ``Optional``, the *whole*
union is considered optional. For example, OmegaConf treats all four of the
following type hints as equivalent:

- ``Optional[Union[int, str]]``
- ``Union[Optional[int], str]``
- ``Union[int, str, None]``
- ``Union[int, str, type(None)]``

Ordinarily, assignment to a structured config field results in coercion of the
assigned value to the field's type. For example, assigning an integer to a
field typed as ``str`` results in the integer being coverted to a string:

.. doctest::

    >>> @dataclass
    ... class HasStr:
    ...     s: str
    ...
    >>> cfg = OmegaConf.structured(HasStr)
    >>> cfg.s = 10.1
    >>> assert cfg.s == "10.1"  # The assigned value has been converted to a string

When dealing with ``Union`` types, however, conversion is disabled so as to
avoid ambiguity. Values assigned to a union-typed field of a structured config
must precisely match one of the types in the ``Union`` annotation:

.. doctest::

    >>> @dataclass
    ... class StrOrInt:
    ...     u: Union[str, float]
    ...
    >>> cfg = OmegaConf.structured(StrOrInt)
    >>> cfg.u = 10.1
    >>> assert cfg.u == 10.1  # The assigned value remains a `float`.
    >>> cfg.u = "10.1"
    >>> assert cfg.u == "10.1"  # The assigned value remains a `str`.
    >>> cfg.u = 123  # Conversion from `int` to `float` does not occur.
    Traceback (most recent call last):
    ...
    omegaconf.errors.ValidationError: Value '123' of type 'int' is incompatible with type hint 'Union[str, float]'
        full_key: u
        object_type=StrOrInt


.. _other_special_features:

Other special features
^^^^^^^^^^^^^^^^^^^^^^
OmegaConf supports field modifiers such as ``MISSING`` and ``Optional``.

.. doctest::

    >>> from typing import Optional
    >>> from omegaconf import MISSING

    >>> @dataclass
    ... class Modifiers:
    ...     num: int = 10
    ...     optional_num: Optional[int] = 10
    ...     another_num: int = MISSING
    ...     optional_dict: Optional[Dict[str, int]] = None
    ...     list_optional: List[Optional[int]] = field(default_factory=lambda: [10, MISSING, None])

    >>> conf: Modifiers = OmegaConf.structured(Modifiers)

Note for Python3.6 users: :ref:`pickling <save_and_load_pickle_file>`
structured configs with complex type annotations, such as dict-of-list or
list-of-optional, is not supported.

Mandatory missing values
++++++++++++++++++++++++

Fields assigned the constant ``MISSING`` do not have a value and the value must be set prior to accessing the field.
Otherwise a ``MissingMandatoryValue`` exception is raised.

.. doctest::

    >>> with raises(MissingMandatoryValue):
    ...     x = conf.another_num
    >>> conf.another_num = 20
    >>> assert conf.another_num == 20


Optional fields
+++++++++++++++

.. doctest::

    >>> with raises(ValidationError):
    ...     # regular fields cannot be assigned None
    ...     conf.num = None

    >>> conf.optional_num = None
    >>> assert conf.optional_num is None
    >>> assert conf.list_optional[2] is None



Interpolations
++++++++++++++

:ref:`interpolation` works normally with Structured configs, but static type checkers may object to you assigning a string to another type.
To work around this, use the special functions ``omegaconf.SI`` and ``omegaconf.II`` described below.

.. doctest::

    >>> from omegaconf import SI, II
    >>> @dataclass
    ... class Interpolation:
    ...     val: int = 100
    ...     # This will work, but static type checkers will complain
    ...     a: int = "${val}"
    ...     # This is equivalent to the above, but static type checkers
    ...     # will not complain
    ...     b: int = SI("${val}")
    ...     # This is syntactic sugar; the input string is
    ...     # wrapped with ${} automatically.
    ...     c: int = II("val")

    >>> conf: Interpolation = OmegaConf.structured(Interpolation)
    >>> assert conf.a == 100
    >>> assert conf.b == 100
    >>> assert conf.c == 100


Interpolated values are validated, and converted when possible, to the annotated type when the interpolation is accessed, e.g:

.. doctest::

    >>> from omegaconf import II
    >>> @dataclass
    ... class Interpolation:
    ...     str_key: str = "string"
    ...     int_key: int = II("str_key")

    >>> cfg = OmegaConf.structured(Interpolation)
    >>> cfg.int_key  # fails due to type mismatch
    Traceback (most recent call last):
      ...
    omegaconf.errors.InterpolationValidationError: Value 'string' could not be converted to Integer
        full_key: int_key
        object_type=Interpolation
    >>> cfg.str_key = "1234"  # string value
    >>> assert cfg.int_key == 1234  # automatically convert str to int

Note however that this validation step is currently skipped for container node interpolations:

.. doctest::

    >>> @dataclass
    ... class NotValidated:
    ...     some_int: int = 0
    ...     some_dict: Dict[str, str] = II("some_int")

    >>> cfg = OmegaConf.structured(NotValidated)
    >>> assert cfg.some_dict == 0  # type mismatch, but no error


Frozen classes
++++++++++++++

Frozen dataclasses and attr classes are supported via OmegaConf :ref:`read-only-flag`, which makes the entire config node and all if it's child nodes read-only.

.. doctest::

    >>> from dataclasses import dataclass, field
    >>> from typing import List
    >>> @dataclass(frozen=True)
    ... class FrozenClass:
    ...     x: int = 10
    ...     list: List = field(default_factory=lambda: [1, 2, 3])

    >>> conf = OmegaConf.structured(FrozenClass)
    >>> with raises(ReadonlyConfigError):
    ...    conf.x = 20

The read-only flag is recursive:

.. doctest::

    >>> with raises(ReadonlyConfigError):
    ...    conf.list[0] = 20

Merging with other configs
^^^^^^^^^^^^^^^^^^^^^^^^^^

Once an OmegaConf object is created, it can be merged with others regardless of its source.
OmegaConf configs created from Structured configs contains type information that is enforced at runtime.
This can be used to validate config files based on a schema specified in a structured config class

**example.yaml** file:

.. include:: example.yaml
   :code: yaml

A Schema for the above config can be defined like this.

.. doctest::

    >>> @dataclass
    ... class Server:
    ...     port: int = MISSING

    >>> @dataclass
    ... class Log:
    ...     file: str = MISSING
    ...     rotation: int = MISSING

    >>> @dataclass
    ... class MyConfig:
    ...     server: Server = Server()
    ...     log: Log = Log()
    ...     users: List[int] = field(default_factory=list)


I intentionally made an error in the type of the users list (``List[int]`` should be ``List[str]``).
This will cause a validation error when merging the config from the file with that from the scheme.

.. doctest::

    >>> schema = OmegaConf.structured(MyConfig)
    >>> conf = OmegaConf.load("source/example.yaml")
    >>> with raises(ValidationError):
    ...     OmegaConf.merge(schema, conf)

