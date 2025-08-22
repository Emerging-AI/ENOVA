import os
import sys
import yaml

from enova.train.common import setup_deepspeed_config
from enova.train.serializer import QuantizationConfig


def setup_quant_config(model, output_dir, **kwargs):
    base_config = QuantizationConfig(
        model_path=model,
        export_dir=output_dir,
    )
    base_config.update(kwargs)
    with open("conf/quant.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def export_model_by_llamafactory():
    """"""
    from llamafactory.cli import main

    sys.argv = ["llamafactory-cli", "export", "conf/quant.yaml"]
    main()


def quantize(model, output_dir, **kwargs):
    """ """
    os.makedirs("conf", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("saves", exist_ok=True)
    setup_deepspeed_config()
    setup_quant_config(model, output_dir, **kwargs)
    export_model_by_llamafactory()
