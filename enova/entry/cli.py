import click

from enova.common.config import _get_pkg_version, CONFIG
from enova.entry.command.algo import algo_cli
from enova.entry.command.app import app_cli
from enova.entry.command.enode import enode_cli
from enova.entry.command.injector import injector_cli
from enova.entry.command.mon import mon_cli
from enova.entry.command.pilot import pilot_cli
from enova.entry.command.webui import webui_cli


@click.version_option(_get_pkg_version(), "--version", "-v")
@click.group(context_settings=CONFIG.cli["context_settings"])
def cli():
    """
    \b
    ███████╗███╗   ██╗ ██████╗ ██╗   ██╗ █████╗
    ██╔════╝████╗  ██║██╔═══██╗██║   ██║██╔══██╗
    █████╗  ██╔██╗ ██║██║   ██║██║   ██║███████║
    ██╔══╝  ██║╚██╗██║██║   ██║╚██╗ ██╔╝██╔══██║
    ███████╗██║ ╚████║╚██████╔╝ ╚████╔╝ ██║  ██║
    ╚══════╝╚═╝  ╚═══╝ ╚═════╝   ╚═══╝  ╚═╝  ╚═╝

    \b
    ENOVA is an open-source llm deployment, monitoring, injection and auto-scaling service.
    It provides a set of commands to deploy stable serverless serving of LLM on GPU clusters with auto-scaling.
    """
    pass


def main():
    cli.add_command(enode_cli)
    cli.add_command(app_cli)
    cli.add_command(webui_cli)
    cli.add_command(mon_cli)
    cli.add_command(algo_cli)
    cli.add_command(injector_cli)

    cli.add_command(pilot_cli)  # all in one

    cli()


if __name__ == "__main__":
    main()
