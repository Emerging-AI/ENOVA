import dataclasses
import functools
from typing import Callable, Dict


@dataclasses.dataclass
class RemoteFunc:
    method: str
    path: str
    func: Callable
    kwarg: Dict


REMOTE_FUNC_TAG = "__remote_func__"


@dataclasses.dataclass
class Enode:
    """"""

    model: str
    name: str = 'enode'

    @classmethod
    def remote_func(cls, method, path=None, **kwarg):
        def decorator(func):
            actual_path = f"/{func.__name__}" if path is None else path

            @functools.wraps(func)
            def wrapped_func(self, *args, **kwargs):
                return func(self, *args, **kwargs)

            setattr(wrapped_func, REMOTE_FUNC_TAG, (RemoteFunc(method, actual_path, func, kwarg)))
            return wrapped_func

        return decorator
