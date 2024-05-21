from enova.common.config import CONFIG
from enova.api.base import ASyncAPI
from enova.common.constant import HttpMethod


PROM_API_HOST = CONFIG.enova_app["prom_api_host"]


class _PromApi:
    def __init__(self) -> None:
        self.query_range = ASyncAPI(method=HttpMethod.GET.value, url=PROM_API_HOST + "/api/v1/query_range")


PromApi = _PromApi()
