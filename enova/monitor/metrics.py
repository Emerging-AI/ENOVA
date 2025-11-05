import abc
import threading
import os
import json
import time
from enova.common.logger import LOGGER

DEFAULT_REPORT_TIME = 60


class MetricsReporter(threading.Thread, metaclass=abc.ABCMeta):
    def __init__(self, log_dir, name="metric_report", *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.log_dir = log_dir
        self.name = name
        self.full_log_dir = os.path.join(self.log_dir, self.name)
        self.stopped = False

    @abc.abstractmethod
    def _post_init_(self):
        """"""

    @abc.abstractmethod
    def _run_once(self):
        pass

    def run(self):
        self._post_init_()
        while not self.stopped:
            try:
                self._run_once()
            except Exception as e:
                LOGGER.exception(f"{self.__class__} _run_once error: {str(e)}")
            finally:
                time.sleep(DEFAULT_REPORT_TIME)

    def stop(self):
        self.stopped = True
        self.join()


class NVMetricsReporter(MetricsReporter):

    def _post_init_(self):
        import pynvml

        pynvml.nvmlInit()
        gpu_count = pynvml.nvmlDeviceGetCount()
        self.handles = [pynvml.nvmlDeviceGetHandleByIndex(i) for i in range(gpu_count)]

    def _run_once(self):
        """"""
        import pynvml

        node_rank = os.environ.get("NODE_RANK") or "0"
        for i, handle in enumerate(self.handles):
            memory_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            utilization = pynvml.nvmlDeviceGetUtilizationRates(handle)
            info = {
                "timestamp": int(time.time()),
                "utilization": utilization.gpu,
                "total_memory": memory_info.total,
                "free_memory": memory_info.free,
                "used_memory": memory_info.used,
                "gpu": i,
                "node_rank": node_rank,
            }
            with open(self.full_log_dir, "a") as w:
                w.write(f"{json.dumps(info)}\n")


class AscendMetricsReporter(MetricsReporter):

    def _post_init_(self):
        self.device_ids = [int(d) for d in os.environ["ASCEND_VISIBLE_DEVICES"].split(",")]

    def _run_once(self):
        """"""
        import acl

        node_rank = os.environ.get("NODE_RANK") or "0"
        for device_id in self.device_ids:
            utilization_info, ret = acl.rt.get_device_utilization_rate(device_id)
            info = {"timestamp": int(time.time()), "utilization": utilization_info.aicpu_utilization, "gpu": device_id, "node_rank": node_rank}
            with open(self.full_log_dir, "a") as w:
                w.write(f"{json.dumps(info)}\n")


class MetricsReporterFactory:

    @classmethod
    def create_reporter(self, log_dir) -> MetricsReporter:
        """"""
        import torch

        if hasattr(torch, "npu") and torch.npu.is_available():
            return AscendMetricsReporter(log_dir)
        return NVMetricsReporter(log_dir)
