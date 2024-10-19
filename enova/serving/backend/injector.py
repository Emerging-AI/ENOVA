import time
import numpy as np
import requests
import itertools
import csv
import threading
from enova.common.constant import Distribution
from enova.common.error import TestStartError
from enova.common.logger import LOGGER
from enova.common.utils import datetime2timestamp, get_enova_path


class VanillaTrafficInjector:
    def run(
        self,
        host,
        port,
        path,
        method="GET",
        duration=5,
        timer={"type": Distribution.POISSON.value, "lambda": 1},
        model = "",
        api_key="",
        max_tokens = 500,
        temperature = 0.9,
        **kwargs,
    ):
        """
        standard entry of the traffic injector
        """

        headers = {"Accept":"*/*"}
        if kwargs.get("headers") is not None:
            headers = kwargs.get("headers")

        data = None
        if kwargs.get("data") is not None:
            data = kwargs.get("data")

        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        

        start_time = kwargs.get("start_time")
        sleep_duration = 0
        if start_time is not None:
            start_timestamp = datetime2timestamp(start_time)
            now_timestamp = time.time()
            if start_timestamp < now_timestamp:
                start_timestamp = now_timestamp
                LOGGER.info("[Traffic Injector] start time before current time, use current time as start time")

            sleep_duration = start_timestamp - now_timestamp
            end_time = kwargs.get("end_time")
            if end_time is not None:
                end_timestamp = datetime2timestamp(end_time)
                if start_timestamp >= end_timestamp:
                    raise TestStartError("[Traffic Injector] invalid end time: end time before start time")

                duration = end_timestamp - start_timestamp

        if method.lower() == "get":
            request_method = requests.get
        elif method.lower() == "post":
            request_method = requests.post
        else:
            raise TestStartError("[Traffic Injector] invalid method: method not supported")

        dataset_name = str.lower(data)
        dataset_path = f"{get_enova_path()}/template/deployment/docker-compose/traffic-injector/data/{dataset_name}.csv"
        with open(dataset_path) as dataset_in:
            reader = csv.DictReader(dataset_in)
            dataset = [s for s in reader]
            for i, sample in enumerate(dataset):
                # NOTE: only fits for OpenAI API server
                if sample.get("answer"):
                    del dataset[i]["answer"]
                if sample.get("id"):
                    del dataset[i]["id"]
                if not sample.get("prompt") and sample.get("question"):
                    dataset[i]["prompt"] = dataset[i].pop("question", None)
                dataset[i]["model"] = model
                dataset[i]["max_tokens"] = max_tokens
                dataset[i]["temperature"] = temperature
        dataset_iter = itertools.cycle(dataset) # NOTE: match JMeter's recycle:True

        # initialize timer
        if timer['type'] == Distribution.POISSON.value:
            delay_iter = iter(np.random.poisson(timer["lambda"],duration))
        elif timer['type'] == Distribution.NORMAL.value:
            delay_iter = iter(np.random.normal(timer["mean"], timer["std"], duration))
        else:
            raise TestStartError(f"VanillaTrafficInjector: argument 'timer' provided is invalid, got {timer} instead")
        def make_request(request_func, url, headers, json_data):
            request_func(url, headers=headers, json=json_data)
        threads_started = []
        while True:
            try:
                sleep_duration = next(delay_iter)
            except StopIteration:
                break
            thread = threading.Thread(target=make_request, args=(request_method, f"http://{host}:{port}{path}", headers, next(dataset_iter)))
            thread.start()
            threads_started.append(thread)
            time.sleep(sleep_duration)
        for thread in threads_started:
            thread.join()