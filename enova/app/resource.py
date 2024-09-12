from typing import Annotated, Dict
from fastapi import Body, Depends

from enova.app.serializer import (
    ServingCreateSLZ,
    QueryServingParameterSLZ,
    QueryServingResponseSLZ,
    SingleQueryServingResponseSLZ,
    SingleQueryTestResponseSLZ,
    ListTestResponseSLZ,
    TestCreateSLZ,
    QueryTestParameterSLZ,
)
from enova.server.restful.router import BaseResource
from enova.app.service import AppService


class BaseResource(BaseResource):
    def __init__(self) -> None:
        self.service = AppService()


class HealthzResource(BaseResource):
    PATH = "/healthz"
    TAGS = ["monitor"]

    async def get(self) -> Dict:
        """"""
        return {"status": "running"}


class ServingResource(BaseResource):
    PATH = "/serving"
    GET_INCLUDE_IN_SCHEMA = True
    GET_RESPONSE_MODEL = QueryServingResponseSLZ
    POST_RESPONSE_MODEL = SingleQueryServingResponseSLZ
    TAGS = ["serving serve"]

    async def post(self, params: Annotated[ServingCreateSLZ, Body(openapi_examples=ServingCreateSLZ.Extra.openapi_examples)]) -> Dict:
        """"""
        return await self.service.create_instance(params.dict())

    async def get(self, params: Annotated[QueryServingParameterSLZ, Depends(QueryServingParameterSLZ)]):
        """"""
        return await self.service.list_instance(params.dict())


class SingleServingResource(BaseResource):
    PATH = "/serving/{instance_id}"
    TAGS = ["serving serve"]

    async def delete(self, instance_id: str):
        """"""
        return await self.service.delete_instance(instance_id)

    async def get(self, instance_id: str):
        """"""
        return await self.service.get_instance(instance_id)


class TestResource(BaseResource):
    PATH = "/serving/instance/test"
    GET_RESPONSE_MODEL = ListTestResponseSLZ
    POST_RESPONSE_MODEL = SingleQueryTestResponseSLZ
    TAGS = ["test inject"]

    async def post(self, params: Annotated[TestCreateSLZ, Body(openapi_examples=TestCreateSLZ.Extra.openapi_examples)]):
        return await self.service.create_test(params.dict())

    async def get(self, params: Annotated[QueryTestParameterSLZ, Depends(QueryTestParameterSLZ)]):
        return await self.service.list_test(params.dict())


class SingleTestResource(BaseResource):
    PATH = "/serving/instance/test/{test_id}"
    GET_RESPONSE_MODEL = SingleQueryTestResponseSLZ
    TAGS = ["test inject"]

    async def get(self, test_id: str):
        return await self.service.get_test(test_id)

    async def delete(self, test_id: str):
        return await self.service.delete_test(test_id)
