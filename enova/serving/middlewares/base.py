import abc
from typing import List
from fastapi import Request


def get_dependencies() -> List:
    return


class BaseMiddleware(metaclass=abc.ABCMeta):
    """"""


class EnovaAIMultiMiddlewares:
    def __init__(self) -> None:
        self.middewares: List[BaseMiddleware] = []
        self.request_middlewares: List[BaseMiddleware] = []
        self.response_middlewares: List[BaseMiddleware] = []

    def register(self, middleware: BaseMiddleware):
        self.middewares.append(middleware)
        if hasattr(middleware, "_process_request"):
            self.request_middlewares.append(middleware)
        if hasattr(middleware, "_process_response"):
            self.response_middlewares.append(middleware)

    async def process(self, request: Request, call_next):
        # request
        for middleware in self.request_middlewares:
            if hasattr(middleware, "_process_request"):
                await middleware._process_request(request)
        response = await call_next(request)
        # response
        for middleware in self.response_middlewares:
            response = await middleware._process_response(request, response)
        return response
