from typing import Optional


class Node(object):
    def __init__(self, parent: Optional["Node"]):
        self.__dict__["parent"] = parent

        # Flags have 3 modes:
        #   unset : inherit from parent, defaults to false in top level config.
        #   set to true: flag is true
        #   set to false: flag is false
        self.__dict__["flags"] = {}

    def _set_parent(self, parent: "Node"):
        assert parent is None or isinstance(parent, Node)
        self.__dict__["parent"] = parent

    def _get_parent(self) -> "Node":
        return self.__dict__["parent"]

    def _get_root(self) -> "Node":
        root = self.__dict__["parent"]
        if root is None:
            return self
        while root.__dict__["parent"] is not None:
            root = root.__dict__["parent"]
        return root

    def _set_flag(self, flag, value):
        assert value is None or isinstance(value, bool)
        self.__dict__["flags"][flag] = value

    def _get_node_flag(self, flag):
        """
        :param flag: flag to inspect
        :return: the state of the flag on this node.
        """
        return self.__dict__["flags"][flag] if flag in self.__dict__["flags"] else None

    def _get_flag(self, flag):
        """
        Returns True if this config node flag is set
        A flag is set if node.set_flag(True) was called
        or one if it's parents is flag is set
        :return:
        """
        if flag in self.__dict__["flags"] and self.__dict__["flags"][flag] is not None:
            return self.__dict__["flags"][flag]

        if self._get_parent() is None:
            return None
        else:
            # noinspection PyProtectedMember
            return self._get_parent()._get_flag(flag)
