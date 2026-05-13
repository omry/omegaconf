.. _yaml_aliases:

YAML Alias Limits
=================

OmegaConf stopped loading a YAML file because anchors and aliases would expand
the document too much. This limit protects applications from YAML bombs such as
the `Billion Laughs attack`_.

If the YAML comes from an untrusted source, keep the default limit and simplify
the file by reducing anchors, aliases, or merge keys.

If the YAML is trusted and legitimately needs more expansion, increase the limit
at the call site:

.. code-block:: python

    cfg = OmegaConf.load("config.yaml", max_yaml_expanded_nodes=50_000)
    cfg = OmegaConf.create(yaml_string, max_yaml_expanded_nodes=50_000)

You can also disable the expansion limit for trusted YAML:

.. code-block:: python

    cfg = OmegaConf.load("config.yaml", max_yaml_expanded_nodes=None)
    cfg = OmegaConf.create(yaml_string, max_yaml_expanded_nodes=None)

If you do not control the call site that invokes OmegaConf, set the environment
variable instead:

.. code-block:: bash

    export OMEGACONF_MAX_YAML_EXPANDED_NODES=50000
    export OMEGACONF_MAX_YAML_EXPANDED_NODES=none

The environment value must be a positive integer, or ``none`` to disable the
expansion limit for trusted input. An explicit ``max_yaml_expanded_nodes``
argument takes precedence over the environment variable.

Details
-------

The default limit is ``10_000`` expanded YAML nodes. OmegaConf also rejects a
YAML document larger than ``1_000`` expanded nodes if aliases make it more than
``100`` times larger than the unexpanded document.

These checks apply to the whole YAML document. Scalar keys, scalar values,
mappings, and lists all count as nodes; aliases are charged each time they
expand the aliased value. Recursive YAML aliases are not supported and are
rejected even if the expansion limit is disabled.

A related denial-of-service vulnerability affected the `Kubernetes API server`_.

.. _Billion Laughs attack: https://en.wikipedia.org/wiki/Billion_laughs_attack
.. _Kubernetes API server: https://discuss.kubernetes.io/t/announce-cve-2019-11253-denial-of-service-vulnerability-from-malicious-yaml-or-json-payloads/8349
