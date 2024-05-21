import uuid
from typing import Union
from enova.common.local import get_contextvars, set_contextvars


def get_traceid() -> Union[str, None]:
    trace_id = get_contextvars("trace_id")
    if trace_id is None:
        trace_id = uuid.uuid4().hex
        set_contextvars("trace_id", trace_id)
    return trace_id


def get_realip() -> Union[str, None]:
    real_ip = get_contextvars("real_ip")
    # TODO: LOGGER will case cyclic reference
    # if real_ip is None:
    #     LOGGER.warn("RealIPMiddleware maybe not Setup.")
    return real_ip
