import asyncio
import dataclasses
import inspect
import json
import os
import subprocess
import sys
import time
from functools import cached_property
from types import FrameType
from typing import Any, ClassVar

import fire
import numpy as np
import yaml

from enova.common.config import CONFIG
from enova.common.constant import DeployMode, Distribution, ServingBackend
from enova.common.logger import LOGGER
from enova.common.utils import camel_to_snake, datetime2timestamp, get_enova_path
from enova.enode.hf import HFText2TextEnode
from enova.serving.apiserver import EApiServer

cli_new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(cli_new_loop)
cli_loop = asyncio.get_event_loop()


@dataclasses.dataclass
class CliCommandArgumentHelper:
    command: Any
    sys_frame: FrameType
    _counter: ClassVar[int] = 0  # Class variable to keep track of the number of instances

    def __post_init__(self):
        type(self)._counter += 1
        self.order_counter = type(self)._counter

        func_name = self.sys_frame.f_code.co_name
        func_obj = getattr(self.command, func_name)
        args = inspect.getfullargspec(func_obj).args
        if args and args[0] == "self":
            args = args[1:]

        f_locals = self.sys_frame.f_locals
        args_map = {arg: f_locals.get(arg) for arg in args}
        args_map.update(f_locals.get("kwargs", {}))
        args_map.update({"call_order": self.order_counter})
        self.args_map = {camel_to_snake(f"{self.command.__class__.__name__}_{func_name}_args"): args_map}


class DockerComposeHeler:
    def __init__(self) -> None:
        base_enova_path = get_enova_path()
        self.excu = os.path.join(base_enova_path, CONFIG.deploy["docker_compose_exce"])
        self.compose_file = os.path.join(base_enova_path, "template/deployment/docker-compose/compose.yaml")
        with open(self.compose_file, "r") as file:
            self.compose_config = yaml.safe_load(file)
            # LOGGER.debug(f"compose init config: {self.compose_config}")
        # self.tmp_id = gen_ulid()
        self.tmp_compose_file = os.path.join(base_enova_path, "template/deployment/docker-compose/enova_compose.yaml")
        with open(self.tmp_compose_file, "w") as file:
            yaml.dump(self.compose_config, file)

        self._base_cmd = [self.excu, "-f"]

    @property
    def base_cmd(self):
        updated_cmd = self._base_cmd.copy()
        updated_cmd.append(self.tmp_compose_file)
        return updated_cmd

    def _run_command(self, command):
        cmd_str = " ".join(command)
        LOGGER.debug("Command: {}".format(cmd_str))
        result = subprocess.run(command, shell=False, capture_output=True)
        # result = subprocess.check_output(command, shell=False)
        if result.returncode != 0:
            raise subprocess.CalledProcessError(returncode=result.returncode, cmd=result.args, stderr=result.stderr)
        if result.stdout:
            LOGGER.debug("Command Result: {}".format(result.stdout.decode("utf-8")))
        return result

    def _get_service_config(self, service) -> dict:
        if service in self.compose_config.get("services", {}):
            return self.compose_config["services"][service]
        return {}

    def update_service_options(self, service, options):
        if not options:
            return

        service_config = self._get_service_config(service)
        if not service_config:
            return

        service_config.update(options)
        LOGGER.debug(f"updated service config: {service_config}")
        self.compose_config["services"][service] = service_config
        LOGGER.debug(f"updated compose file: {self.tmp_compose_file}")
        with open(self.tmp_compose_file, "w") as file:
            yaml.dump(self.compose_config, file)

    def get_service_option(self, service, option_name):
        service_config = self._get_service_config(service)
        if not service_config:
            return

        return service_config.get(option_name)

    def _extract_state(self, service_infos):
        service_info_lst = [json.loads(jline) for jline in service_infos.splitlines()]
        if not service_info_lst:
            return None

        service_info = service_info_lst[0]
        service_state = service_info["State"]
        return service_state

    def get_service_state(self, service):
        """
        output: None / [paused | restarting | removing | running | dead | created | exited]
            None: this service isnot exist in docker server
            other:
        """
        cmd_params = self.base_cmd.copy()
        cmd_params += ["ps", service, "--all", "--no-trunc", "--format", "json"]

        cmd_ret = self._run_command(cmd_params)

        service_state = self._extract_state(cmd_ret.stdout)
        if not service_state:
            LOGGER.debug(f"service {service} not existed")
        else:
            LOGGER.debug(f"service {service}' state is {service_state}")
        return service_state

    def startup_service(self, service: str, is_daemon=False):
        cmd_params = self.base_cmd
        cmd_params += ["up", service]

        if is_daemon:
            cmd_params.append("-d")

        cmd_ret = self._run_command(cmd_params)
        return cmd_ret

    def stop_service(self, service):
        cmd_params = self.base_cmd
        cmd_params += ["down", service]

        cmd_ret = self._run_command(cmd_params)
        return cmd_ret

    def down_service(self, service):
        cmd_params = self.base_cmd
        cmd_params += ["down", service]

        cmd_ret = self._run_command(cmd_params)
        return cmd_ret

    def down_all(self):
        cmd_params = self.base_cmd.copy()
        cmd_params += ["down"]

        result = subprocess.run(cmd_params, capture_output=True, text=True)
        if result.returncode == 0:
            LOGGER.info("all service down successfully")
        else:
            LOGGER.error(f"all service stop failed, {result.stderr}")

    def get_svc_info(self, svc):
        """"""
        cmd_params = self.base_cmd
        cmd_params += ["ps", "--no-trunc", "--format", "json"]

        result = subprocess.run(cmd_params, capture_output=True, text=True)
        # TODO: extract and reform the output
        # LOGGER.info(f"result: {result}")
        service_info_lst = [json.loads(jline) for jline in result.stdout.splitlines()]
        for service_info in service_info_lst:
            service_info["Service"] == svc
            return service_info
        return None


