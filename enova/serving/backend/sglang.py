from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, RedirectResponse
import dataclasses
from enova.common.logger import LOGGER
from enova.common.config import CONFIG
from enova.serving.backend.base import BaseBackend

@dataclasses.dataclass
class SgLangBackend(BaseBackend):
    def __post_init__(self):
        """Initialize the SgLangBackend specific components."""
        self._create_app()

    def _create_app(self):
        from sglang.srt.server import app as sglang_app, Engine
        from sglang.srt.server_args import ServerArgs

        if not hasattr(self, 'model'):
            raise RuntimeError("Model path must be specified")
        
        server_args = ServerArgs(model=self.model, **CONFIG.sglang)

        
        self.app = sglang_app # TODO: 


        @self.app.get("/v1/model/info/args")
        async def get_engine_args():
            return RedirectResponse(url="/get_model_info")

        self.engine = Engine(**server_args.dict()) # TODO: will it blocked here? 
        # or asyncio.run(launch_engine, server_args)
        LOGGER.info("SGLangBackend FastAPI app created and routes defined.")
