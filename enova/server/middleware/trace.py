import uuid
from fastapi import Request
from enova.server.middleware.base import BaseMiddleware
from enova.common.local import set_contextvars


class TraceMiddleware(BaseMiddleware):

    async def _process_request(self, request: Request):
        """get header trace_id"""
        trace_id = request.headers.get('trace_id') or uuid.uuid4().hex
        set_contextvars('trace_id', trace_id)
