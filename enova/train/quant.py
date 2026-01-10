import os
import shutil
import json
import stat
import argparse
import types
from functools import partial
from typing import List
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from llmcompressor.modifiers.awq import AWQModifier
from llmcompressor import oneshot
from sqlalchemy import text
import torch
from enova.common.logger import LOGGER
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


def process_sft_text_generation_data(row, system_prompt=None):
    """
    prompt, response
    """
    return {
        "messages": row["messages"],
    }


DATASET_TYPE_ROW_PROCESS_MAP = {
    "qa": process_qa_data,
    "sft_text_generation": process_sft_text_generation_data,
}


def qa_preprocess(msg, tokenizer):
    return {
        "text": tokenizer.apply_chat_template(
            [{"role": "user", "content": msg["question"]}, {"role": "assistant", "content": msg["answer"]}],
            tokenize=False,
            add_generation_prompt=False,
        )
    }


def sft_text_generation_preprocess(msg, tokenizer):
    return {
        "text": tokenizer.apply_chat_template(
            msg["messages"],
            tokenize=False,
            add_generation_prompt=False,
        )
    }


DATASET_TYPE_HF_DATASET_PROCESS_MAP = {
    "qa": qa_preprocess,
    "sft_text_generation": sft_text_generation_preprocess,
}


def download_dataset(dataset_id_list: List[str]) -> List:
    """ """
    dataset_filename = "quant_data.json"
    datasets = get_datasets(dataset_id_list)
    LOGGER.info(f"{datasets=}")
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


def json_safe_dump(obj, path, indent=None, extensions="json", check_user_stat=True):
    write_path = path
    default_mode = stat.S_IWUSR | stat.S_IRUSR
    with os.fdopen(os.open(write_path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, mode=default_mode), "w") as json_file:
        json.dump(obj, json_file, indent=indent)


def json_safe_load(path, extensions="json"):
    with open(path) as json_file:
        raw_dict = json.load(json_file)
    return raw_dict


def cmd_bool(cmd_arg):
    if cmd_arg == "True":
        return True
    elif cmd_arg == "False":
        return False
    raise ValueError(f"{cmd_arg} should be True or False")


def parse_tokenizer_args(input_str, default=None):
    default = {} if default is None else default
    try:
        args_dict = json.loads(input_str)
        if not isinstance(args_dict, dict):
            raise ValueError("Parsed JSON must be a dictionary")
        return args_dict
    except (json.JSONDecodeError, TypeError, AttributeError) as e:
        if not isinstance(default, dict):
            raise ValueError("Default value must be a dictionary") from e
        return default


class SafeGenerator:
    def __init__(self):
        pass

    @staticmethod
    def get_config_from_pretrained(model_path, **kwargs):
        try:
            config = AutoConfig.from_pretrained(model_path, local_files_only=True, **kwargs)
        except EnvironmentError as env_err:
            raise EnvironmentError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {env_err}"
            ) from env_err
        except Exception as err:
            raise ValueError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {err}"
            ) from err
        return config

    @staticmethod
    def get_model_from_pretrained(model_path, **kwargs):
        try:
            model = AutoModelForCausalLM.from_pretrained(model_path, local_files_only=True, **kwargs)
        except EnvironmentError as env_err:
            raise EnvironmentError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {env_err}"
            ) from env_err
        except Exception as err:
            raise ValueError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {err}"
            ) from err
        return model

    @staticmethod
    def get_tokenizer_from_pretrained(model_path, **kwargs):
        try:
            tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True, **kwargs)
        except EnvironmentError as env_err:
            raise EnvironmentError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {env_err}"
            ) from env_err
        except Exception as err:
            raise ValueError(
                f"Get model from pretrained failed, please check model weights files in the model path. "
                f"If the file exists, make sure the folder's owner has execute permission."
                f"Original error: {err}"
            ) from err
        return tokenizer

    @staticmethod
    def copy_tokenizer_files(model_dir, dest_dir):
        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir, mode=0o750, exist_ok=True)
        filenames = os.listdir(model_dir)
        max_file_num = 1024
        if len(filenames) > max_file_num:
            raise argparse.ArgumentTypeError(f"The file num in dir is {len(filenames)}, " f"which exceeds the limit {max_file_num}.")
        for filename in filenames:
            need_move = False
            file_names = ["tokenizer", "tokenization", "special_token_map", "generation", "configuration", "tiktoken"]
            for f in file_names:
                if f in filename:
                    need_move = True
                    break
            if need_move:
                src_filepath = os.path.join(model_dir, filename)
                dest_filepath = os.path.join(dest_dir, filename)
                shutil.copyfile(src_filepath, dest_filepath)
                os.chmod(dest_filepath, int("600", 8))

    @staticmethod
    def modify_config(model_dir, dest_dir, torch_dtype, quantize_type, args=None):
        src_config_filepath = os.path.join(model_dir, "config.json")
        data = json_safe_load(src_config_filepath)

        if args.mindie_format:
            dest_quant_description_filepath = os.path.join(dest_dir, f"quant_model_description_{quantize_type.lower()}.json")
        else:
            dest_quant_description_filepath = os.path.join(dest_dir, f"quant_model_description.json")
        if not os.path.exists(dest_quant_description_filepath):
            with open(dest_quant_description_filepath, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=4, ensure_ascii=False)
        quant_description_data = json_safe_load(dest_quant_description_filepath)

        data["torch_dtype"] = str(torch_dtype).split(".")[1]
        if args.mindie_format:
            data["quantize"] = quantize_type
        quantization_config = {
            # 当is_lowbit为True，open_outlier为False时，group_size生效
            "group_size": args.group_size if args.is_lowbit and not args.open_outlier else 0,
            "kv_quant_type": "C8" if args.use_kvcache_quant else None,
            "fa_quant_type": "FAQuant" if args.use_fa_quant else None,
            "w_bit": args.w_bit,
            "a_bit": args.a_bit,
            "dev_type": args.device_type,
            "fraction": args.fraction,
            "act_method": args.act_method,
            "co_sparse": args.co_sparse,
            "anti_method": args.anti_method,
            "disable_level": args.disable_level,
            "do_smooth": args.do_smooth,
            "use_sigma": args.use_sigma,
            "sigma_factor": args.sigma_factor,
            "is_lowbit": args.is_lowbit,
            "mm_tensor": False,
            "w_sym": args.w_sym,
            "open_outlier": args.open_outlier,
            "is_dynamic": args.is_dynamic,
        }
        if hasattr(args, "pdmix") and args.pdmix:
            quantization_config.update({"pdmix": args.pdmix})
        if args.use_reduce_quant:
            quantization_config.update({"reduce_quant_type": "per_channel"})
        quant_description_data.update(quantization_config)
        data["quantization_config"] = quantization_config
        LOGGER.info(f"modified config.json: {data}, dest_dir: {dest_dir}")
        dest_config_filepath = os.path.join(dest_dir, "config.json")
        json_safe_dump(data, dest_config_filepath, 4)

    @staticmethod
    def load_jsonl(dataset_path, key_name="inputs_pretokenized"):
        dataset = []
        if dataset_path == "humaneval_x.jsonl":
            key_name = "prompt"
        with os.fdopen(os.open(dataset_path, os.O_RDONLY, 0o600), "r", encoding="utf-8") as file:
            lines = file.readlines()
            for line in lines:
                data = json.loads(line)
                text = data.get(key_name, line)
                dataset.append(text)
        return dataset


