from typing import Collection
from opentelemetry import trace, metrics
from opentelemetry.instrumentation.instrumentor import BaseInstrumentor
from opentelemetry.instrumentation.utils import unwrap
from opentelemetry.instrumentation.asgi import collect_request_attributes
from opentelemetry.util.http import _parse_active_request_count_attrs
from wrapt import wrap_function_wrapper
from starlette.types import ASGIApp, Scope, Receive, Send
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor

import json

_instruments = ("fastapi >= 0.1",)


class EnovaMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app
        self.meter = metrics.get_meter(__name__)
        self.tracer = trace.get_tracer(__name__)
        self.requests_counter = self.meter.create_counter(
            name="http.server.requests", unit="requests", description="measures the number of HTTP requests received",
        )

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        attrs = collect_request_attributes(scope)
        _request_count_attrs = _parse_active_request_count_attrs(attrs)
        self.requests_counter.add(1, _request_count_attrs)

        if scope['method'] == "POST" and scope['path'] in ["/generate", "/v1/completions", "/v1/chat/completions"]:
            span_name = f"POST {scope['path']} params"
            messages = []
            more_body = True

            try:
                while more_body:
                    message = await receive()
                    messages.append(message)
                    more_body = message.get("more_body", False)
                body = b''.join([message.get("body", b"") for message in messages if message.get("body")])
                if body:
                    with self.tracer.start_as_current_span(span_name) as generate_span:
                        body_json = json.loads(body)
                        for key in ['prompt', 'messages', 'model']:
                            if key in body_json:
                                generate_span.set_attribute(key, str(body_json[key]))
            except Exception as e:
                pass

        async def wrapped_receive():
            if messages:
                return messages.pop(0)
            return await receive()

        await self.app(scope, wrapped_receive, send)


class EnovaFastAPIInstrumentor(BaseInstrumentor):
    def instrumentation_dependencies(self) -> Collection[str]:
        return _instruments

    def _instrument(self, **kwargs):
        def fastapi_init_wrapper(wrapped, instance, args, kwargs):
            result = wrapped(*args, **kwargs)
            instance.add_middleware(EnovaMiddleware)
            FastAPIInstrumentor.instrument_app(instance)
            return result

        wrap_function_wrapper('fastapi', 'FastAPI.__init__', fastapi_init_wrapper)

    def _uninstrument(self, **kwargs):
        unwrap('fastapi', 'FastAPI.__init__')
