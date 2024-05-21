import logging
import re
import threading
import time
from typing import Iterable

from opentelemetry import metrics
from opentelemetry.metrics import CallbackOptions, Observation

meter = metrics.get_meter(__name__)

metric_info = {
    "avg_prompt_throughput": {"value": 0.0, "unit": "tokens/s", "last_update": time.time()},
    "avg_generation_throughput": {"value": 0.0, "unit": "tokens/s", "last_update": time.time()},
    "running_requests": {"value": 0.0, "unit": "requests", "last_update": time.time()},
    "swapped_requests": {"value": 0.0, "unit": "requests", "last_update": time.time()},
    "pending_requests": {"value": 0.0, "unit": "requests", "last_update": time.time()},
    "gpu_kv_cache_usage": {"value": 0.0, "unit": "%", "last_update": time.time()},
    "cpu_kv_cache_usage": {"value": 0.0, "unit": "%", "last_update": time.time()},
}

timeout_seconds = 15

for metric_name, info in metric_info.items():
    def create_scrape_metric_callback(metric_name):
        def scrape_metric_callback(options: CallbackOptions) -> Iterable[Observation]:
            value = metric_info[metric_name]["value"]
            yield Observation(value, attributes={})

        return scrape_metric_callback

    callback = create_scrape_metric_callback(metric_name)
    unit = info["unit"]

    meter.create_observable_gauge(
        name=metric_name,
        callbacks=[callback],
        description=f"The value of {metric_name}",
        unit=unit
    )


def update_metric(name, value, current_time):
    metric_info[name]["value"] = value
    metric_info[name]["last_update"] = current_time


class VLLMLogMetricsAdapter(logging.Handler):
    def __init__(self):
        super().__init__()
        self.pattern = re.compile(
            r".*?"
            r"Avg prompt throughput: (?P<avg_prompt>\d+\.\d+) tokens/s, "
            r"Avg generation throughput: (?P<avg_gen>\d+\.\d+) tokens/s, "
            r"Running: (?P<running>\d+) reqs, "
            r"Swapped: (?P<swapped>\d+) reqs, "
            r"Pending: (?P<pending>\d+) reqs, "
            r"GPU KV cache usage: (?P<gpu_cache>\d+\.\d+)%, "
            r"CPU KV cache usage: (?P<cpu_cache>\d+\.\d+)%"
        )

    def emit(self, record):
        log_message = record.getMessage()
        match = self.pattern.search(log_message)
        if match:
            current_time = time.time()
            update_metric("avg_prompt_throughput", float(match.group("avg_prompt")), current_time)
            update_metric("avg_generation_throughput", float(match.group("avg_gen")), current_time)
            update_metric("running_requests", float(match.group("running")), current_time)
            update_metric("swapped_requests", float(match.group("swapped")), current_time)
            update_metric("pending_requests", float(match.group("pending")), current_time)
            update_metric("gpu_kv_cache_usage", float(match.group("gpu_cache")), current_time)
            update_metric("cpu_kv_cache_usage", float(match.group("cpu_cache")), current_time)


def update_metrics_periodically():
    while True:
        for metric_name, info in metric_info.items():
            current_time = time.time()
            if current_time - info["last_update"] > timeout_seconds:
                metric_info[metric_name]["value"] = 0.0  # Reset the value if the data is stale
        time.sleep(5)  # Update every 5 seconds


# Start the background thread to update metrics periodically
threading.Thread(target=update_metrics_periodically, daemon=True).start()