class EnodeHandler:
    """
    enode handler
    """

    def __init__(self, host, port, model, backend):
        self.host = host
        self.port = port
        self.model = model
        self.enode = HFText2TextEnode(model)
        if backend == ServingBackend.HF.value:
            self.enode.init()
        self.apiserver = EApiServer(host, port, self.enode, backend)

    def start(self, **kwargs):
        self.apiserver.local_run(**kwargs)

    def stop(self, *args):
        """"""


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


class Monitor:
    def __init__(self) -> None:
        self.docker_services = [
            "dcgm-exporter",
            "grafana",
            "otel-collector",
            "prometheus",
            "tempo",
            "enova-pilot",
            "enova-algo",
        ]  # start up by order
        self._docker_compose = DockerComposeHeler()
        self._is_run_by_compose = True  # TODO:

    def _run_by_compose(self):
        for service in self.docker_services:
            # options = CONFIG.get_user_args()
            user_args = CONFIG.get_user_args()
            print(user_args)
            options = {}
            self._docker_compose.update_service_options(service, options)
            self._docker_compose.startup_service(service, is_daemon=True)

    def run(self, **kwargs):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._is_run_by_compose:
            self._run_by_compose()
        else:
            raise NotImplementedError()

    def start(
        self,
        is_deamon=True,
        **kwargs,
    ):
        """"""
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        cmd_params = self._docker_compose.base_cmd
        if is_deamon:
            cmd_params += ["up", "-d"]
        else:
            cmd_params += ["up"]

        result = subprocess.run(cmd_params, capture_output=True, text=True)
        if result.returncode != 0:
            raise Exception(f"monitors start failed: result: {result}")
        LOGGER.info(f"result: {result}")

    def status(self):
        cmd_params = self._docker_compose.base_cmd
        cmd_params += ["ps", "--no-trunc", "--format", "json"]

        result = subprocess.run(cmd_params, capture_output=True, text=True)
        # TODO: extract and reform the output
        # LOGGER.info(f"result: {result}")
        service_info_lst = [json.loads(jline) for jline in result.stdout.splitlines()]
        for service_info in service_info_lst:
            print(json.dumps(service_info))
        return service_info_lst

    def stop(self):
        cmd_params = self._docker_compose.base_cmd
        cmd_params += ["down"]

        result = subprocess.run(
            [self._docker_compose.excu, "-f", self._docker_compose.compose_file, "down"],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            LOGGER.info("llmo monitors stop successfully")
        else:
            LOGGER.error(f"llmo monitors stop failed, {result.stderr}")


class Webui:
    def __init__(self):
        self.streamlit_process = None

    def start(self, serving_host, serving_port, host, port):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        os.environ["SERVING_URL"] = f"http://{serving_host}:{serving_port}/generate"

        base_enova_path = get_enova_path()
        streamlit_script = os.path.join(base_enova_path, CONFIG.webui["script"])
        self.streamlit_process = subprocess.Popen(
            ["streamlit", "run", streamlit_script, "--server.port", str(port), "--server.address", host]
        )

    def run(
        self,
        serving_host=CONFIG.serving["host"],
        serving_port=CONFIG.serving["port"],
        host=CONFIG.webui["host"],
        port=CONFIG.webui["port"],
        run_background=False,
        **kwargs,
    ):
        """"""
        self.start(serving_host, serving_port, host, port)
        if not run_background:
            self.streamlit_process.wait()

    def stop(self):
        self.streamlit_process.terminate()
        self.streamlit_process.wait()


class Enode:
    def __init__(self, is_run_by_compose=False) -> None:
        self.docker_services = ["enova-enode", "nginx"]  # start up by order
        self._docker_compose = DockerComposeHeler()
        self._is_run_by_compose = is_run_by_compose

    def _run_by_compose(self):
        pass

    def run(
        self,
        model,
        host=CONFIG.serving["host"],
        port=CONFIG.serving["port"],
        backend=CONFIG.serving["backend"],
        exporter_endpoint=CONFIG.llmo["eai_exporter_endpoint"],
        exporter_service_name=CONFIG.llmo["eai_exporter_service_name"],
        include_webui=True,
        hf_proxy=None,
        **kwargs,
    ):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._is_run_by_compose:
            self._run_by_compose()
        else:
            from enova.llmo import start as llmo_start

            CONFIG.update_config({backend: kwargs})
            # CONFIG.print_config()
            llmo_start(otlp_exporter_endpoint=exporter_endpoint, service_name=exporter_service_name)
            if include_webui:
                Webui().run(run_background=True)
            EnodeHandler(host, port, model, backend).start()


class EnodeProxyNginx:
    def __init__(self, is_run_by_compose=True) -> None:
        self._svc_name = "enova-nginx"
        self.docker_services = ["nginx"]  # start up by order
        self._docker_compose = DockerComposeHeler()
        self._is_run_by_compose = is_run_by_compose

    def _run_by_compose(self):
        # TODO:
        for service in self.docker_services:
            # options = CONFIG.get_user_args()
            user_args = CONFIG.get_user_args()
            print(user_args)
            options = {}
            self._docker_compose.update_service_options(service, options)
            self._docker_compose.startup_service(service, is_daemon=True)

    def _stop_by_compose(self):
        for service in self.docker_services:
            self._docker_compose.down_service(service)

    def run(
        self,
        host=CONFIG.serving["host"],
        port=CONFIG.serving["port"],
    ):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._is_run_by_compose:
            self._run_by_compose()
        else:
            raise NotImplementedError()

    def stop(self):
        if self._is_run_by_compose:
            self._stop_by_compose()
        else:
            raise NotImplementedError()


class WebuiProxyNginx:
    def __init__(self, is_run_by_compose=True) -> None:
        self._svc_name = "enova-webui-nginx"
        self.docker_services = ["webui-nginx"]  # start up by order
        self._docker_compose = DockerComposeHeler()
        self._is_run_by_compose = is_run_by_compose

    def _run_by_compose(self):
        # TODO:
        for service in self.docker_services:
            # options = CONFIG.get_user_args()
            user_args = CONFIG.get_user_args()
            print(user_args)
            options = {}
            self._docker_compose.update_service_options(service, options)
            self._docker_compose.startup_service(service, is_daemon=True)

    def _stop_by_compose(self):
        for service in self.docker_services:
            self._docker_compose.down_service(service)

    def run(
        self,
        host=CONFIG.serving["host"],
        port=CONFIG.serving["port"],
    ):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._is_run_by_compose:
            self._run_by_compose()
        else:
            raise NotImplementedError()

    def stop(self):
        if self._is_run_by_compose:
            self._stop_by_compose()
        else:
            raise NotImplementedError()


class EnovaPurePilot:
    @cached_property
    def enova_app(self):
        return EnovaApp(deploy_mode=DeployMode.COMPOSE.value)

    @cached_property
    def nginx(self):
        return EnodeProxyNginx()

    @cached_property
    def webui_nginx(self):
        return WebuiProxyNginx()

    @cached_property
    def mon(self):
        return Monitor()

    def status(self):
        return self.mon.status()

    def run(self, failed_with_stop=False, *args, **kwars):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        # TODO: check container's status
        try:
            self.nginx.run()
        except Exception as e:
            LOGGER.warning(f"nginx start failed: err: {str(e)}")
            if failed_with_stop:
                self.nginx.stop()

        try:
            self.webui_nginx.run()
        except Exception as e:
            LOGGER.warning(f"webui_nginx start failed: err: {str(e)}")
            if failed_with_stop:
                self.webui_nginx.stop()

        try:
            self.mon.run()
        except Exception as e:
            LOGGER.warning(f"monitor start failed: err: {str(e)}")
            if failed_with_stop:
                self.mon.stop()
        try:
            self.enova_app.run(
                host=kwars["enova_app_host"],
                port=kwars["enova_app_port"],
            )
        except Exception as e:
            LOGGER.warning(f"enova_app start failed: err: {str(e)}")
            if failed_with_stop:
                self.enova_app.stop()

    def stop(self):
        try:
            self.nginx.stop()
            self.webui_nginx.stop()
            self.mon.stop()
            self.enova_app.stop()
        except Exception as e:
            raise e


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


class EnovaAlgo:
    def run(self):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        import uvicorn

        from enova.algo.server import get_algo_api_server

        api_server = get_algo_api_server()
        uvicorn.run(api_server.app, host=CONFIG.enova_algo["host"], port=CONFIG.enova_algo["port"])


class EnovaApp:
    def __init__(self, deploy_mode: DeployMode = DeployMode.LOCAL.value) -> None:
        self._svc_name = "enova-app"
        self._docker_compose = DockerComposeHeler()
        self._deploy_mode = deploy_mode

    def _run_local(self, host, port):
        import uvicorn

        from enova.app.server import get_app_api_server

        api_server = get_app_api_server()
        uvicorn.run(api_server.app, host=host, port=port)

    def _get_dataset_dir(self):
        # base_enova_path = get_enova_path()
        base_enova_path = "/opt/enova/enova"  # TODO:
        dataset_dir = os.path.join(base_enova_path, "template/deployment/docker-compose/traffic-injector/data")

        return dataset_dir

    def _run_compose(self, host, port):
        """
        - first stop svc
        - update svc options
        - start up svc
        """

        self._docker_compose.stop_service(self._svc_name)

        svc_cmd = ["enova", "app", "run", "--host", host, "--port", port]
        environment_lst = self._docker_compose.get_service_option(self._svc_name, "environment") or []
        volumes_lst = self._docker_compose.get_service_option(self._svc_name, "volumes") or []

        def check_local_model_dir(dir_path):
            if os.path.isabs(dir_path):
                if not os.path.exists(dir_path):
                    raise FileNotFoundError(f"Directory not found: {dir_path}")
                if not os.path.isdir(dir_path):
                    raise FileNotFoundError(f"{dir_path} is a Directory")
                return True
            else:
                maybe_rel = os.path.abspath(dir_path)
                if os.path.exists(maybe_rel) and os.path.isdir(maybe_rel):
                    return True

            return False

        if isinstance(environment_lst, list):
            user_args = CONFIG.get_user_args()
            if "hf_proxy" in user_args.keys() and user_args["hf_proxy"]:
                hf_proxy = user_args["hf_proxy"]
                environment_lst.append(f"EMERGINGAI_ENOVA_APP_HF_PROXY={hf_proxy}")

            if "model" in user_args.keys() and user_args["model"]:
                model_dir = user_args["model"]
                if check_local_model_dir(model_dir):
                    environment_lst.append(f"EMERGINGAI_ENOVA_APP_HOST_MODEL_DIR={model_dir}")
                    volumes_lst.append(f"{model_dir}:{CONFIG.enova_app['model_dir']}")
                    LOGGER.info(f"use local model: {model_dir}")
                    LOGGER.debug(f"maping local model in compose: {CONFIG.enova_app['model_dir']}")
                else:
                    LOGGER.info(f"use remote model: {model_dir}")

            environment_lst.append("EMERGINGAI_ENOVA_APP_USER_ARGS=" + json.dumps(user_args))

        # traffic inject setup
        os.makedirs(CONFIG.traffic_injector["cache_dir"], exist_ok=True)
        os.makedirs(CONFIG.traffic_injector["dataset_host_dir"], exist_ok=True)
        dataset_dir = self._get_dataset_dir()
        volumes_lst.extend(
            [
                f"{CONFIG.traffic_injector['cache_dir']}:{CONFIG.traffic_injector['cache_dir']}",
                f"{CONFIG.traffic_injector['dataset_dir']}:{dataset_dir}",
            ]
        )

        options = {
            "command": " ".join([str(cmd) for cmd in svc_cmd]),
            "environment": environment_lst,
            "volumes": volumes_lst,
        }

        # print(json.dumps(options, indent=2))

        self._docker_compose.update_service_options(self._svc_name, options)
        self._docker_compose.startup_service(self._svc_name, is_daemon=True)

    def run(
        self,
        host=CONFIG.enova_app["host"],
        port=CONFIG.enova_app["port"],
        **kwargs,
    ):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        if self._deploy_mode in [DeployMode.LOCAL.value]:
            self._run_local(host=host, port=port)

        elif self._deploy_mode in [DeployMode.COMPOSE.value]:
            self._run_compose(host=host, port=port)

        else:
            raise NotImplementedError()

    def _stop_compose(self):
        self._docker_compose.stop_service(self._svc_name)

    def stop(self):
        if self._deploy_mode in [DeployMode.LOCAL.value]:
            return NotImplemented

        if self._deploy_mode in [DeployMode.COMPOSE.value]:
            self._stop_compose()


class Pilot:
    def run(
        self,
        serving_host=CONFIG.serving["host"],
        serving_port=CONFIG.serving["port"],
        backend=CONFIG.serving["backend"],
        webui_host=CONFIG.webui["host"],
        webui_port=CONFIG.webui["port"],
        exporter_endpoint=CONFIG.llmo["eai_exporter_endpoint"],
        exporter_service_name=CONFIG.llmo["eai_exporter_service_name"],
        enova_app_host=CONFIG.enova_app["host"],
        enova_app_port=CONFIG.enova_app["port"],
        hf_proxy=None,
        **kwargs,
    ):
        args_helper = CliCommandArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        from enova.api.app_api import EnovaAppApi

        EnovaPurePilot().run(
            serving_host=serving_host,
            serving_port=serving_port,
            backend=backend,
            webui_host=webui_host,
            webui_port=webui_port,
            exporter_endpoint=exporter_endpoint,
            exporter_service_name=exporter_service_name,
            enova_app_host=enova_app_host,
            enova_app_port=enova_app_port,
            **kwargs,
        )

        # check enova_app heathz
        e = None
        for i in range(CONFIG.cli["default_app_healthz_check_count"]):
            try:
                healthz_res = cli_loop.run_until_complete(EnovaAppApi.healthz(params={}))
                assert healthz_res["status"] == "running"
                e = None
                break
            except Exception as h_e:
                e = h_e
                time.sleep(1)
        if e is not None:
            raise e

        app_params = {
            "instance_name": kwargs.get("name") or "enova-enode",
            "model": kwargs["model"],
        }
        enode_ret = cli_loop.run_until_complete(EnovaAppApi.enode.create(params=app_params))
        LOGGER.info(f"pilot run enode result: {enode_ret}")

    def stop(self, instance_id, service=None, *args, **kwargs):
        from enova.api.app_api import EnovaAppApi

        try:
            delete_ret = cli_loop.run_until_complete(EnovaAppApi.enode.delete(params={"instance_id": instance_id}))
            LOGGER.info(f"enode delete ret: {delete_ret}")
        except Exception as e:
            LOGGER.warning(f"enode delete error: {str(e)}")
        # magic number, stop 2 sec that pilot can delete enode asynchronously
        time.sleep(2)
        if service == "all":
            EnovaPurePilot().stop()


class EnovaCliV1:
    """
    enova cli tools

    examples:

    """

    def __init__(self, deploy_mode: DeployMode = DeployMode.COMPOSE.value):  # TODO: add deploy modes: k8s
        self.enode = Enode()
        self.mon = Monitor()
        self.webui = Webui()
        self.algo = EnovaAlgo()
        self.app = EnovaApp()
        self.injector = TrafficInjector()

        self.pilot = Pilot()


def main():
    fire.Fire(EnovaCliV1, name="enova")


if __name__ == "__main__":
    main()
