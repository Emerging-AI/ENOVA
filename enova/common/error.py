from enova.common.config import CONFIG


class EmergingAIBaseError(Exception):
    BASE_ERROR_CODE: str = CONFIG.BASIC_ERROR_CODE or "100"
    MODULE_CODE: str = CONFIG.MODULE_CODE or "001"
    ERROR_CODE: str = "000"
    ERROR_MESSAGE: str = ""

    def __init__(self, error_message=None, error_code=None, *args, **kwargs):
        self.error_code = error_code if error_code is not None else self.ERROR_CODE
        self.error_code = f"{self.BASE_ERROR_CODE}{self.MODULE_CODE}{self.error_code}"

        self.error_message = error_message if error_message is not None else self.ERROR_MESSAGE
        self.message = self.error_message
        self.code = int(self.error_code)
        errors = []
        if kwargs.get("errors", None):
            errors = kwargs["errors"] if isinstance(kwargs["errors"], list) else [kwargs["errors"]]
            del kwargs["errors"]
        self.errors = errors
        kwargs["args"] = args

        super(EmergingAIBaseError, self).__init__(self.error_message, self.error_code, kwargs, errors)


class ArgsError(EmergingAIBaseError):
    ERROR_CODE: str = "001"
    ERROR_MESSAGE: str = "args error"


class TranslationError(EmergingAIBaseError):
    ERROR_CODE: str = "091"
    ERROR_MESSAGE: str = "translation error"


# --
class EmergingaiAPIResponseError(EmergingAIBaseError):
    ERROR_CODE: str = "010"
    ERROR_MESSAGE: str = "response error"


class APIParamsError(EmergingAIBaseError):
    ERROR_CODE: str = "011"
    ERROR_MESSAGE: str = "response error"


# --- enode backend api ---
class EScalerApiResponseError(EmergingAIBaseError):
    ERROR_CODE: str = "101"
    ERROR_MESSAGE: str = "node api response error"


class DeploymentInstanceExistError(EmergingAIBaseError):
    ERROR_CODE: str = "401"
    ERROR_MESSAGE: str = "deployment workload had existed"


class DeploymentInstanceNotExistError(EmergingAIBaseError):
    ERROR_CODE: str = "402"
    ERROR_MESSAGE: str = "deployment workload is not exist"


class DeploymentInstanceCreateFailedError(EmergingAIBaseError):
    ERROR_CODE: str = "403"
    ERROR_MESSAGE: str = "deployment workload create failed"


class TestNotExistError(EmergingAIBaseError):
    ERROR_CODE: str = "403"
    ERROR_MESSAGE: str = "test record is not exist"


class JmeterContainerLaunchError(EmergingAIBaseError):
    ERROR_CODE: str = "404"
    ERROR_MESSAGE: str = "fail to launch jmeter container"


class TestStartError(EmergingAIBaseError):
    ERROR_CODE: str = "406"
    ERROR_MESSAGE: str = "test start failed"


class DataFileNotExistError(EmergingAIBaseError):
    ERROR_CODE: str = "407"
    ERROR_MESSAGE: str = "data file not existed"


# ----


class NotReadyError(EmergingAIBaseError):
    ERROR_CODE: str = "101"
    ERROR_MESSAGE: str = "support service not ready"


class BackendConfigMissingError(EmergingAIBaseError):
    ERROR_CODE: str = "102"
    ERROR_MESSAGE: str = "backend default config missing"
