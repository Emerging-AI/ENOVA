from typing import List, Tuple
from enova.server.restful.serializer import EmergingAIBaseModel


class LlmModel(EmergingAIBaseModel):
    framework: str
    param: float


class GpuModel(EmergingAIBaseModel):
    name: str
    spec: int
    num: int


TimeSeriesData = List[Tuple[float, float]]


# metric of serving llm model
class Metrics(EmergingAIBaseModel):
    active_requests: TimeSeriesData
    running_requests: TimeSeriesData
    pending_requests: TimeSeriesData
    server_new_requests: TimeSeriesData
    server_success_requests: TimeSeriesData
    gpu_kv_cache_usage: TimeSeriesData


# Configurations of llm model
class Configurations(EmergingAIBaseModel):
    max_num_seqs: int
    tensor_parallel_size: int
    gpu_memory_utilization: float
    replicas: int


class ConfigRecommendRequestSLZ(EmergingAIBaseModel):
    llm: LlmModel
    gpu: GpuModel

    class Config:
        schema_extra = {
            "llm": {
                "framework": "llama",
                "param": 13.0,
            },
            "gpu": {
                "name": "4090",
                "spec": 24,
                "num": 2,
            },
        }


class ConfigRecommendResponseSLZ(EmergingAIBaseModel):
    max_num_seqs: int
    tensor_parallel_size: int
    gpu_memory_utilization: float
    replicas: int


class AnomalyDetectRequestSLZ(EmergingAIBaseModel):
    metrics: List[Metrics]
    configurations: Configurations

    class Config:
        schema_extra = {
            "metrics": [
                {
                    "active_requests": [[1000000000, 10.0], [1000000000, 20.0]],
                    "running_requests": [[1000000000, 5.0], [1000000000, 15.0]],
                    "pending_requests": [[1000000000, 2.0], [1000000000, 4.0]],
                    "server_new_requests": [[1000000000, 30.0], [1000000000, 40.0]],
                    "server_success_requests": [[1000000000, 30.0], [1000000000, 40.0]],
                    "gpu_kv_cache_usage": [[1000000000, 30.0], [1000000000, 40.0]],
                }
            ],
            "configurations": {
                "max_num_seqs": 100,
                "tensor_parallel_size": 8,
                "gpu_memory_utilization": 0.75,
                "replicas": 1,
            },
        }


class AnomalyDetectResponseSLZ(EmergingAIBaseModel):
    is_anomaly: int


class AnomalyRecoverRequestSLZ(EmergingAIBaseModel):
    metrics: List[Metrics]
    configurations: Configurations
    llm: LlmModel
    gpu: GpuModel

    class Config:
        schema_extra = {
            "metrics": [
                {
                    "active_requests": [[1000000000, 10.0], [1000000000, 20.0]],
                    "running_requests": [[1000000000, 5.0], [1000000000, 15.0]],
                    "pending_requests": [[1000000000, 2.0], [1000000000, 4.0]],
                    "server_new_requests": [[1000000000, 30.0], [1000000000, 40.0]],
                    "server_success_requests": [[1000000000, 30.0], [1000000000, 40.0]],
                    "gpu_kv_cache_usage": [[1000000000, 30.0], [1000000000, 40.0]],
                }
            ],
            "configurations": {
                "max_num_seqs": 100,
                "tensor_parallel_size": 8,
                "gpu_memory_utilization": 0.75,
                "replicas": 1,
            },
            "llm": {
                "framework": "llama",
                "param": 13.0,
            },
            "gpu": {
                "name": "4090",
                "spec": 24,
                "num": 2,
            },
        }


class AnomalyRecoverResponseSLZ(ConfigRecommendResponseSLZ):
    pass
