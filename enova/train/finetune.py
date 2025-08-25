import sys
from enova.common.logger import LOGGER


def mock_sys_exit(*args, **kwargs):
    LOGGER.info(f"mock sys.exit called with args: {args}, kwargs: {kwargs}")


sys_exit = sys.exit
sys.exit = mock_sys_exit


import os
from typing import List
import sys
import yaml
import json
from sqlalchemy import text
from enova.api.data_api import get_datasets
from enova.database.relation.transaction.session import db_router, PostgresqlEngine, get_session
from enova.train.common import setup_deepspeed_config


def process_qa_data(row):
    """
    question, answers, selected_answer
    """

    return {
        "question": row["question"],
        "answer": row["selected_answer"],
        "history": [],
    }


DATASET_TYPE_ROW_PROCESS_MAP = {
    "qa": process_qa_data,
}


def download_dataset(dataset_id_list: List[str]):
    """ """
    dataset_info = {}
    datasets = get_datasets(dataset_id_list)
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
        dataset_filename = f"{dataset_id}.json"
        with open(f"data/{dataset_filename}", "w", encoding="utf-8") as f:
            json.dump(data_list, f, indent=4, ensure_ascii=False)
        dataset_info[dataset_id] = {"file_name": dataset_filename, "columns": {"prompt": "question", "response": "answer", "history": "history"}}

    with open("data/dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=4, ensure_ascii=False)


def setup_train_config(dataset_id_list: List[str], model, output_dir, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "trust_remote_code": True,
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
    with open("conf/finetune.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def setup_merge_lora_config(model, output_dir, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "adapter_name_or_path": "saves/lora/sft",
        "template": "qwen",
        "trust_remote_code": True,
        "export_dir": output_dir,
        "export_size": 5,
        "export_device": "cpu",
        "export_legacy_format": False,
    }
    with open("conf/merge_lora.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def train_by_llamafactory():
    """"""
    from llamafactory.cli import main

    sys.argv = ["llamafactory-cli", "train", "conf/finetune.yaml"]
    main()

    sys.argv = ["llamafactory-cli", "export", "conf/merge_lora.yaml"]
    main()


def train(dataset_id_list, model, output_dir, **kwargs):
    """ """
    os.makedirs("conf", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("saves", exist_ok=True)
    download_dataset(dataset_id_list)
    setup_deepspeed_config()
    setup_train_config(dataset_id_list, model, output_dir, **kwargs)
    setup_merge_lora_config(model, output_dir)
    train_by_llamafactory()
