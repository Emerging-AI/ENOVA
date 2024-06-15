from typing import Annotated, Dict
from fastapi import Body, Depends

from enova.app.serializer import (
    EnodeCreateSLZ,
    QueryEnodeParameterSLZ,
    QueryEnodeResponseSLZ,
    SingleQueryEnodeResponseSLZ,
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


class EnodeResource(BaseResource):
    PATH = "/enode"
    GET_INCLUDE_IN_SCHEMA = True
    GET_RESPONSE_MODEL = QueryEnodeResponseSLZ
    POST_RESPONSE_MODEL = SingleQueryEnodeResponseSLZ
    TAGS = ["enode serve"]

    async def post(
        self, params: Annotated[EnodeCreateSLZ, Body(openapi_examples=EnodeCreateSLZ.Extra.openapi_examples)]
    ) -> Dict:
        """"""
        return await self.service.create_instance(params.dict())

    async def get(self, params: Annotated[QueryEnodeParameterSLZ, Depends(QueryEnodeParameterSLZ)]):
        """"""
        return await self.service.list_instance(params.dict())


class SingleEnodeResource(BaseResource):
    PATH = "/enode/{instance_id}"
    TAGS = ["enode serve"]

    async def delete(self, instance_id: str):
        """"""
        return await self.service.delete_instance(instance_id)

    async def get(self, instance_id: str):
        """"""
        return await self.service.get_instance(instance_id)


class TestResource(BaseResource):
    PATH = "/enode/instance/test"
    GET_RESPONSE_MODEL = ListTestResponseSLZ
    POST_RESPONSE_MODEL = SingleQueryTestResponseSLZ
    TAGS = ["test inject"]

    async def post(
        self, params: Annotated[TestCreateSLZ, Body(openapi_examples=TestCreateSLZ.Extra.openapi_examples)]
    ):
        return await self.service.create_test(params.dict())

    async def get(self, params: Annotated[QueryTestParameterSLZ, Depends(QueryTestParameterSLZ)]):
        return await self.service.list_test(params.dict())


class SingleTestResource(BaseResource):
    PATH = "/enode/instance/test/{test_id}"
    GET_RESPONSE_MODEL = SingleQueryTestResponseSLZ
    TAGS = ["test inject"]

    async def get(self, test_id: str):
        return await self.service.get_test(test_id)

    async def delete(self, test_id: str):
        return await self.service.delete_test(test_id)
