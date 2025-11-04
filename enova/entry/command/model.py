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
        from enova.monitor.metrics import MetricsReporterFactory

        checkpoint_dir = kwargs.get("checkpoint_dir")
        reporter = None
        if checkpoint_dir:
            reporter = MetricsReporterFactory.create_reporter(checkpoint_dir).start()
        train(dataset_id_list, model, output_dir, **kwargs)
        if reporter is not None:
            reporter.stop()

    def quantize(self, dataset_id_list, model, output_dir, quantization_method, **kwargs):
        from enova.train.quant import quantize

        quantize(model, dataset_id_list, output_dir, quantization_method, **kwargs)


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


@model_cli.command(name="quant", context_settings=CONFIG.cli["subcmd_context_settings"])
@click.option("--dataset_ids", type=str, help="Comma-separated list of dataset IDs", required=True)
@click.option("--model", type=str, required=True)
@click.option("--output_dir", type=str, required=True)
@click.option("--quantization_bit", type=int, required=False, default=4)
@click.option("--quantization_method", type=str, required=False, default="awq")
@pass_enova_model
@click.pass_context
def quant(
    ctx,
    enova_model,
    dataset_ids,
    model,
    output_dir,
    quantization_bit,
    quantization_method,
):
    enova_model.quantize(
        dataset_id_list=dataset_ids.split(","),
        model=model,
        output_dir=output_dir,
        quantization_method=quantization_method,
        **parse_extra_args(ctx),
    )
