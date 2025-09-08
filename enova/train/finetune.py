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
import numpy as np
import pandas as pd
import shutil
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
        "answer": row["selected_answer"] or row["answers"][0],
        "history": [],
    }


DATASET_TYPE_ROW_PROCESS_MAP = {
    "qa": process_qa_data,
}


def split_dataframe_by_ratio_numpy_index(df, split_ratio=0.8, random_state=None):
    """
    利用 NumPy 生成随机索引将 DataFrame 切分为训练集和测试集。

    Args:
        df (pd.DataFrame): 待切分的原始 DataFrame。
        split_ratio (float): 训练集所占的比例 (0 到 1 之间)。
        random_state (int, optional): 随机种子，用于重现性。

    Returns:
        tuple: (train_df, test_df)，包含训练集 DataFrame 和测试集 DataFrame。
    """
    if not (0 < split_ratio < 1):
        raise ValueError("split_ratio 必须在 0 到 1 之间。")

    num_rows = len(df)
    train_size = int(num_rows * split_ratio)

    # 创建一个包含所有索引的数组
    indices = np.arange(num_rows)

    # # 设置随机种子
    # if random_state is not None:
    #     np.random.seed(random_state)

    # # 随机打乱索引
    # np.random.shuffle(indices)

    # 根据比例划分索引
    train_indices = indices[:train_size]
    test_indices = indices[train_size:]

    # 使用 .iloc 按照索引切分 DataFrame
    train_df = df.iloc[train_indices]
    test_df = df.iloc[test_indices]

    return train_df, test_df


def download_dataset(dataset_id_list: List[str], split_ratio=0.1):
    """"""
    dataset_info = {}
    datasets = get_datasets(dataset_id_list)
    train_dataset_id_list = []
    eval_dataset_id_list = []
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
        train_dataset_filename = f"{dataset_id}_train.json"
        eval_dataset_filename = f"{dataset_id}_eval.json"

        pdf = pd.DataFrame(data_list)
        if split_ratio > 0:
            train_df, eval_df = split_dataframe_by_ratio_numpy_index(pdf, split_ratio)
            train_df.to_json(f"data/{train_dataset_filename}", orient="records", lines=False, force_ascii=False, indent=4)
            eval_df.to_json(f"data/{eval_dataset_filename}", orient="records", lines=False, force_ascii=False, indent=4)
            # with open(f"data/{train_dataset_filename}", "w", encoding="utf-8") as f:
            #     json.dump(data_list, f, indent=4, ensure_ascii=False)
            train_dataset_id = f"{dataset_id}_train"
            eval_dataset_id = f"{dataset_id}_eval"
            train_dataset_id_list.append(train_dataset_id)
            eval_dataset_id_list.append(eval_dataset_id)
            dataset_info[train_dataset_id] = {
                "file_name": train_dataset_filename,
                "columns": {"prompt": "question", "response": "answer", "history": "history"},
            }
            dataset_info[eval_dataset_id] = {
                "file_name": eval_dataset_filename,
                "columns": {"prompt": "question", "response": "answer", "history": "history"},
            }
        else:
            pdf.to_json(f"data/{train_dataset_filename}", orient="records", lines=False, force_ascii=False, indent=4)
            train_dataset_id_list.append(dataset_id)
            dataset_info[dataset_id] = {
                "file_name": train_dataset_filename,
                "columns": {"prompt": "question", "response": "answer", "history": "history"},
            }

    with open("data/dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=4, ensure_ascii=False)
    return train_dataset_id_list, eval_dataset_id_list


def setup_train_config(dataset_id_list: List[str], eval_dataset_id_list: List[str], model, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "trust_remote_code": True,
        # method
        "stage": "sft",
        "do_train": True,
        "finetuning_type": "lora",
        "lora_rank": 8,
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
        "fp16": False,
    }

    if len(eval_dataset_id_list) > 0:
        base_config.update(
            {
                ### dataset
                "eval_dataset": ",".join(dataset_id_list),
                "template": "qwen",
                "overwrite_cache": True,
                "preprocessing_num_workers": 8,
                ### output
                "overwrite_output_dir": True,
                ### eval
                "per_device_eval_batch_size": 1,
                "predict_with_generate": True,
                "do_predict": True,
            }
        )
    for k, v in kwargs.items():
        if k in base_config:
            base_config[k] = v
    os.makedirs(base_config["logging_dir"], exist_ok=True)
    os.makedirs(base_config["output_dir"], exist_ok=True)
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


def setup_eval_config(dataset_id_list: List[str], model, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "adapter_name_or_path": "saves/lora/sft",
        ### method
        "stage": "sft",
        "do_predict": True,
        "finetuning_type": "lora",
        ### dataset
        "eval_dataset": ",".join(dataset_id_list),
        "template": "qwen",
        "cutoff_len": 2048,
        "max_samples": 50,
        "overwrite_cache": True,
        "preprocessing_num_workers": 8,
        ### output
        "output_dir": "saves/eval/qwen3/sft",
        "overwrite_output_dir": True,
        ### eval
        "per_device_eval_batch_size": 8,
        "predict_with_generate": True,
        "ddp_timeout": 180000000,
    }
    for k, v in kwargs.items():
        if k in base_config:
            base_config[k] = v
    os.makedirs(base_config["output_dir"], exist_ok=True)
    with open("conf/eval.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def train_by_llamafactory(output_dir, eval_result_path):
    """"""
    from llamafactory.cli import main

    os.environ["FORCE_TORCHRUN"] = "1"

    sys.argv = ["llamafactory-cli", "train", "conf/finetune.yaml"]
    main()

    LOGGER.info("**** start copying results ****")
    for filename in ["predict_results.json", "generated_predictions.jsonl", "all_results.json"]:
        shutil.copyfile(os.path.join(output_dir, filename), os.path.join(eval_result_path, filename))

    sys.argv = ["llamafactory-cli", "export", "conf/merge_lora.yaml"]
    main()


def train(dataset_id_list, model, output_dir, **kwargs):
    """ """
    os.makedirs("conf", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("saves", exist_ok=True)
    train_dataset_id_list, eval_dataset_id_list = download_dataset(dataset_id_list, kwargs.get("split_ratio", 0))
    setup_deepspeed_config(**kwargs)
    # setup_eval_config(eval_dataset_id_list, model, **kwargs)
    setup_train_config(train_dataset_id_list, eval_dataset_id_list, model, **kwargs)
    setup_merge_lora_config(model, output_dir)
    eval_result_path = kwargs.get("eval_result_path", "saves/eval/")
    train_by_llamafactory(eval_result_path)
