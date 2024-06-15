from typing import List
from enova.common.constant import DurationUnitType, TrafficDistributionType, VllmMode
from enova.server.restful.serializer import (
    EmergingAIBaseModel,
    EmergingAIQueryRequestBaseModel,
    EmergingAIQueryResponseBaseModel,
)


class EnodeStartupArgs(EmergingAIBaseModel):
    exported_job: str
    dtype: str
    load_format: str
    max_num_batched_tokens: int
    max_num_seqs: int
    max_paddings: int
    max_seq_len: int
    model: str
    tokenizer: str
    pipeline_parallel_size: int
    tensor_parallel_size: int
    quantization: str | None = None
    engine_args: dict | None = None


class GPUSpec(EmergingAIBaseModel):
    product: str
    video_memory: str
    card_amount: int


class CPUSpec(EmergingAIBaseModel):
    brand_name: str
    core_amount: int


class EnodeInstanceSpec(EmergingAIBaseModel):
    gpu: GPUSpec
    cpu: CPUSpec
    memory: str


class EnodeCreateSLZ(EmergingAIBaseModel):
    instance_name: str | None
    model: str
    backend_config: dict | None
    creator: str | None = "eadmin"

    class Extra:
        openapi_examples = {
            "Enode Instance 1": {
                "value": {
                    "instance_name": "enova_test",
                    "model": "THUDM/chatglm3-6b",
                    # "creator": "eadmin",
                }
            }
        }


class QueryEnodeParameterSLZ(EmergingAIBaseModel):
    instance_id: str | None = None
    # TODO: limit in 1 instance running
    # deploy_status: DeployStatus | None = None
    # test_status: DeployStatus | None = None
    # serve_status: DeployStatus | None = None
    # creator: str | None = None
    # order_by: str | None = "create_time"
    # order_type: OrderBy | None = OrderBy.DESC.value


class QueryTestParameterSLZ(EmergingAIQueryRequestBaseModel):
    test_id: str | None = None
    instance_id: str | None = None
    data_set: str | None = None
    test_status: str | None = None
    creator: str | None = None


class TestSpec(EmergingAIBaseModel):
    data_set: str
    duration: int
    duration_unit: DurationUnitType = DurationUnitType.SECOND.value
    distribution: TrafficDistributionType
    tps_mean: float | None
    tps_std: float | None  # TODO: change to distribution_params, fit more distributions setup


class ParamSpec(EmergingAIBaseModel):
    max_tokens: int
    temperature: float
    top_p: float
    others: str


class TestCreateSLZ(EmergingAIBaseModel):
    instance_id: str
    test_spec: TestSpec
    param_spec: ParamSpec
    creator: str | None = None

    class Extra:
        openapi_examples = {
            "Test Instance 1": {
                "value": {
                    "instance_id": "18f421c628390d63e5f10249454e054",
                    "test_spec": {
                        "data_set": "GSM8K",
                        "duration": 10,
                        "duration_unit": "sec",
                        "distribution": "poisson",
                        "tps_mean": 10.0,
                        "tps_std": 10.0,
                    },
                    "param_spec": {"max_tokens": 1024, "temperature": 0.8, "top_p": 0.8, "others": "do_sample:true"},
                    "creator": "eadmin",
                }
            }
        }


class SingleQueryEnodeResponseSLZ(EmergingAIBaseModel):
    instance_id: str
    instance_name: str | None
    instance_spec: dict | None
    mdl_cfg: dict | None  # TODO: pydantic 2.7 not suggest model_* as property
    startup_args: dict | None
    enode_id: str
    deploy_status: str
    create_time: str
    extra: dict | None


class QueryEnodeResponseSLZ(EmergingAIBaseModel):
    data: List[SingleQueryEnodeResponseSLZ]


class SingleQueryTestResponseSLZ(EmergingAIBaseModel):
    test_id: str
    instance_id: str | None = None
    test_spec: dict | None = None
    param_spec: dict | None = None
    test_status: str | None = None
    prompt_tps: float | None = None
    generation_tps: float | None = None
    result: dict | None = None
    create_time: str | None = None


class ListTestResponseSLZ(EmergingAIQueryResponseBaseModel):
    data: List[SingleQueryTestResponseSLZ]
