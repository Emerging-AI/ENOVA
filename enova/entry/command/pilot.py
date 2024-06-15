import asyncio
import subprocess
import sys
import time
from functools import cached_property
import click

from enova.common.cli_helper import ArgumentHelper, DockerComposeHeler, parse_extra_args
from enova.common.config import CONFIG
from enova.common.constant import DeployMode
from enova.common.logger import LOGGER
from enova.entry.command.app import EnovaApp
from enova.entry.command.mon import EnovaMonitor

cli_new_loop = asyncio.new_event_loop()
asyncio.set_event_loop(cli_new_loop)
cli_loop = asyncio.get_event_loop()


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
        args_helper = ArgumentHelper(self, sys._getframe())
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
        args_helper = ArgumentHelper(self, sys._getframe())
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


class EnovaService:
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
        return EnovaMonitor()

    def status(self):
        return self.mon.status()

    def run(self, failed_with_stop=False, *args, **kwars):
        restart_service = kwars.pop("restart_service", None)
        args_helper = ArgumentHelper(self, sys._getframe())
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
            self.enova_app.run(host=kwars["enova_app_host"], port=int(kwars["enova_app_port"]), restart=restart_service == "enova_app")
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


class EnovaPilot:
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
        restart_service=None,
        **kwargs,
    ):
        """
        pilot run

        :param serving_host: llm serving host

        """
        args_helper = ArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        from enova.api.app_api import EnovaAppApi

        EnovaService().run(
            serving_host=serving_host,
            serving_port=serving_port,
            backend=backend,
            webui_host=webui_host,
            webui_port=webui_port,
            exporter_endpoint=exporter_endpoint,
            exporter_service_name=exporter_service_name,
            enova_app_host=enova_app_host,
            enova_app_port=enova_app_port,
            restart_service=restart_service,
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
            "backend_config": kwargs,
        }
        enode_ret = cli_loop.run_until_complete(EnovaAppApi.enode.create(params=app_params))

        LOGGER.info(f"pilot create enode result: {enode_ret}")

        time.sleep(3)

        # TODO: handle enova-escaler's errors
        instance_id = enode_ret["instance_id"]
        get_params = {"instance_id": instance_id}
        enode_info = cli_loop.run_until_complete(EnovaAppApi.enode.get(params=get_params))
        LOGGER.info(f"enode_info: {enode_info}")

        # TODO:
        container_infos = enode_info.get("extra", {}).get("get_deploy_ret", {}).get("ret", {}).get("result", {}).get("container_infos")
        LOGGER.info(f"container_infos: {container_infos}")

        if not container_infos:
            LOGGER.error(f"container deployed by '{instance_id}' is not exised")
            return

        container_info = container_infos[0]

        container_id = container_info.get("ContainerId")
        if not container_id:
            LOGGER.error(f"container info of instance '{instance_id}' get failed ")
            return

        LOGGER.info(f"enode container id: {container_id}")

        # show logs of enode startup, enode not run in compose
        command = ["docker", "logs", "-f", container_id]
        cmd_str = " ".join(command)
        LOGGER.debug("Command: {}".format(cmd_str))
        subprocess.Popen(command)

    def stop(self, instance_id=None, service=None, *args, **kwargs):
        from enova.api.app_api import EnovaAppApi

        def delete_enode(enode_id):
            try:
                delete_ret = cli_loop.run_until_complete(EnovaAppApi.enode.delete(params={"instance_id": enode_id}))
                LOGGER.info(f"enode delete ret: {delete_ret}")
            except Exception as e:
                LOGGER.warning(f"enode delete error: {str(e)}")

        if instance_id in ["all", None]:
            enode_list = cli_loop.run_until_complete(EnovaAppApi.enode.list(params={}))["data"]
            for enode_info in enode_list:
                delete_enode(enode_info["instance_id"])
        else:
            delete_enode(instance_id)

        # magic number, stop 2 sec that pilot can delete enode asynchronously
        time.sleep(2)
        if service == "all":
            EnovaService().stop()


pass_enova_pilot = click.make_pass_decorator(EnovaPilot)


@click.group(name="pilot")
@click.pass_context
def pilot_cli(ctx):
    """
    Start an all-in-one LLM server with deployment, monitoring, injection and auto-scaling service.
    """
    ctx.obj = EnovaPilot()


@pilot_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--serving-host", "--serving_host", "serving_host", type=str, default=CONFIG.serving["host"])
@click.option("--serving-port", "--serving_port", "serving_port", type=int, default=CONFIG.serving["port"])
@click.option("--backend", type=str, default=CONFIG.serving["backend"])
@click.option("--webui-host", "--webui_host", "webui_host", type=str, default=CONFIG.webui["host"])
@click.option("--webui-port", "--webui_port", "webui_port", type=int, default=CONFIG.webui["port"])
@click.option(
    "--exporter-endpoint",
    "--exporter_endpoint",
    "exporter_endpoint",
    type=str,
    default=CONFIG.llmo["eai_exporter_endpoint"],
)
@click.option(
    "--exporter-service-name",
    "--exporter_service_name",
    "exporter_service_name",
    type=str,
    default=CONFIG.llmo["eai_exporter_service_name"],
)
@click.option("--enova-app-host", "--enova_app_host", "enova_app_host", type=str, default=CONFIG.enova_app["host"])
@click.option("--enova-app-port", "--enova_app_port", "enova_app_port", type=int, default=CONFIG.enova_app["port"])
@click.option("--hf-proxy", "--hf_proxy", "hf_proxy", type=str, default=None)
@click.option("--restart-service", "--restart_service", "restart_service", type=str, default=None)
@pass_enova_pilot
@click.pass_context
def pilot_run(
    ctx,
    enova_pilot: EnovaPilot,
    serving_host,
    serving_port,
    backend,
    webui_host,
    webui_port,
    exporter_endpoint,
    exporter_service_name,
    enova_app_host,
    enova_app_port,
    hf_proxy,
    restart_service=None,
):
    enova_pilot.run(
        serving_host=serving_host,
        serving_port=serving_port,
        backend=backend,
        webui_host=webui_host,
        webui_port=webui_port,
        exporter_endpoint=exporter_endpoint,
        exporter_service_name=exporter_service_name,
        enova_app_host=enova_app_host,
        enova_app_port=enova_app_port,
        hf_proxy=hf_proxy,
        restart_service=restart_service,
        **parse_extra_args(ctx),
    )


@pilot_cli.command(name="stop")
@click.option("--instance-id", "--instance_id", "instance_id", type=str)
@click.option("--service", "--service", "service", type=str)
@pass_enova_pilot
@click.pass_context
def pilot_stop(ctx, enova_pilot: EnovaPilot, instance_id, service=None):
    enova_pilot.stop(instance_id, service, **parse_extra_args(ctx))
