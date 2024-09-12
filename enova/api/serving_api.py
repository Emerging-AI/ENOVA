from enova.common.config import CONFIG
from enova.api.base import ASyncEmergingaiAPI
from enova.common.constant import HttpMethod


SERVING_API_HOST = CONFIG.enova_app["serving_api_host"]


class _ServingApi:
    def __init__(self) -> None:
        self.engine_args = ASyncEmergingaiAPI(method=HttpMethod.GET.value, url=SERVING_API_HOST + "/v1/model/info/args")


ServingApi = _ServingApi()
