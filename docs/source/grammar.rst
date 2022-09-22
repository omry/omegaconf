=====================
The OmegaConf grammar
=====================

.. contents::
   :local:

.. testsetup:: *

    from omegaconf import OmegaConf

OmegaConf uses an `ANTLR <https://www.antlr.org/>`_-based grammar to parse string expressions,
where the `lexer rules <https://github.com/omry/omegaconf/blob/master/omegaconf/grammar/OmegaConfGrammarLexer.g4>`_
rules define the tokens used by the `parser rules <https://github.com/omry/omegaconf/blob/master/omegaconf/grammar/OmegaConfGrammarParser.g4>`_.
Currently this grammar's main usage is in the parsing of :ref:`interpolations<interpolation>`, detailed below.


.. _interpolation-strings:

Interpolation strings
^^^^^^^^^^^^^^^^^^^^^

An interpolation string is any string containing the ``${`` character sequence (denoting the start of an interpolation),
and is parsed using the ``text`` rule of the grammar:

    .. code-block:: antlr

        text: (interpolation |
               ANY_STR | ESC | ESC_INTER | TOP_ESC | QUOTED_ESC)+;

Such a string can either be a single interpolation, or the concatenation of multiple fragments
that can either be interpolations or regular strings
(with a special handling of escaped characters, see :ref:`escaping-in-interpolation-strings` below).
These are all examples of interpolation strings:

    - ``${foo.bar}``
    - ``https://${host}:${port}``
    - ``Hello ${name}``
    - ``${a}${oc.env:B}${c}``


Interpolation types
^^^^^^^^^^^^^^^^^^^

An ``interpolation`` as found in the rule above can either be a :ref:`config-node-interpolation`
(e.g., ``${host}``) or a call to a :ref:`resolver<resolvers>` (e.g., ``${oc.env:B}``).
This is reflected in the following parser rules:

    .. code-block:: antlr

        interpolation: interpolationNode | interpolationResolver;

        interpolationNode:
            INTER_OPEN  // ${
            DOT* 
            (configKey | BRACKET_OPEN configKey BRACKET_CLOSE)
            (DOT configKey | BRACKET_OPEN configKey BRACKET_CLOSE)*
            INTER_CLOSE;  // }

        interpolationResolver:
            INTER_OPEN  // ${
            resolverName COLON sequence?
            BRACE_CLOSE;  // }

The following are all valid examples of config node interpolations according to the ``interpolationNode`` rule
(note in particular that it supports both dot and bracket notations to access child nodes):

    - ``${host}``
    - ``${.sibling}``
    - ``${..uncle.cousin}``
    - ``${some_list[3]}``
    - ``${some_deep_dict[key1][subkey2].subsubkey3}``

Here are also examples of resolver calls from the ``interpolationResolver`` rule:

    - ``${oc.env:B}``
    - ``${my_resolver_without_args:}``
    - ``${oc.select: missing, default}``

Resolver arguments must be provided in a comma-separated list as per the following
``sequence`` parser rule:

    .. code-block:: antlr

        sequence: (element (COMMA element?)*) | (COMMA element?)+;

*Note that this rule currently supports empty arguments to preserve backward compatibility
with OmegaConf 2.0, but this has been deprecated (see* `#572 <https://github.com/omry/omegaconf/issues/572>`_ *).*


.. _element-types:

Element types
^^^^^^^^^^^^^

As seen in the ``sequence`` rule above, each resolver argument is parsed by an ``element`` rule,
which currently supports four main types of arguments:

    .. code-block:: antlr

        element:
            quotedValue
            | listContainer
            | dictContainer
            | primitive
        ;

A ``quotedValue`` is a quoted string that may contain basically anything in-between either double or single quotes
(including interpolations, which will be resolved at evaluation time).
For instance:

    - ``"Hello World!"``
    - ``'Hello ${name}!'``
    - ``"I ${can: ${nest}, ${interpolations}, 'and quotes'}"``

The ``quotedValue`` parser rule is formally defined as:

    .. code-block:: antlr

        quotedValue:
            (QUOTE_OPEN_SINGLE | QUOTE_OPEN_DOUBLE)
            text?
            MATCHING_QUOTE_CLOSE;


``listContainer`` and ``dictContainer`` are respectively lists and dictionaries, using a familiar syntax:

    - List examples: ``[]``, ``[1, 2, 3]``, ``[${a}, ${oc.env:B}, c]``
    - Dict examples: ``{}``, ``{a: 1, b: 2}``, ``{a: ${a}, b: ${oc.env:B}}``

Their corresponding parser rules are:

    .. code-block:: antlr

        listContainer: BRACKET_OPEN sequence? BRACKET_CLOSE;
        dictContainer: BRACE_OPEN
                       (dictKeyValuePair (COMMA dictKeyValuePair)*)?
                       BRACE_CLOSE;

Regarding dictionaries, note that although values can be any ``element``, keys are more
restricted, and in particular quoted strings and interpolations are currently *not* allowed as
dictionary keys (see the definition of ``dictKey`` in the `grammar <https://github.com/omry/omegaconf/blob/master/omegaconf/grammar/OmegaConfGrammarParser.g4>`_).

Finally, a ``primitive`` is everything else that is allowed, including in particular (see the `full grammar <https://github.com/omry/omegaconf/blob/master/omegaconf/grammar/OmegaConfGrammarParser.g4>`_
for details):

    - Unquoted strings (that support only a subset of characters, contrary to quoted ones): ``foo``, ``foo_bar``, ``hello world 123``
    - Integer numbers: ``123``, ``-5``, ``+1_000_000``
    - Floating point numbers (with special case-independent keywords for infinity and NaN): ``0.1``, ``1e-3``, ``inf``, ``-INF``, ``nan``
    - Other special keywords (also case-independent): ``null``, ``true``, ``false``, ``NULL``, ``True``, ``fAlSe``.
      **IMPORTANT**: ``None`` is *not* a special keyword and will be parsed as an unquoted string, you must
      use the ``null`` keyword instead (as in YAML).
    - Interpolations (thus allowing for nested interpolations)


Escaped characters
^^^^^^^^^^^^^^^^^^

Some characters need to be escaped, with varying escaping requirements depending on the situation.
In general, however, you can use the following rule of thumb:
*you only need to escape characters that otherwise have a special meaning in the current context*.

.. _escaping-in-interpolation-strings:

Escaping in interpolation strings
+++++++++++++++++++++++++++++++++

In order to define fields whose value is an interpolation-like string, interpolations can be escaped with ``\${``.
For instance:

.. doctest::

    >>> c = OmegaConf.create({"path": r"\${dir}", "dir": "tmp"})
    >>> print(c.path)  # does *not* interpolate into the `dir` node
    ${dir}

If you actually want to follow a ``\`` with a resolved interpolation, this backslash
needs to be escaped into ``\\`` to differentiate it from an escaped interpolation:

.. doctest::

    >>> c = OmegaConf.create({"path": r"C:\\${dir}", "dir": "tmp"})
    >>> print(c.path)  # *does* interpolate into the `dir` node
    C:\tmp

Note that we use Python raw strings here to make code
more readable -- otherwise all ``\`` characters would need be duplicated due to how Python handles
escaping in regular string literals.

Finally, since the ``\`` character has no special meaning unless followed by ``${``,
it does *not* need to be escaped anywhere else:

.. doctest::

    >>> c = OmegaConf.create({"path": r"C:\foo_${dir}", "dir": "tmp"})
    >>> print(c.path)  # a single \ is preserved...
    C:\foo_tmp
    >>> c = OmegaConf.create({"path": r"C:\\foo_${dir}", "dir": "tmp"})
    >>> print(c.path)  # ... and multiple \\ too (no escape sequence)
    C:\\foo_tmp

Escaping in unquoted strings
++++++++++++++++++++++++++++

Unquoted strings can be found in a number of contexts, including dictionary keys/values,
list elements, etc. As a result, the  escape sequences are used for some
special characters
(``\\``, ``\[``, ``\]``, ``\{``, ``\}``, ``\(``, ``\)``, ``\:``, ``\=``, ``\,``),
for instance:

    - ``C\:\\$\{dir\}`` resolves to the string ``"C:\${dir}"``
    - ``\[a\, b\, c\]`` resolves to the string ``"[a, b, c]"``

In addition, leading and trailing whitespaces must be escaped in unquoted strings
if we do not want them to be stripped (while inner whitespaces are always preserved):

.. doctest::

    >>> c = OmegaConf.create({"esc": r"${oc.decode: \ hi u \  }"})
    >>> c.esc  # one leading whitespace and two trailing ones
    ' hi u  '
    >>> # Tabs are handled similarly (NB: r-strings can't be used below)
    >>> c = OmegaConf.create({"esc": "${oc.decode:\t\\\thi u\t\\\t\t}"})
    >>> c.esc  # one leading tab and two trailing ones
    '\thi u\t\t'

Escaping in unquoted strings can lead to hard-to-read expressions, and it is recommended
to switch to quoted strings instead of relying heavily on the above escape sequences.

Escaping in quoted strings
++++++++++++++++++++++++++

As can be seen from the definition of the ``quotedValue`` parser rule above, quoted strings
are just ``text`` fragments surrounded by quotes, and are thus very similar to :ref:`interpolation-strings`.
As a result, the ``\${`` escape sequence can also be used to escape interpolations
in quoted strings (as described in :ref:`escaping-in-interpolation-strings`):

    - ``"\${dir}"`` resolves to the string ``"${dir}"``
    - ``"C:\\${dir}"`` resolves to the string ``"C:\<value of dir>"``

However, one key difference with interpolation strings is that quotes of the same type
as the enclosing quotes must be escaped, unless they are within a nested interpolation.
For instance:

    - ``'\'Hi you\', I said'`` resolves to the string ``"'Hi you', I said"``
    - ``"'Hi ${concat: 'y', "o", u}', I said"`` also resolves to the string ``"'Hi you', I said"``
      if ``concat`` is a :doc:`custom resolver<custom_resolvers>` concatenating its inputs.
      The main point to pay attention to in this example is that the quoted strings ``'y'`` and
      ``"o"`` found within the resolver interpolation ``${concat: ...}`` do *not* need to be
      escaped, regardless of existing quotes outside of this interpolation.
