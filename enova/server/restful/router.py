import dataclasses
from fastapi import APIRouter
from fastapi.responses import JSONResponse
from enova.common.config import CONFIG
from enova.common.constant import HttpMethod


class BaseResource:
    PATH = NotImplemented
    DEPENDENCIS = NotImplemented
    GET_RESPONSE_MODEL = None
    PUT_RESPONSE_MODEL = None
    DELETE_RESPONSE_MODEL = None
    POST_RESPONSE_MODEL = None
    GET_RESPONSE_CLASS = JSONResponse
    PUT_RESPONSE_CLASS = JSONResponse
    DELETE_RESPONSE_CLASS = JSONResponse
    POST_RESPONSE_CLASS = JSONResponse
    GET_INCLUDE_IN_SCHEMA = True
    PUT_INCLUDE_IN_SCHEMA = True
    DELETE_INCLUDE_IN_SCHEMA = True
    POST_INCLUDE_IN_SCHEMA = True
    TAGS = None


class WebSocketResource:
    PATH = NotImplemented


@dataclasses.dataclass
class ApiRouter:
    prefix: str = None

    def __post_init__(self) -> None:
        """
        Dynamically convert GET, POST, DELETE, PUT into interfaces. just for fastapi
        """
        self.router = APIRouter(
            prefix=self.prefix,
            dependencies=[],
        )

    def register(self, resource_cls):
        """"""
        if issubclass(resource_cls, BaseResource) and resource_cls != BaseResource:
            self._register_http(resource_cls)

        if issubclass(resource_cls, WebSocketResource) and resource_cls != WebSocketResource:
            self._register_ws(resource_cls)

    def _register_http(self, resource_cls):
        resource_ins = resource_cls()
        for method in HttpMethod.values():
            if hasattr(resource_ins, method):
                response_model = getattr(resource_ins, f"{method.upper()}_RESPONSE_MODEL")
                response_class = getattr(resource_ins, f"{method.upper()}_RESPONSE_CLASS")
                include_in_schema = getattr(resource_ins, f"{method.upper()}_INCLUDE_IN_SCHEMA")
                actual_path = f"/{CONFIG.api['api_version']}{resource_ins.PATH}"
                tags = getattr(resource_ins, "TAGS") or []
                getattr(self.router, method)(
                    actual_path,
                    response_model=response_model,
                    response_class=response_class,
                    include_in_schema=include_in_schema,
                    tags=tags,
                )(getattr(resource_ins, method))

    def _register_ws(self, resource_cls):
        resource_ins = resource_cls()
        if resource_ins.PATH is not NotImplemented:
            actual_path = f"/{CONFIG.api['api_version']}{resource_ins.PATH}"
            self.router.add_api_websocket_route(actual_path, getattr(resource_ins, "get"))