def quantize_by_msmodelslim(model, dataset_id_list, output_dir, quantization_method="awq", **kwargs):
    import sys
    from msmodelslim.infra import practice_manager

    def mock_confirm_to_continue(*args, **kwargs):
        LOGGER.warning("Auto confirm to continue.")

    practice_manager.confirm_to_continue = mock_confirm_to_continue
    from msmodelslim.cli.__main__ import main

    model_type = kwargs.get("model_type")
    support_model_types = [
        "Qwen3-8B",
        "Qwen3-32B",
        "Qwen3-14B",
        "Qwen-QwQ-32B",
        "Qwen2.5-Coder-7B-Instruct",
        "Qwen2.5-72B-Instruct",
        "Qwen2.5-32B-Instruct",
        "Qwen2.5-7B-Instruct",
    ]
    if model_type not in support_model_types:
        raise ValueError(f"Only {', '.join(support_model_types)} are supported.")
    sys.argv = [
        "msmodelslim",
        "quant",
        "--model_path",
        model,
        "--save_path",
        output_dir,
        "--device",
        "npu",
        "--model_type",
        model_type,
        "--quant_type",
        "w8a8",
        "--trust_remote_code",
        "True",
    ]
    main()

    def copy_tokenizer_files(model_dir, dest_dir):
        filenames = os.listdir(model_dir)
        max_file_num = 1024
        if len(filenames) > max_file_num:
            raise argparse.ArgumentTypeError(f"The file num in dir is {len(filenames)}, " f"which exceeds the limit {max_file_num}.")
        for filename in filenames:
            need_move = False
            file_names = ["chat_template.jinja"]
            for f in file_names:
                if f in filename:
                    need_move = True
                    break
            if need_move:
                src_filepath = os.path.join(model_dir, filename)
                dest_filepath = os.path.join(dest_dir, filename)
                shutil.copyfile(src_filepath, dest_filepath)
                os.chmod(dest_filepath, int("600", 8))

    LOGGER.info("Copy tokenizer files to output_dir.")
    copy_tokenizer_files(model, output_dir)


def quantize_by_llmcompressor(model, dataset_id_list, output_dir, quantization_method="awq", **kwargs):
    """"""
    dataset = download_dataset(dataset_id_list)

    tokenizer = AutoTokenizer.from_pretrained(model)

    base_preprocess = DATASET_TYPE_HF_DATASET_PROCESS_MAP[dataset_type]

    dataset = dataset.map(partial(base_preprocess, tokenizer=tokenizer))

    recipe = [
        AWQModifier(ignore=["lm_head"], scheme="W4A16_ASYM", targets=["Linear"]),
    ]

    # Apply algorithms.
    oneshot(
        model=model,
        output_dir=output_dir,
        dataset=dataset,
        recipe=recipe,
        num_calibration_samples=kwargs.get("num_calibration_samples", min(128, dataset.num_rows)),
    )


def quantize(model, dataset_id_list, output_dir, quantization_method="awq", **kwargs):
    """ """
    os.makedirs("conf", exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("saves", exist_ok=True)
    if hasattr(torch, "npu") and torch.npu.is_available():
        quantize_by_msmodelslim(model, dataset_id_list, output_dir, quantization_method=quantization_method, **kwargs)
    else:
        quantize_by_llmcompressor(model, dataset_id_list, output_dir, quantization_method=quantization_method, **kwargs)
    with open(os.path.join(output_dir, "quantization_done"), "w", encoding="utf-8") as f:
        f.write("quantization_done")
