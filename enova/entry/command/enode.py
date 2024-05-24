import sys
import click

from enova.common.cli_helper import ArgumentHelper, parse_extra_args
from enova.common.config import CONFIG
from enova.common.constant import ServingBackend
from enova.enode.hf import HFText2TextEnode
from enova.entry.command.webui import Webui
from enova.serving.apiserver import EApiServer


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


class EnovaEnode:
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
        args_helper = ArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        from enova.llmo import start as llmo_start

        CONFIG.update_config({backend: kwargs})
        # CONFIG.print_config()
        llmo_start(otlp_exporter_endpoint=exporter_endpoint, service_name=exporter_service_name)
        if include_webui:
            Webui().run(daemon=False)
        EnodeHandler(host, port, model, backend).start()


pass_enova_enode = click.make_pass_decorator(EnovaEnode)


@click.group(name="enode")
@click.pass_context
def enode_cli(ctx):
    """
    Deploy the target LLM and launch the LLM API service.
    """
    ctx.obj = EnovaEnode()


@enode_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--model", type=str)
@click.option("--host", type=str, default=CONFIG.serving["host"])
@click.option("--port", type=int, default=CONFIG.serving["port"])
@click.option("--backend", type=str, default=CONFIG.serving["backend"])
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
@click.option("--include-webui", "--include_webui", "include_webui", type=bool, default=True)
@click.option("--hf-proxy", "--hf_proxy", "hf_proxy", type=str, default=None)
@pass_enova_enode
@click.pass_context
def enode_run(
    ctx,
    enova_enode,
    model,
    host,
    port,
    backend,
    exporter_endpoint,
    exporter_service_name,
    include_webui,
    hf_proxy,
):
    enova_enode.run(
        model=model,
        host=host,
        port=port,
        backend=backend,
        exporter_endpoint=exporter_endpoint,
        exporter_service_name=exporter_service_name,
        include_webui=include_webui,
        hf_proxy=hf_proxy,
        **parse_extra_args(ctx),
    )
