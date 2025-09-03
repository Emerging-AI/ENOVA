import os
import yaml
import json
from typing import List
from datasets import Dataset
from transformers import AutoTokenizer
from llmcompressor.modifiers.awq import AWQModifier
from llmcompressor import oneshot
from sqlalchemy import text

from enova.api.data_api import get_datasets
from enova.database.relation.transaction.session import db_router, PostgresqlEngine, get_session


def process_qa_data(row):
    """
    question, answers, selected_answer
    """

    return {
        "question": row["question"],
        "answer": row["selected_answer"] or row["answers"][0],
        "history": [],
    }


DATASET_TYPE_ROW_PROCESS_MAP = {
    "qa": process_qa_data,
}


def download_dataset(dataset_id_list: List[str]) -> List:
    """ """
    dataset_filename = "quant_data.json"
    datasets = get_datasets(dataset_id_list)
    data_list = []
    if not os.path.exists(f"data/{dataset_filename}"):
        with open(f"data/{dataset_filename}", "w", encoding="utf-8") as f:
            for dataset in datasets:
                data_list = []
                dataset_id = dataset["dataset_id"]
                if dataset["dataset_storage"][0]["storage_type"] == "pgsql":
                    pg_engine = PostgresqlEngine(dataset["dataset_storage"][0]["storage_detail_config"])
                    db_router.set_custom_db_engine(dataset_id, pg_engine)
                    table_name = dataset["dataset_storage"][0]["storage_detail_config"]["table_name"]
                    with get_session(dataset_id) as session:
                        for row in session.execute(text(f'select * from "{table_name}"')):
                            row_dct = row._mapping
                            data_list.append(DATASET_TYPE_ROW_PROCESS_MAP[dataset["dataset_type"]](row_dct))

        with open(f"data/{dataset_filename}", "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)
    else:
        with open(f"data/{dataset_filename}", "r", encoding="utf-8") as f:
            data_list = json.load(f)
    ds = Dataset.from_list(data_list)
    ds = ds.shuffle()
    return ds


def setup_train_config(dataset_id_list: List[str], model, output_dir, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "trust_remote_code": True,
        "quantization_bit": 4,
        "quantization_method": "awq",
        # method
        "stage": "sft",
        "do_train": True,
        "finetuning_type": "lora",
        "lora_rank": 4,
        "lora_target": "all",
        "deepspeed": "conf/deepspeed_config.json",
        # dataset
        "dataset": ",".join(dataset_id_list),
        "template": "qwen",
        "cutoff_len": 1024,
        "max_samples": 1000,
        "overwrite_cache": True,
        "preprocessing_num_workers": 8,
        "dataloader_num_workers": 4,
        # output
        "output_dir": "saves/lora/sft",
        "logging_steps": 10,
        "save_steps": 20,
        "plot_loss": True,
        "overwrite_output_dir": True,
        "save_only_model": True,
        "report_to": "tensorboard",
        "logging_dir": "saves/tensorboard/qwen3/sft",
        # train
        "per_device_train_batch_size": 1,
        "gradient_accumulation_steps": 8,
        "learning_rate": 0.0001,
        "num_train_epochs": 1.0,
        "lr_scheduler_type": "cosine",
        "warmup_ratio": 0.1,
        "ddp_timeout": 180000000,
        "resume_from_checkpoint": None,
        "bf16": True,
    }
    base_config.update(kwargs)
    with open("conf/quant.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def quantize(model, dataset_id_list, output_dir, quantization_method="awq", **kwargs):
    """ """
    os.makedirs("conf", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("saves", exist_ok=True)
    dataset = download_dataset(dataset_id_list)

    tokenizer = AutoTokenizer.from_pretrained(model)

    def preprocess(msg):
        return {
            "text": tokenizer.apply_chat_template(
                [{"role": "user", "content": msg["question"]}, {"role": "assistant", "content": msg["answer"]}],
                tokenize=False,
                add_generation_prompt=False,
            )
        }

    dataset = dataset.map(preprocess)

    recipe = [
        AWQModifier(
            ignore=["lm_head", "re:.*mlp.gate$", "re:.*mlp.shared_expert_gate$"],
            scheme="W4A16",
            targets=["Linear"],
        ),
    ]

    # Apply algorithms.
    oneshot(
        model=model,
        output_dir=output_dir,
        dataset=dataset,
        recipe=recipe,
        max_seq_length=kwargs.get("max_seq_length", 512),
        num_calibration_samples=kwargs.get("num_calibration_samples", min(512, dataset.num_rows)),
    )
