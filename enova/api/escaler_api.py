import dataclasses
import threading
from typing import Dict, List
from enova.common.config import CONFIG
from enova.api.base import ASyncAPI
from enova.common.constant import HttpMethod
from enova.common.logger import LOGGER
from enova.server.restful.serializer import EmergingAIBaseModel
from enova.common.error import EScalerApiResponseError


ESCALER_API_HOST = CONFIG.api["escaler_api_host"]


# ----------------


class GetEScalerStatusRequest(EmergingAIBaseModel):
    task_name: str


class GetDeployRequest(EmergingAIBaseModel):
    task_name: str


class EnvKVPair(EmergingAIBaseModel):
    name: str
    value: str


class GPUSpec(EmergingAIBaseModel):
    name: str
    num: int
    spec: int


class LLMSpec(EmergingAIBaseModel):
    framework: str
    param: int


class ModelConfig(EmergingAIBaseModel):
    gpu: GPUSpec
    llm: LLMSpec
    version: str


class VolumePaths(EmergingAIBaseModel):
    hostPath: str
    mountPath: str


class CreateEScalerDeployParameters(EmergingAIBaseModel):
    backend: str
    backendConfig: dict
    envs: List[EnvKVPair]
    exporter_endpoint: str
    exporter_service_name: str
    model: str
    modelConfig: ModelConfig
    name: str
    port: int
    replica: int
    volumes: List[VolumePaths]


class DeleteDeployRequest(EmergingAIBaseModel):
    task_name: str


class ListDetectHistoryRequest(EmergingAIBaseModel):
    task_name: str


# ----------------


class _EScalerRequestFormer:
    def get_deploy(self, params) -> Dict:
        req_body = {"task_name": params["task_name"]}
        req_body = GetDeployRequest(**req_body)
        return req_body.dict()

    def create_deploy(self, params) -> Dict:
        req_body = params
        req_body = CreateEScalerDeployParameters(**req_body)
        return req_body.dict()

    def delete_deploy(self, params) -> Dict:
        req_body = {"task_name": params["task_name"]}
        req_body = DeleteDeployRequest(**req_body)
        return req_body.dict()

    def list_detect_history(self, params) -> Dict:
        req_body = {"task_name": params["task_name"]}
        req_body = ListDetectHistoryRequest(**req_body)
        return req_body.dict()


class _EScalerResponseReformer:
    def get_deploy(self, ret) -> Dict:
        if ret.get("code") and ret["code"] not in [0]:
            raise EScalerApiResponseError()

        resp_dict = {"ret": ret}
        return resp_dict

    def create_deploy(self, ret) -> Dict:
        if ret.get("code") and ret["code"] not in [0]:
            raise EScalerApiResponseError()

        resp_dict = {"ret": ret}
        return resp_dict

    def delete_deploy(self, ret) -> Dict:
        if ret.get("code") and ret["code"] not in [0]:
            raise EScalerApiResponseError()

        resp_dict = {"ret": ret}
        return resp_dict

    def list_detect_history(self, ret) -> Dict:
        if ret.get("code") and ret["code"] not in [0]:
            raise EScalerApiResponseError()

        resp_dict = {"ret": ret}
        return resp_dict


class _EScalerApi:
    def __init__(self) -> None:
        # self.xxx = ASyncAPI()
        LOGGER.debug(f"pilot api init: ESCALER_API_HOST={ESCALER_API_HOST}")
        self.get_deploy = ASyncAPI(
            url=ESCALER_API_HOST + "/api/escaler/v1/docker/deploy",
            method=HttpMethod.GET.value,
            header_builder=self.get_request_header,
        )
        self.create_deploy = ASyncAPI(
            url=ESCALER_API_HOST + "/api/escaler/v1/docker/deploy",
            method=HttpMethod.POST.value,
            post_send=self.post_send,
            header_builder=self.get_request_header,
        )
        self.delete_deploy = ASyncAPI(
            url=ESCALER_API_HOST + "/api/escaler/v1/docker/deploy",
            method=HttpMethod.DELETE.value,
            header_builder=self.get_request_header,
        )
        self.list_detect_history = ASyncAPI(
            url=ESCALER_API_HOST + "/api/escaler/v1/task/detect/history",
            method=HttpMethod.GET.value,
            header_builder=self.get_request_header,
        )

    def post_send(self, ret: Dict):
        return ret

    def get_request_header(self):
        # TODO:
        return {}


@dataclasses.dataclass
class EScalerApiWrapper:
    _instance = None
    _lock = threading.Lock()
    _initialized: bool = dataclasses.field(default=False, init=False)

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super(EScalerApiWrapper, cls).__new__(cls)
        return cls._instance

    def __post_init__(self) -> None:
        if self._initialized:
            return
        self.async_api = _EScalerApi()
        self.request_former = _EScalerRequestFormer
        self.response_reformer = _EScalerResponseReformer
        self._initialized = True

    def __getattr__(self, item):
        if all(
            [
                hasattr(self.request_former, item),
                hasattr(self.async_api, item),
                hasattr(self.response_reformer, item),
            ]
        ):

            async def pipeline(params):
                req_body = getattr(self.request_former, item)(self, params)
                api_ret = await getattr(self.async_api, item)(req_body)
                res = getattr(self.response_reformer, item)(self, api_ret)

                return res

            return pipeline

        if hasattr(self.async_api, item):
            return getattr(self.async_api, item)
        return super().__getattr__(item)
