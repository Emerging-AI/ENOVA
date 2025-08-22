import json
import os


def setup_deepspeed_config():
    os.makedirs("conf", exist_ok=True)
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
    with open("conf/deepspeed_config.json", "w", encoding="utf-8") as f:
        json.dump(deepspeed_config, f, indent=4, ensure_ascii=False)