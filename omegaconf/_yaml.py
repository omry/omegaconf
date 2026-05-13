import os
import pathlib
import re
from typing import Any, Dict, Optional

import yaml

try:
    from yaml import CSafeLoader

    BaseLoader = CSafeLoader
except ImportError:  # pragma: no cover
    BaseLoader = yaml.SafeLoader

# This URL is also spelled out in public OmegaConf docstrings so IDE/help() views
# show it; keep those docstrings in sync if the docs move.
_YAML_ALIAS_EXPANSION_DOCS_URL = (
    "https://omegaconf.readthedocs.io/en/latest/yaml_aliases.html"
)
_MAX_YAML_ALIAS_EXPANSION_RATIO = 100
_MIN_YAML_ALIAS_EXPANSION_RATIO_NODES = 1_000
_DEFAULT_MAX_YAML_EXPANDED_NODES_VALUE = 10_000
_MAX_YAML_EXPANDED_NODES_ENV = "OMEGACONF_MAX_YAML_EXPANDED_NODES"


class _DefaultMaxYamlExpandedNodes(int):
    def __new__(cls) -> "_DefaultMaxYamlExpandedNodes":
        return int.__new__(cls, _DEFAULT_MAX_YAML_EXPANDED_NODES_VALUE)


_DEFAULT_MAX_YAML_EXPANDED_NODES = _DefaultMaxYamlExpandedNodes()


def _parse_max_yaml_expanded_nodes(value: str) -> Optional[int]:
    value = value.strip()
    if value.lower() == "none":
        return None
    try:
        limit = int(value)
    except ValueError:
        limit = 0
    if limit <= 0:
        raise ValueError(
            f"Invalid value for {_MAX_YAML_EXPANDED_NODES_ENV}: {value!r}. "
            "Set it to a positive integer or 'none'."
        )
    return limit


def _resolve_max_yaml_expanded_nodes(max_yaml_expanded_nodes: Any) -> Optional[int]:
    if max_yaml_expanded_nodes is _DEFAULT_MAX_YAML_EXPANDED_NODES:
        env_value = os.environ.get(_MAX_YAML_EXPANDED_NODES_ENV)
        if env_value is None:
            return _DEFAULT_MAX_YAML_EXPANDED_NODES_VALUE
        return _parse_max_yaml_expanded_nodes(env_value)
    if max_yaml_expanded_nodes is None:
        return None
    if (
        not isinstance(max_yaml_expanded_nodes, int)
        or isinstance(max_yaml_expanded_nodes, bool)
        or max_yaml_expanded_nodes <= 0
    ):
        raise ValueError("max_yaml_expanded_nodes must be a positive integer or None")
    return max_yaml_expanded_nodes


