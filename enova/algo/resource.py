from enova.server.restful.router import BaseResource
from enova.algo.serializer import (
    ConfigRecommendRequestSLZ,
    ConfigRecommendResponseSLZ,
    AnomalyDetectRequestSLZ,
    AnomalyDetectResponseSLZ,
    AnomalyRecoverRequestSLZ,
    AnomalyRecoverResponseSLZ,
)
from enova.algo.service import AlgoService


class BaseResource(BaseResource):
    def __init__(self) -> None:
        self.service = AlgoService()


class ConfigRecommendResource(BaseResource):
    PATH = "/config_recommend"
    TAGS = ["Algo"]
    GET_INCLUDE_IN_SCHEMA = False
    POST_INCLUDE_IN_SCHEMA = False

    async def post(self, params: ConfigRecommendRequestSLZ) -> ConfigRecommendResponseSLZ:
        return await self.service.config_recommend(params.dict())


class AnomalyDetectResource(BaseResource):
    PATH = "/anomaly_detect"
    TAGS = ["Algo"]
    GET_INCLUDE_IN_SCHEMA = False
    POST_INCLUDE_IN_SCHEMA = False

    async def post(self, params: AnomalyDetectRequestSLZ) -> AnomalyDetectResponseSLZ:
        return await self.service.anomaly_detect(params.dict())


class AnomalyRecoverResource(BaseResource):
    PATH = "/anomaly_recover"
    TAGS = ["Algo"]
    GET_INCLUDE_IN_SCHEMA = False
    POST_INCLUDE_IN_SCHEMA = False

    async def post(self, params: AnomalyRecoverRequestSLZ) -> AnomalyRecoverResponseSLZ:
        return await self.service.anomaly_recover(params.dict())
