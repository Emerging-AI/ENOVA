import dataclasses
from enum import Enum
import inspect
import json
import os
import subprocess
from types import FrameType
from typing import Any, ClassVar

import click
import yaml
from enova.common.config import CONFIG
from enova.common.logger import LOGGER
from enova.common.utils import camel_to_snake, get_enova_path

import ast


def args_type_eval(v):
    try:
        return ast.literal_eval(v)
    except Exception:  # maybe it's a string, eval failed, return anyway
        return v


def parse_extra_args(ctx: click.Context) -> dict:
    """
    Parse extra arguments passed via ctx.args and return them as a dictionary.
    Supports both --key=value and --key value formats.
    """
    extra_args = {}
    args = ctx.args
    i = 0

    while i < len(args):
        if args[i].startswith("--"):
            if "=" in args[i]:
                # Handle --key=value format
                key, value = args[i][2:].split("=", 1)
                key.replace("-", "_")
                extra_args[key] = args_type_eval(value)
                i += 1
            else:
                # Handle --key value format
                key = args[i][2:]
                key.replace("-", "_")
                if i + 1 < len(args) and not args[i + 1].startswith("--"):
                    value = args[i + 1]
                    extra_args[key] = args_type_eval(value)
                    i += 2
                else:
                    click.echo(f"Warning: Missing value for argument '{args[i]}'", err=True)
                    i += 1
        else:
            click.echo(f"Warning: Ignoring invalid argument '{args[i]}'", err=True)
            i += 1

    return extra_args


@dataclasses.dataclass
class ArgumentHelper:
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


class EnumType(click.Choice):
    def __init__(self, enum: Enum, case_sensitive=False):
        self.__enum = enum
        super().__init__(choices=[item.value for item in enum], case_sensitive=case_sensitive)

    def convert(self, value, param, ctx):
        if value is None or isinstance(value, Enum):
            return value

        converted_str = super().convert(value, param, ctx)
        return self.__enum(converted_str)
