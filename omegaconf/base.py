from abc import ABC, abstractmethod
from typing import Any, Iterator, Optional, Union


class Node(ABC):
    def __init__(self, parent: Optional["Node"]):
        self.__dict__["parent"] = parent

        # Flags have 3 modes:
        #   unset : inherit from parent (None if no parent specifies)
        #   set to true: flag is true
        #   set to false: flag is false
        self.__dict__["flags"] = {}

    def _set_parent(self, parent: Optional["Container"]) -> None:
        assert parent is None or isinstance(parent, Container)
        self.__dict__["parent"] = parent

    def _get_parent(self) -> "Container":
        return self.__dict__["parent"]  # type: ignore

    def _get_root(self) -> "Container":
        root: Container = self.__dict__["parent"]
        if root is None:
            return self
        while root.__dict__["parent"] is not None:
            root = root.__dict__["parent"]
        return root

    def _set_flag(self, flag: str, value: Optional[bool]) -> None:
        assert value is None or isinstance(value, bool)
        self.__dict__["flags"][flag] = value

    def _get_node_flag(self, flag: str) -> Optional[bool]:
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        return self.__dict__["flags"][flag] if flag in self.__dict__["flags"] else None

    def _get_flag(self, flag: str) -> Optional[bool]:
        """
        Returns True if this config node flag is set
        A flag is set if node.set_flag(True) was called
        or one if it's parents is flag is set
        :return:
        """
        if flag in self.__dict__["flags"] and self.__dict__["flags"][flag] is not None:
            return self.__dict__["flags"][flag]  # type: ignore

        if self._get_parent() is None:
            return None
        else:
            # noinspection PyProtectedMember
            return self._get_parent()._get_flag(flag)


class Container(Node):
    """
    Container tagging interface
    """

    @abstractmethod
    def pretty(self, resolve: bool = False) -> str:
        ...  # pragma: no cover

    @abstractmethod
    def update_node(self, key: str, value: Any = None) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def select(self, key: str) -> Any:
        ...  # pragma: no cover

    def get_node(self, key: Any) -> Node:
        ...  # pragma: no cover

    @abstractmethod
    def __delitem__(self, key: Union[str, int, slice]) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def __setitem__(self, key: Any, value: Any) -> None:
        ...  # pragma: no cover

    @abstractmethod
    def __eq__(self, other: Any) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def __ne__(self, other: Any) -> bool:
        ...  # pragma: no cover

    @abstractmethod
    def __hash__(self) -> int:
        ...  # pragma: no cover

    @abstractmethod
    def __iter__(self) -> Iterator[str]:
        ...  # pragma: no cover

    @abstractmethod
    def __getitem__(self, key_or_index: Any) -> Any:
        ...  # pragma: no cover