def get_yaml_loader(
    *, max_yaml_expanded_nodes: Optional[int] = _DEFAULT_MAX_YAML_EXPANDED_NODES
) -> Any:
    effective_max_yaml_expanded_nodes = _resolve_max_yaml_expanded_nodes(
        max_yaml_expanded_nodes
    )

    class OmegaConfLoader(BaseLoader):  # type: ignore
        def construct_document(self, node: yaml.Node) -> Any:
            self._reject_recursive_aliases(node)
            if effective_max_yaml_expanded_nodes is not None:
                expanded_nodes = self._expanded_node_count(
                    node, limit=effective_max_yaml_expanded_nodes
                )
                if expanded_nodes > effective_max_yaml_expanded_nodes:
                    raise yaml.constructor.ConstructorError(
                        None,
                        None,
                        "YAML node expansion exceeds the configured limit of "
                        f"{effective_max_yaml_expanded_nodes}. See "
                        f"{_YAML_ALIAS_EXPANSION_DOCS_URL}. Increase "
                        "max_yaml_expanded_nodes or set "
                        f"{_MAX_YAML_EXPANDED_NODES_ENV} to a larger positive "
                        "integer. Use 'none' only for trusted input.",
                        node.start_mark,
                    )
                baseline_nodes = self._unique_node_count(node)
                if (
                    expanded_nodes > _MIN_YAML_ALIAS_EXPANSION_RATIO_NODES
                    and expanded_nodes
                    > baseline_nodes * _MAX_YAML_ALIAS_EXPANSION_RATIO
                ):
                    raise yaml.constructor.ConstructorError(
                        None,
                        None,
                        "YAML aliases expand the document from "
                        f"{baseline_nodes} nodes to {expanded_nodes} nodes, "
                        "exceeding the supported ratio of "
                        f"{_MAX_YAML_ALIAS_EXPANSION_RATIO}x. See "
                        f"{_YAML_ALIAS_EXPANSION_DOCS_URL}. For trusted input, "
                        "pass max_yaml_expanded_nodes=None or set "
                        f"{_MAX_YAML_EXPANDED_NODES_ENV}=none.",
                        node.start_mark,
                    )
            return super().construct_document(node)

        def _reject_recursive_aliases(self, node: yaml.Node) -> None:
            seen: Dict[yaml.Node, None] = {}
            visiting: Dict[yaml.Node, None] = {}

            def visit(n: yaml.Node) -> None:
                if n in seen:
                    return
                if n in visiting:
                    raise yaml.constructor.ConstructorError(
                        None,
                        None,
                        "YAML recursive aliases are not supported.",
                        n.start_mark,
                    )

                visiting[n] = None
                try:
                    if isinstance(n, yaml.SequenceNode):
                        for child in n.value:
                            visit(child)
                    elif isinstance(n, yaml.MappingNode):
                        for key_node, value_node in n.value:
                            visit(key_node)
                            visit(value_node)
                finally:
                    del visiting[n]

                seen[n] = None

            visit(node)

        def _unique_node_count(self, node: yaml.Node) -> int:
            seen: Dict[yaml.Node, None] = {}

            def count(n: yaml.Node) -> int:
                if n in seen:
                    return 0
                seen[n] = None

                total = 1
                if isinstance(n, yaml.SequenceNode):
                    for child in n.value:
                        total += count(child)
                elif isinstance(n, yaml.MappingNode):
                    for key_node, value_node in n.value:
                        total += count(key_node)
                        total += count(value_node)
                return total

            return count(node)

        def _expanded_node_count(self, node: yaml.Node, limit: int) -> int:
            memo: Dict[yaml.Node, int] = {}

            def count(n: yaml.Node) -> int:
                if n in memo:
                    return memo[n]

                total = 1
                if isinstance(n, yaml.SequenceNode):
                    for child in n.value:
                        total += count(child)
                        if total > limit:
                            break
                elif isinstance(n, yaml.MappingNode):
                    for key_node, value_node in n.value:
                        total += count(key_node)
                        if total > limit:
                            break
                        total += count(value_node)
                        if total > limit:
                            break

                memo[n] = total
                return total

            return count(node)

        def flatten_mapping(self, node: yaml.Node) -> Any:
            merge_tag = "tag:yaml.org,2002:merge"
            explicit_keys = set()
            for key_node, _ in node.value:
                if key_node.tag == merge_tag:
                    continue
                if key_node.tag != yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG:
                    continue
                if key_node.value in explicit_keys:
                    raise yaml.constructor.ConstructorError(
                        "while constructing a mapping",
                        node.start_mark,
                        f"found duplicate key {key_node.value}",
                        key_node.start_mark,
                    )
                explicit_keys.add(key_node.value)

            merge = []
            index = 0
            while index < len(node.value):
                key_node, value_node = node.value[index]
                if key_node.tag == merge_tag:
                    del node.value[index]
                    if isinstance(value_node, yaml.MappingNode):
                        self.flatten_mapping(value_node)
                        merge.extend(value_node.value)
                    elif isinstance(value_node, yaml.SequenceNode):
                        submerge = []
                        for subnode in value_node.value:
                            if not isinstance(subnode, yaml.MappingNode):
                                raise yaml.constructor.ConstructorError(
                                    "while constructing a mapping",
                                    node.start_mark,
                                    "expected a mapping for merging, but found "
                                    f"{subnode.id}",
                                    subnode.start_mark,
                                )
                            self.flatten_mapping(subnode)
                            submerge.append(subnode.value)
                        submerge.reverse()
                        for value in submerge:
                            merge.extend(value)
                    else:
                        raise yaml.constructor.ConstructorError(
                            "while constructing a mapping",
                            node.start_mark,
                            "expected a mapping or list of mappings for merging, "
                            f"but found {value_node.id}",
                            value_node.start_mark,
                        )
                elif key_node.tag == "tag:yaml.org,2002:value":
                    key_node.tag = yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG
                    index += 1
                else:
                    index += 1

            if merge:
                merge = [
                    (key_node, value_node)
                    for key_node, value_node in merge
                    if key_node.tag != yaml.resolver.BaseResolver.DEFAULT_SCALAR_TAG
                    or key_node.value not in explicit_keys
                ]
                node.value = merge + node.value

        def construct_mapping(self, node: yaml.Node, deep: bool = False) -> Any:
            return super().construct_mapping(node, deep=deep)

    loader = OmegaConfLoader
    loader.add_implicit_resolver(
        "tag:yaml.org,2002:float",
        re.compile(
            """^(?:
         [-+]?[0-9]+(?:_[0-9]+)*\\.[0-9_]*(?:[eE][-+]?[0-9]+)?
        |[-+]?[0-9]+(?:_[0-9]+)*(?:[eE][-+]?[0-9]+)
        |\\.[0-9]+(?:_[0-9]+)*(?:[eE][-+][0-9]+)?
        |[-+]?[0-9]+(?:_[0-9]+)*(?::[0-5]?[0-9])+\\.[0-9_]*
        |[-+]?\\.(?:inf|Inf|INF)
        |\\.(?:nan|NaN|NAN))$""",
            re.X,
        ),
        list("-+0123456789."),
    )
    loader.yaml_implicit_resolvers = {
        key: [
            (tag, regexp)
            for tag, regexp in resolvers
            if tag != "tag:yaml.org,2002:timestamp"
        ]
        for key, resolvers in loader.yaml_implicit_resolvers.items()
    }

    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib.Path",
        lambda loader, node: pathlib.Path(*loader.construct_sequence(node)),
    )
    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib.PosixPath",
        lambda loader, node: pathlib.PosixPath(*loader.construct_sequence(node)),
    )
    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib.WindowsPath",
        lambda loader, node: pathlib.WindowsPath(*loader.construct_sequence(node)),
    )

    # Python 3.13+ uses internal pathlib._local module
    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib._local.Path",
        lambda loader, node: pathlib.Path(*loader.construct_sequence(node)),
    )
    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib._local.PosixPath",
        lambda loader, node: pathlib.PosixPath(*loader.construct_sequence(node)),
    )
    loader.add_constructor(
        "tag:yaml.org,2002:python/object/apply:pathlib._local.WindowsPath",
        lambda loader, node: pathlib.WindowsPath(*loader.construct_sequence(node)),
    )

    return loader
