import dataclasses
from enova.common.constant import ServingBackend
from enova.common.config import CONFIG
from enova.enode.enode import Enode
from enova.serving.backend.transformers import TransformersBackend
from enova.serving.backend.vllm import VllmBackend


@dataclasses.dataclass
class EApiServer:
    """
    Need to adapt to multiple task, text2text, text2image, image2image
    support multiple api according to different task
    """

    host: str
    port: int
    enode: Enode
    backend: str

    def __post_init__(self):
        self.backend_ins = None

    def get_backend_ins(self):
        engine_map = {ServingBackend.HF.value: TransformersBackend, ServingBackend.VLLM.value: VllmBackend}
        if self.backend not in engine_map:
            raise ValueError(f"serving.backend: {CONFIG.serving['backend']} is not in {ServingBackend.values()}")
        return engine_map[self.backend](self.enode)

    def local_run(self):
        """"""
        self.backend_ins = self.get_backend_ins()
        self.backend_ins.local_run(host=self.host, port=self.port)
