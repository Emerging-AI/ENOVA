import abc
import dataclasses
import uvicorn
from enova.common.logger import LOGGER
from enova.server.restful.serializer import EmergingAIBaseModel
import pandas as pd
from typing import Literal, Optional

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
        from enova.serving.backend.injector import ThreadpoolBasedTrafficInjector
        from enova.common.config import CONFIG
        class InjectionRequest(EmergingAIBaseModel):
            distribution: Literal[TrafficDistributionType.GAUSSIAN.value, TrafficDistributionType.POISSON.value]
            tps_mean: int
            tps_std: Optional[int] = None
            duration: int
            duration_unit: str
            data_set: str
        @self.app.post("/v1/inject")
        def stress_test(params: InjectionRequest):
            """
            stress test a served 
            """

            traffic_injector_path_map = {
                VllmMode.NORMAL.value: "/generate",
                # TODO: adapt /v1/chat/completions
                VllmMode.OPENAI.value: "/v1/completions",
            }

            if params.distribution == TrafficDistributionType.GAUSSIAN.value:
                timer = {"type": Distribution.NORMAL.value, "mean": params.tps_mean, "std": params.tps_std}
            elif params.distribution == TrafficDistributionType.POISSON.value:
                timer = {"type": Distribution.POISSON.value, "lambda": params.tps_mean}
            else:
                distribution = params.distribution
                LOGGER.exception(f"distribution {distribution} not allow.")
                raise NotImplementedError()

            vllm_mode = CONFIG.enova_serving_run_args["vllm_mode"]
            path = traffic_injector_path_map[vllm_mode]

            try:
                injector = ThreadpoolBasedTrafficInjector()
                injector.run(
                    host=host,
                    port=port,
                    path=path,
                    method="post",
                    duration=int(pd.Timedelta(str(params.duration)+params.duration_unit).total_seconds()),
                    timer=timer,
                    data=params.data_set,
                    headers={"Content-Type":"application/json"},
                    model=self.model,
                )
                return True
            except TestStartError as e:
                LOGGER.error(f"{type(e).__name__}: {str(e)}")
                return False
