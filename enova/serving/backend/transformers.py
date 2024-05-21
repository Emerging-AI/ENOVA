import dataclasses
import locate
from fastapi import FastAPI, APIRouter
from fastapi.middleware.cors import CORSMiddleware
from enova.common.config import CONFIG
from enova.enode.enode import Enode
from enova.serving.middlewares.base import EnovaAIMultiMiddlewares
from enova.serving.backend.base import BaseBackend


@dataclasses.dataclass
class TransformersBackend(BaseBackend):
    enode: Enode

    def _create_apiserver(self):
        self._create_app()
        self._init_middlewares()
        self._init_routers()

    def _init_middlewares(self):
        """"""
        middlewares = EnovaAIMultiMiddlewares()
        for middleware_cls_name in CONFIG.api.get("middleware_names", []):
            middleware_ins = locate(middleware_cls_name)()
            middlewares.register(middleware_ins)
        self.app.middleware("http")(middlewares.process)
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    def _init_exception_handler(self):
        """"""

    def _init_routers(self):
        """
        according task to add route, such as openai
        """
        self.api_router = APIRouter(
            prefix="",
            dependencies=[],
        )

        @self.app.get("/healthz", include_in_schema=False)
        async def healthz():
            return {"status": "ok"}

        self.register_enode_api()

    def _create_app(self):
        """"""
        self.app = FastAPI(
            title=self.enode.name,
            description=(self.__doc__ if self.__doc__ else f"Enova {self.enode.name}"),
        )

    def register_enode_api(self):
        """
        register_api from enode
        """
        self.enode.register_api_router(self.api_router)
        self.app.include_router(self.api_router)
