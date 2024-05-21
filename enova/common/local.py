import contextvars
import functools
import threading


context_vars_dict = {}


def set_contextvars(key, value):
    """"""
    if key not in context_vars_dict:
        context_vars_dict[key] = contextvars.ContextVar(key)
    context_vars_dict[key].set(value)


def del_contextvars(key):
    """
    mainly delete the thread vars
    """
    if key in context_vars_dict:
        context_vars_dict[key].clear()


def get_contextvars(key, default=None):
    """
    mainly get the thread vars
    """
    if key not in context_vars_dict:
        return default
    try:
        return context_vars_dict[key].get()
    except LookupError:
        return default


def has_contextvars(key):
    """TODO:"""
    return False


_local = threading.local()


def set_local_param(key, value):
    """
    mainly setup the custom vars of threads
    """
    setattr(_local, key, value)


def del_local_param(key):
    """
    mainly delete the custom vars of threads
    """
    if hasattr(_local, key):
        delattr(_local, key)


def get_local_param(key, default=None):
    return getattr(_local, key, default)


def contextlocal_cache(func):
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        key = functools._make_key(args, kwargs, False)
        key = f"{func.__name__}_{key}"
        if has_contextvars(key):
            return get_local_param(key)
        ret = func(*args, **kwargs)
        set_contextvars(key, ret)
        return ret

    return wrapper
