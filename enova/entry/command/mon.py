import subprocess
import sys
import click

from enova.common.cli_helper import ArgumentHelper, DockerComposeHeler
from enova.common.config import CONFIG
from enova.common.logger import LOGGER


class EnovaMonitor:
    def __init__(self) -> None:
        self.docker_services = [
            "dcgm-exporter",
            "grafana",
            "otel-collector",
            "prometheus",
            "tempo",
            "enova-escaler",
            "enova-algo",
        ]  # start up by order
        self._docker_compose = DockerComposeHeler()

    def _run_by_compose(self):
        for service in self.docker_services:
            options = {}
            self._docker_compose.update_service_options(service, options)
            self._docker_compose.startup_service(service, is_daemon=True)

    def run(self, **kwargs):
        args_helper = ArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        self._run_by_compose()

    def _stop_by_compose(self):
        pass

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


pass_enova_monitor = click.make_pass_decorator(EnovaMonitor)


@click.group(name="mon")
@click.pass_context
def mon_cli(ctx):
    """
    Run the monitors of LLM server
    """
    ctx.obj = EnovaMonitor()


@mon_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@pass_enova_monitor
@click.pass_context
def mon_run(ctx, enova_monitor: EnovaMonitor):
    enova_monitor.run()


@mon_cli.command(name="stop")
@pass_enova_monitor
@click.pass_context
def mon_stop(ctx, enova_monitor: EnovaMonitor):
    enova_monitor.stop()
