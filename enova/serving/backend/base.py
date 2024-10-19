import abc
import dataclasses
import uvicorn
from enova.common.logger import LOGGER
import pandas as pd
from typing import Dict

@dataclasses.dataclass
class BaseBackend(metaclass=abc.ABCMeta):
    name: str
    model: str

    @abc.abstractmethod
    def _create_app(self):
        """"""

    def _create_apiserver(self):
        self._create_app()
        self._init_middlewares()
        self._init_routers()

    def _init_middlewares(self):
        """"""

    def _init_exception_handler(self):
        """"""

    def _init_routers(self):
        """ """

    def local_run(self, host, port):
        """"""
        self._create_apiserver()
        self._create_injector(host, port)
        self.print_run_info(host, port)
        uvicorn.run(self.app, host=host, port=port)

    def print_run_info(self, host, port):
        # Send the welcome message, especially to make sure that users will know
        # whicl URL to visit in order to not get a "not found" error.
        LOGGER.info(f"host: {host}, port: {port}")

    def _create_injector(self, host, port):
        """"""
        from enova.common.constant import (
            Distribution,
            TrafficDistributionType,
            VllmMode,
        )
        from enova.common.error import (
            TestStartError,
        )
        from enova.serving.backend.injector import VanillaTrafficInjector
        @self.app.post("/v1/inject")
        def stress_test(params: Dict):
            """
            stress test a served 
            """

            test_info = {
                "test_spec": params["test_spec"],
                "data_set": params["data_set"],
            }
            traffic_injector_path_map = {
                VllmMode.NORMAL.value: "/generate",
                # TODO: adapt /v1/chat/completions
                VllmMode.OPENAI.value: "/v1/completions",
            }

            test_spec = test_info["test_spec"]
            if test_spec["distribution"] == TrafficDistributionType.GAUSSIAN.value:
                timer = {"type": Distribution.NORMAL.value, "mean": test_spec["tps_mean"], "std": test_spec["tps_std"]}
            elif test_spec["distribution"] == TrafficDistributionType.POISSON.value:
                timer = {"type": Distribution.POISSON.value, "lambda": test_spec["tps_mean"]}
            else:
                distribution = test_spec["distribution"]
                LOGGER.exception(f"distribution {distribution} not allow.")
                raise NotImplementedError()

            vllm_mode = VllmMode.OPENAI.value # TODO: CONFIG.vllm.get("vllm_mode") has been consumed by vllm at __post_init__
            path = traffic_injector_path_map[vllm_mode]

            try:
                injector = VanillaTrafficInjector()
                injector.run(
                    host=host,
                    port=port,
                    path=path,
                    method="post",
                    duration=int(pd.Timedelta(str(test_spec["duration"])+test_spec["duration_unit"]).total_seconds()),
                    timer=timer,
                    data=test_info["data_set"],
                    headers={"Content-Type":"application/json"},
                    model=self.model,
                )
                return True
            except TestStartError as e:
                LOGGER.error(e.message)
                return False
