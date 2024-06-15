import asyncio
import dataclasses
from enova.common.logger import LOGGER
from enova.common.config import CONFIG
from enova.common.constant import VllmMode
from enova.serving.backend.base import BaseBackend


@dataclasses.dataclass
class VllmBackend(BaseBackend):
    def __post_init__(self):
        """"""

    def _create_app(self):
        vllm_mode = CONFIG.vllm.pop("vllm_mode", VllmMode.NORMAL.value)
        from vllm.engine.arg_utils import AsyncEngineArgs
        from vllm.engine.async_llm_engine import AsyncLLMEngine
        from vllm.transformers_utils.tokenizer import get_tokenizer
        import torch

        if not torch.cuda.is_available():
            raise RuntimeError("vLLM Photon requires CUDA runtime")

        if vllm_mode == VllmMode.NORMAL.value:
            from vllm.entrypoints import api_server

            engine_args = AsyncEngineArgs(model=self.enode.model, **CONFIG.vllm)
            engine = AsyncLLMEngine.from_engine_args(engine_args)
            engine_model_config = asyncio.run(engine.get_model_config())
            max_model_len = engine_model_config.max_model_len

            api_server.served_model = self.enode.model
            api_server.engine = engine
            api_server.max_model_len = max_model_len
            api_server.tokenizer = get_tokenizer(
                engine_args.tokenizer,
                tokenizer_mode=engine_args.tokenizer_mode,
                trust_remote_code=engine_args.trust_remote_code,
            )
        elif vllm_mode == VllmMode.OPENAI.value:
            from vllm.entrypoints.openai import api_server

            engine_args = AsyncEngineArgs(model=self.enode.model, **CONFIG.vllm)
            engine = AsyncLLMEngine.from_engine_args(engine_args, usage_context=api_server.UsageContext.OPENAI_API_SERVER)

            served_model_names = [self.enode.model]
            openai_serving_chat = api_server.OpenAIServingChat(
                engine,
                served_model_names,
                CONFIG.vllm.get("response_role") or "assistant",
                CONFIG.vllm.get("lora_modules"),
                CONFIG.vllm.get("chat_template"),
            )
            openai_serving_completion = api_server.OpenAIServingCompletion(engine, served_model_names, CONFIG.vllm.get("lora_modules"))
            api_server.engine = engine
            api_server.engine_args = engine_args
            api_server.openai_serving_chat = openai_serving_chat
            api_server.openai_serving_completion = openai_serving_completion
        else:
            raise ValueError(f"vllm_mode: {vllm_mode} is not support")
        LOGGER.info(f"CONFIG.vllm: {CONFIG.vllm}")

        self.app = api_server.app

        cur_app = api_server.app

        @cur_app.get("/v1/model/info/args")
        async def get_engine_args():
            return {"code": 0, "result": engine_args}
