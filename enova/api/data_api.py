from typing import List
from enova.common.config import CONFIG
from enova.api.base import ASyncRestfulEmergingaiAPI
from enova.common.constant import HttpMethod, AUTHORIZATION_HEADER

DATA_SERVICE_HOST = CONFIG.api["data_service_host"]


class _DataServiceApi:

    def __init__(self) -> None:
        self.data_table = ASyncRestfulEmergingaiAPI(
            url=f"{DATA_SERVICE_HOST}/api/data/v1/data/dataset",
            resource_key="dataset_id",
            header_builder=self.get_headers,
        )

    def get_headers(self):
        # todo: 从前端获取
        if CONFIG.api["model_service_token"]:
            return {AUTHORIZATION_HEADER: f"Bearer {CONFIG.api['model_service_token']}"}
        return {}


DataServiceApi = _DataServiceApi()


def get_datasets(dataset_id_list: List[str]):
    """"""
    datasets = DataServiceApi.data_table.sync_list({"dataset_id": dataset_id_list})["data"]
    return datasets
