from enova.common.config import CONFIG
from enova.api.base import ASyncRestfulEmergingaiAPI, ASyncEmergingaiAPI
from enova.common.constant import HttpMethod


APP_API_HOST = CONFIG.enova_app["app_api_host"]


class _EnovaAppApi:
    def __init__(self) -> None:
        self.healthz = ASyncEmergingaiAPI(method=HttpMethod.GET.value, url=APP_API_HOST + "/v1/healthz")

        self.enode = ASyncRestfulEmergingaiAPI(
            url=APP_API_HOST + "/v1/enode",
            resource_key="instance_id",
        )

        self.delete_enode_by_name = ASyncEmergingaiAPI(method=HttpMethod.DELETE.value, url=APP_API_HOST + "/v1/enode/name")


EnovaAppApi = _EnovaAppApi()
