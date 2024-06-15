from enum import Enum as BaseEnum


class Enum(BaseEnum):
    @classmethod
    def values(cls):
        return list(e.value for e in cls.__members__.values())


class ServingBackend(Enum):
    HF = "hf"
    VLLM = "vllm"


class HttpMethod(Enum):
    GET = "get"
    POST = "post"
    PUT = "put"
    DELETE = "delete"

    @classmethod
    def methods_with_body(cls):
        return [cls.POST.value, cls.PUT.value]


class OrderBy(Enum):
    ASC = "asc"
    DESC = "desc"


JSON_RESPONSE_HEADER = "application/json"


# --- server scope ---
class ApiServerType(Enum):
    ENOVA_ALGO = "enova_algo"
    ENOVA_APP = "enova_app"


class DeployMode(Enum):
    COMPOSE = "compose"
    LOCAL = "local"


class TrafficDistributionType(Enum):
    GAUSSIAN = "gaussian"
    POISSON = "poisson"


class DurationUnitType(Enum):
    SECOND = "sec"
    MINUTE = "min"
    HOUR = "hour"


# --- db_model scope ---
class DeployStatus(Enum):
    UNKNOWN = "unknown"
    PENDING = "pending"
    RUNNING = "running"
    FAILED = "failed"
    FINISHED = "finsihed"


class TestStatus(Enum):
    UNKNOWN = "unknown"
    INIT = "init"
    SUCCESS = "success"
    FAILED = "failed"
    RUNNING = "running"
    FINISHED = "finished"


class ServeStatus(Enum):
    UNKNOWN = "unknown"
    OFF_LINE = "off_line"
    NORMAL = "normal"
    ABNORMAL = "abnormal"


class Distribution(Enum):
    NORMAL = "normal"
    POISSON = "poisson"


class VllmMode(Enum):
    NORMAL = "normal"
    OPENAI = "openai"
