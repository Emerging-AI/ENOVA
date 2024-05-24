import os
import subprocess
import sys
import click

from enova.common.cli_helper import ArgumentHelper, parse_extra_args
from enova.common.config import CONFIG
from enova.common.utils import get_enova_path


class Webui:
    def __init__(self):
        self.streamlit_process = None

    def start(self, serving_host, serving_port, host, port):
        args_helper = ArgumentHelper(self, sys._getframe())
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
        daemon=CONFIG.webui["daemon"],
        **kwargs,
    ):
        """"""
        self.start(serving_host, serving_port, host, port)
        if daemon:
            self.streamlit_process.wait()

    def stop(self):
        self.streamlit_process.terminate()
        self.streamlit_process.wait()


pass_enova_webui = click.make_pass_decorator(Webui)


@click.group(name="webui")
@click.pass_context
def webui_cli(ctx):
    """
    Build agent at this page based on the launched LLM API service.
    """
    pass


@webui_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--serving-host", type=str, default=CONFIG.serving["host"])
@click.option("--serving-port", type=int, default=CONFIG.serving["port"])
@click.option("--host", type=str, default=CONFIG.webui["host"])
@click.option("--port", type=int, default=CONFIG.webui["port"])
@click.option("--daemon", type=bool, default=CONFIG.webui["daemon"])
@pass_enova_webui
@click.pass_context
def webui_run(
    ctx,
    enova_webui: Webui,
    serving_host,
    serving_port,
    host,
    port,
    daemon,
):
    enova_webui.run(
        serving_host=serving_host,
        serving_port=serving_port,
        host=host,
        port=port,
        daemon=daemon,
        **parse_extra_args(ctx),
    )
    pass


@webui_cli.command(
    name="stop",
    context_settings=dict(help_option_names=["-h", "--help"], ignore_unknown_options=True, allow_extra_args=True),
)
@pass_enova_webui
@click.pass_context
def webui_stop(ctx, enova_webui: Webui):
    enova_webui.stop()
