import sys
import click

from enova.common.cli_helper import ArgumentHelper
from enova.common.config import CONFIG


class EnovaAlgo:
    # TODO: support run compose
    def run(self):
        args_helper = ArgumentHelper(self, sys._getframe())
        CONFIG.update_config(args_helper.args_map)

        import uvicorn

        from enova.algo.server import get_algo_api_server

        api_server = get_algo_api_server()
        uvicorn.run(api_server.app, host=CONFIG.enova_algo["host"], port=CONFIG.enova_algo["port"])


pass_enova_algo = click.make_pass_decorator(EnovaAlgo)


@click.group(name="algo")
@click.pass_context
def algo_cli(ctx):
    """
    Run the autoscaling service.
    """
    ctx.obj = EnovaAlgo()


@algo_cli.command(name="run", context_settings=CONFIG.cli["subcmd_context_settings"])
@pass_enova_algo
@click.pass_context
def mon_run(ctx, enova_algo: EnovaAlgo):
    enova_algo.run()


@algo_cli.command(name="stop")
@pass_enova_algo
@click.pass_context
def mon_stop(ctx, enova_algo: EnovaAlgo):
    enova_algo.stop()
