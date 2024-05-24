from functools import cached_property
import os
import time

import click
import numpy as np

from enova.common.cli_helper import DockerComposeHeler, parse_extra_args
from enova.common.config import CONFIG
from enova.common.constant import Distribution
from enova.common.logger import LOGGER
from enova.common.utils import datetime2timestamp, get_enova_path


class BaseEnovaDockerCompose:
    def __init__(self) -> None:
        self.is_run_by_compose = True

    @cached_property
    def docker_compose(self):
        return DockerComposeHeler()

    def stop(self):
        if self.is_run_by_compose:
            self.stop_by_compose()
        else:
            raise NotImplementedError()


class TrafficInjector(BaseEnovaDockerCompose):
    def __init__(self) -> None:
        super().__init__()
        self._svc_name = "traffic_injector"
        self._config_dir = os.path.join(get_enova_path(), CONFIG.traffic_injector["conf"])
        self._cache_dir = CONFIG.traffic_injector["cache_dir"]
        self._dataset_dir = CONFIG.traffic_injector["dataset_dir"]
        self._dataset_host_dir = CONFIG.traffic_injector["dataset_host_dir"]

    @staticmethod
    def generate_header_config_str(header_list):
        headers_str = ""
        for header in header_list:
            if ":" not in header:
                continue
            name, value = header.split(":")
            header_str = f"""\
            \n            <elementProp name="" elementType="Header">\
            \n              <stringProp name="Header.name">{name}</stringProp>\
            \n              <stringProp name="Header.value">{value}</stringProp>\
            \n            </elementProp>"""
            headers_str += header_str

        return headers_str

    @staticmethod
    def generate_data_config_str(variable_names):
        data_str = f"""\
        \n        <CSVDataSet guiclass="TestBeanGUI" testclass="CSVDataSet" testname="CSV Data Set Config">\
        \n          <stringProp name="delimiter">,</stringProp>\
        \n          <stringProp name="filename">/opt/data.csv</stringProp>\
        \n          <boolProp name="ignoreFirstLine">true</boolProp>\
        \n          <boolProp name="quotedData">true</boolProp>\
        \n          <boolProp name="recycle">true</boolProp>\
        \n          <stringProp name="shareMode">shareMode.all</stringProp>\
        \n          <stringProp name="variableNames">{variable_names}</stringProp>\
        \n        </CSVDataSet>\
        \n        <hashTree/>"""
        return data_str

    @staticmethod
    def generate_timer_config_str(timer_config):
        timer_str = ""
        if timer_config["type"] == "gaussian":
            timer_str = f"""\
            \n        <GaussianRandomTimer guiclass="GaussianRandomTimerGui" testclass="GaussianRandomTimer" testname="Gaussian Random Timer">\
            \n          <stringProp name="ConstantTimer.delay">{timer_config["delay"]}</stringProp>\
            \n          <stringProp name="RandomTimer.range">{timer_config["range"]}</stringProp>\
            \n        </GaussianRandomTimer>\
            \n        <hashTree/>"""
        elif timer_config["type"] == "poisson":
            timer_str = f"""\
            \n        <PoissonRandomTimer guiclass="PoissonRandomTimerGui" testclass="PoissonRandomTimer" testname="Poisson Random Timer">\
            \n          <stringProp name="ConstantTimer.delay">{timer_config["delay"]}</stringProp>\
            \n          <stringProp name="RandomTimer.range">{timer_config["range"]}</stringProp>\
            \n        </PoissonRandomTimer>\
            \n        <hashTree/>"""
        return timer_str

    @staticmethod
    def generate_load_profile_str(timer_config, duration):
        load_profile = ""
        if timer_config["type"] == Distribution.NORMAL.value:
            data = np.random.normal(timer_config["mean"], timer_config["std"], duration)
        else:
            data = np.random.poisson(timer_config["lambda"], duration)

        for value in data:
            value = max(value, 0)
            load_profile = (
                load_profile
                + f"""\
            \n          <collectionProp name="">\
            \n            <stringProp name="start">{value}</stringProp>\
            \n            <stringProp name="end">{value}</stringProp>\
            \n            <stringProp name="duration">1</stringProp>\
            \n          </collectionProp>"""
            )

        return load_profile

    def generate_jmeter_config(
        self,
        host,
        port,
        path,
        method,
        headers,
        body,
        duration,
        timer,
        data,
        output_dir,
    ):
        traffic_injector_dir = os.path.join(get_enova_path(), CONFIG.traffic_injector["conf"])
        config_template_path = os.path.join(traffic_injector_dir, "jmeter-config-template.xml")
        with open(config_template_path, "r") as fp:
            config_template_str = fp.read()
            config_template_str = config_template_str.replace("@HOST@", host)
            config_template_str = config_template_str.replace("@PORT@", str(port))
            config_template_str = config_template_str.replace("@PATH@", path)
            config_template_str = config_template_str.replace("@METHOD@", method.upper())
            config_template_str = config_template_str.replace("@BODY@", body)
            config_template_str = config_template_str.replace("@DURATION@", str(duration))
            config_template_str = config_template_str.replace(
                "@ELEMENT_PROP@", self.generate_header_config_str(headers.split(","))
            )
            config_template_str = config_template_str.replace(
                "@LOAD_PROFILE@", self.generate_load_profile_str(timer, duration)
            )

            if data is not None:
                data_path = self.get_data_file_path(data)
                with open(data_path, "r") as fp:
                    first_line = fp.readline().strip()
                config_template_str = config_template_str.replace("@DATA@", self.generate_data_config_str(first_line))
            else:
                config_template_str = config_template_str.replace("@DATA@", "")

        config_path = os.path.join(output_dir, "jmeter-config.xml")
        with open(config_path, "w") as fp:
            fp.write(config_template_str)

    def get_data_file_path(self, data):
        # TODO: also allow not in  enova-app container

        # data_file = os.path.join(self._dataset_host_dir, f"{data.lower()}.csv")
        dataset_dir = "/opt/enova/enova/template/deployment/docker-compose/traffic-injector/data"
        data_file = os.path.join(dataset_dir, f"{data.lower()}.csv")

        return data_file

    @staticmethod
    def generate_env_config(env_dict, output_dir):
        config_path = os.path.join(output_dir, ".env")
        with open(config_path, "w") as fp:
            for k in env_dict:
                fp.write(f"{k}={env_dict[k]}\n")

    def run(
        self,
        host,
        port,
        path,
        method="GET",
        duration=5,
        timer=None,
        container_name=None,
        **kwargs,
    ):
        if timer is None:
            timer = {"type": Distribution.NORMAL.value, "mean": 1, "std": 1}

        headers = "Accept:*/*"
        if kwargs.get("headers") is not None:
            headers = kwargs.get("headers")

        body = ""
        if kwargs.get("body") is not None:
            body = kwargs.get("body")

        output = "default"
        if kwargs.get("output") is not None:
            output = kwargs.get("output")

        data = None
        if kwargs.get("data") is not None:
            data = kwargs.get("data")

        if not os.path.exists(self._cache_dir):
            LOGGER.info(f"[Traffic Injector] create cache dir {self._cache_dir}")
            os.makedirs(CONFIG.traffic_injector["cache_dir"])

        output_dir = os.path.join(self._cache_dir, output)
        if not os.path.exists(output_dir):
            LOGGER.info(f"[Traffic Injector] create output dir {output_dir}")
            os.makedirs(output_dir)

        if not os.path.exists(self._dataset_dir):
            LOGGER.info(f"[Traffic Injector] create dataset dir {self._dataset_dir}")
            os.makedirs(CONFIG.traffic_injector["dataset_dir"])

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
                    LOGGER.error("[Traffic Injector] invalid end time: end time before start time")
                    return

                duration = end_timestamp - start_timestamp

        self.generate_jmeter_config(host, port, path, method, headers, body, duration, timer, data, output_dir)

        dataset_name = str.lower(data)
        options = {
            "container_name": container_name,
            "volumes": [
                f"{CONFIG.traffic_injector['dataset_host_dir']}/{dataset_name}.csv:/opt/data.csv",
                f"{output_dir}:/data",
                f"{CONFIG.traffic_injector['cache_dir']}:{CONFIG.traffic_injector['cache_dir']}",
            ],
        }
        self.docker_compose.update_service_options(self._svc_name, options)
        self.docker_compose.startup_service(self._svc_name, is_daemon=True)

    def stop_by_compose(self):
        self.docker_compose.down_service(self._svc_name)

    def status(self, container_name):
        return self.docker_compose.get_service_state(self._svc_name)


pass_enova_injector = click.make_pass_decorator(TrafficInjector)


@click.group(name="injector")
@click.pass_context
def injector_cli(ctx):
    """
    Run the autoscaling service.
    """
    ctx.obj = TrafficInjector()


@injector_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--host", type=str)
@click.option("--port", type=int)
@click.option("--path", type=str)
@click.option("--method", type=str, default="GET")
@click.option("--duration", type=int, default=5)
@click.option("--timer", type=str, default=None)
@click.option("--container-name", "--container_name", "container_name", type=str, default=None)
@pass_enova_injector
@click.pass_context
def injector_run(
    ctx,
    enova_injector: TrafficInjector,
    host,
    port,
    path,
    method,
    duration,
    timer,
    container_name,
):
    enova_injector.run(
        host=host,
        port=port,
        path=path,
        method=method,
        duration=duration,
        timer=timer,
        container_name=container_name,
        **parse_extra_args(ctx),
    )
