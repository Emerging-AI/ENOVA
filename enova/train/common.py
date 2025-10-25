import json
import os
from enova.common.logger import LOGGER


def setup_deepspeed_config(model, **kwargs):
    # 根据 model 配置找
    from enova.serving.backend.utils import estimate_hf_model_params_size

    need_offload = False
    estimate_result = estimate_hf_model_params_size(model)
    LOGGER.info(f"estimate_hf_model_params_size model: {model}, result: {estimate_result}")
    if estimate_result["params_size"] > 400 * 10**9:
        need_offload = True
    default_zero_stage = 2
    if estimate_result["params_size"] > 100 * 10**9:
        default_zero_stage = 3
    zero_stage = int(kwargs.pop("zero_stage", default_zero_stage))
    os.makedirs("conf", exist_ok=True)
    if zero_stage == 3:
        deepspeed_config = {
            "train_batch_size": "auto",
            "train_micro_batch_size_per_gpu": "auto",
            "gradient_accumulation_steps": "auto",
            "gradient_clipping": "auto",
            "zero_allow_untested_optimizer": True,
            "fp16": {"enabled": "auto", "loss_scale": 0, "loss_scale_window": 1000, "initial_scale_power": 16, "hysteresis": 2, "min_loss_scale": 1},
            "bf16": {"enabled": "auto"},
            "zero_optimization": {
                "stage": 3,
                "overlap_comm": False,
                "contiguous_gradients": True,
                "sub_group_size": 1e9,
                "reduce_bucket_size": "auto",
                "stage3_prefetch_bucket_size": "auto",
                "stage3_param_persistence_threshold": "auto",
                "stage3_max_live_parameters": 1e9,
                "stage3_max_reuse_distance": 1e9,
                "stage3_gather_16bit_weights_on_model_save": True,
            },
        }
        if need_offload:
            deepspeed_config["zero_optimization"].update(
                {
                    "offload_optimizer": {"device": "cpu", "pin_memory": True},
                    "offload_param": {"device": "cpu", "pin_memory": True},
                }
            )
    elif zero_stage == 2:
        deepspeed_config = {
            "train_batch_size": "auto",
            "train_micro_batch_size_per_gpu": "auto",
            "gradient_accumulation_steps": "auto",
            "gradient_clipping": "auto",
            "zero_allow_untested_optimizer": True,
            "fp16": {"enabled": "auto", "loss_scale": 0, "loss_scale_window": 1000, "initial_scale_power": 16, "hysteresis": 2, "min_loss_scale": 1},
            "bf16": {"enabled": "auto"},
            "zero_optimization": {
                "stage": 2,
                "allgather_partitions": True,
                "allgather_bucket_size": 5e8,
                "overlap_comm": False,
                "reduce_scatter": True,
                "reduce_bucket_size": 5e8,
                "contiguous_gradients": True,
                "round_robin_gradients": True,
            },
        }
    else:
        deepspeed_config = {
            "train_batch_size": "auto",
            "train_micro_batch_size_per_gpu": "auto",
            "gradient_accumulation_steps": "auto",
            "gradient_clipping": "auto",
            "zero_allow_untested_optimizer": True,
            "fp16": {"enabled": "auto", "loss_scale": 0, "loss_scale_window": 1000, "initial_scale_power": 16, "hysteresis": 2, "min_loss_scale": 1},
            "bf16": {"enabled": "auto"},
            "zero_optimization": {
                "stage": 0,
                "allgather_partitions": True,
                "allgather_bucket_size": 5e8,
                "overlap_comm": False,
                "reduce_scatter": True,
                "reduce_bucket_size": 5e8,
                "contiguous_gradients": True,
                "round_robin_gradients": True,
            },
        }

    LOGGER.info("####" * 10)
    LOGGER.info(f"deepspeed config: {json.dumps(deepspeed_config, indent=4)}")
    with open("conf/deepspeed_config.json", "w", encoding="utf-8") as f:
        json.dump(deepspeed_config, f, indent=4, ensure_ascii=False)
