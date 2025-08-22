import re
import sys
import click

from enova.common.cli_helper import ArgumentHelper, parse_extra_args
from enova.common.config import CONFIG


class EnovaTrain:
    def run(
        self,
        dataset_id_list: str,
        model: str,
        output_dir: str,
        **kwargs,
    ):
        from enova.train.finetune import train

        train(dataset_id_list, model, output_dir, **kwargs)


@click.command(name="train", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--dataset_ids", type=str, help="Comma-separated list of dataset IDs", required=True)
@click.option("--model", type=str, required=True)
@click.option("--output_dir", type=str, required=True)
@click.pass_context
def train_cli(
    ctx,
    dataset_ids,
    model,
    output_dir,
):
    EnovaTrain().run(
        dataset_id_list=dataset_ids.split(","),
        model=model,
        output_dir=output_dir,
        **parse_extra_args(ctx),
    )
