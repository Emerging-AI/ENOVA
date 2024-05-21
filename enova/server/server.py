from pydoc import locate  # noqa
import importlib  # noqa
import inspect
from typing import List  # noqa
from fastapi import FastAPI, Request, status  # noqa
from fastapi.exceptions import RequestValidationError  # noqa
from fastapi.responses import JSONResponse  # noqa
from fastapi.middleware.cors import CORSMiddleware  # noqa
from enova.common.config import CONFIG  # noqa
from enova.common.logger import LOGGER  # noqa
from enova.common.error import EmergingAIBaseError  # noqa
from enova.server.restful.router import ApiRouter, BaseResource, WebSocketResource  # noqa
from enova.server.middleware.base import EmergingAIMultiMiddlewares  # noqa
from enova.server.exception.handler import BaseExceptionHandler  # noqa


async def unexpected_exception_handler(request: Request, exc: Exception):
    LOGGER.exception(f"unexpected_exception: {str(exc)}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"message": str(exc), "code": status.HTTP_500_INTERNAL_SERVER_ERROR, "result": None},
    )


async def emergingai_exception_handler(request: Request, exc: EmergingAIBaseError):
    LOGGER.exception(f"emergingai_exception: error_code: {exc.code}, message: {exc.message}")
    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"message": str(exc.message), "code": exc.code, "result": None},
    )


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    exc_str = f"{exc}".replace("\n", " ").replace("   ", " ")
    # or logger.error(f'{exc}')
    content = {"message": exc_str, "code": 422, "result": None}
    return JSONResponse(content=content, status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)


class ApiServer:
    def __init__(self, api_config) -> None:
        self.api_config = api_config
        self.resource_names = api_config["resource_names"]
        self.middleware_names = api_config.get("middleware_names", [])
        self.app = FastAPI(
            docs_url=self.api_config["url_prefix"] + "/docs",
            redoc_url=self.api_config["url_prefix"] + "/redoc",
            openapi_url=self.api_config["url_prefix"] + "/openapi.json",
        )
        self.api_router = ApiRouter(api_config["url_prefix"])
        self.init_middlewares()
        self.init_routers()
        self.init_exception_handler()

    def init_routers(self):
        allow_base_resouce_cls = [BaseResource, WebSocketResource]
        for resource_module_name in self.resource_names:
            module = importlib.import_module(resource_module_name)
            for _, cls in vars(module).items():
                if inspect.isclass(cls) and any(
                    [(issubclass(cls, base_cls) and cls != base_cls) for base_cls in allow_base_resouce_cls]
                ):
                    self.api_router.register(cls)
        self.app.include_router(self.api_router.router)

    def init_middlewares(self):
        middlewares = EmergingAIMultiMiddlewares()
        for middleware_cls_name in self.middleware_names:
            middleware_ins = locate(middleware_cls_name)(self.api_config)
            middlewares.register(middleware_ins)
        self.app.middleware("http")(middlewares.process)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def init_exception_handler(self):
        for exception_handler_cls_name in self.api_config.get("exception_handler_names", []):
            exception_handler_cls_name
            exception_handler_ins: BaseExceptionHandler = locate(exception_handler_cls_name)()
            self.app.exception_handler(exception_handler_ins.get_exception_class())(
                exception_handler_ins.exception_handler
            )
        self.app.exception_handler(EmergingAIBaseError)(emergingai_exception_handler)
        self.app.exception_handler(RequestValidationError)(validation_exception_handler)
        self.app.exception_handler(Exception)(unexpected_exception_handler)
