import json
from typing import Dict, List

from pydantic import BaseModel, Field
from pydantic.version import VERSION as PYDANTIC_VERSION


PYDANTIC_V2 = PYDANTIC_VERSION.startswith("2.")
if PYDANTIC_V2:
    from pydantic._internal._model_construction import ModelMetaclass
else:
    from pydantic.main import ModelMetaclass

from enova.common.config import CONFIG  # noqa
from enova.common.constant import OrderBy  # noqa


class AllFields(ModelMetaclass):
    def __new__(self, name, bases, namespaces, **kwargs):
        for field in namespaces:
            if not field.startswith("__"):
                namespaces[field] = Field(namespaces[field])
        return super().__new__(self, name, bases, namespaces, **kwargs)


class EmergingAIBaseModel(BaseModel):
    def dict(self, *args, **kwargs):
        return json.loads(self.model_dump_json())


class EmergingAIQueryRequestBaseModel(EmergingAIBaseModel):
    page: int = Field(default=1, ge=CONFIG.api["default_min_page"], le=CONFIG.api["default_max_page"])
    size: int = Field(default=10, ge=CONFIG.api["default_min_size"], le=CONFIG.api["default_max_size"])
    order_by: str | None = None
    order_type: OrderBy | None = None
    fuzzy: str | None = None
    start_time: str | None = None
    end_time: str | None = None


class EmergingAIQueryResponseBaseModel(EmergingAIBaseModel):
    page: int
    size: int
    total_num: int
    total_page: int
    num: int
    data: List[Dict]
