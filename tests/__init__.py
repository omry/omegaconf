from contextlib import contextmanager


class IllegalType:
    def __init__(self):
        pass


@contextmanager
def does_not_raise(enter_result=None):
    yield enter_result
