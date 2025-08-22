import re
import sys
import click

from enova.common.cli_helper import ArgumentHelper, parse_extra_args
from enova.common.config import CONFIG


class EnovaModel:
    def train(
        self,
        dataset_id_list: str,
        model: str,
        output_dir: str,
        **kwargs,
    ):
        from enova.train.finetune import train

        train(dataset_id_list, model, output_dir, **kwargs)


@click.group(name="model")
@click.pass_context
def model_cli(ctx):
    """
    Deploy the target LLM and launch the LLM API service.
    """
    ctx.obj = EnovaModel()


pass_enova_model = click.make_pass_decorator(EnovaModel)


@model_cli.command(name="train", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--dataset_ids", type=str, help="Comma-separated list of dataset IDs", required=True)
@click.option("--model", type=str, required=True)
@click.option("--output_dir", type=str, required=True)
@pass_enova_model
@click.pass_context
def train(
    ctx,
    enova_model,
    dataset_ids,
    model,
    output_dir,
):
    enova_model.train(
        dataset_id_list=dataset_ids.split(","),
        model=model,
        output_dir=output_dir,
        **parse_extra_args(ctx),
    )
