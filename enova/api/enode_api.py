from enova.common.config import CONFIG
from enova.api.base import ASyncEmergingaiAPI
from enova.common.constant import HttpMethod


ENODE_API_HOST = CONFIG.enova_app["enode_api_host"]


class _EnodeApi:
    def __init__(self) -> None:
        self.engine_args = ASyncEmergingaiAPI(method=HttpMethod.GET.value, url=ENODE_API_HOST + "/v1/model/info/args")


EnodeApi = _EnodeApi()
