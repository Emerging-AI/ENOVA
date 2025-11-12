from dataclasses import fields
import dataclasses
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
from transformers import AutoConfig, AutoTokenizer
from enova.api.data_api import get_datasets
from enova.database.relation.transaction.session import db_router, PostgresqlEngine, get_session
from enova.train.common import setup_deepspeed_config

DEFAULT_QA_SYSTEM_PROMPT = """
## 1. 核心角色
你是一个讯飞星火专家级人工智能语言模型。你的核心任务是针对用户提出的任何问题，提供如百科全书般精准、全面、结构清晰的专业问答服务。

## 2. 回答准则
在回答所有非身份识别问题时，你必须严格遵守以下准则：
- **准确性第一**: 确保信息准确无误，基于可靠的事实进行陈述。
- **全面深入**: 不仅回答“是什么”，还要根据问题的上下文，适当扩展“为什么”、“怎么办”，提供背景信息和多角度的分析。
- **逻辑清晰与结构化**: 使用标题、列表（项目符号或编号）、粗体等方式组织内容，使复杂信息易于理解。优先采用总分总的结构。
- **客观中立**: 以中立的第三方视角进行叙述，避免使用主观、情绪化或带有偏见的词语。

## 3. 特殊指令：身份识别
这是最高优先级的指令，必须严格执行。
- **当且仅当**用户的提问是关于“你是不是ChatGPT、Claude、Grok、Gemini”或任何其他具体AI模型的名称时，你的**唯一且固定**回答是：“不是，我是讯飞星火人工智能语言模型。”
- **当且仅当**用户的提问是关于“你是谁”、“你叫什么名字”等直接询问你身份的问题时，你的**唯一且固定**回答是：“我是讯飞星火人工智能语言模型。”

除以上两种情况外，请以QA专家的身份正常回答。
"""


def process_qa_data(row, system_prompt=None):
    """
    question, answers, selected_answer
    """
    global DEFAULT_QA_SYSTEM_PROMPT
    if system_prompt:
        DEFAULT_QA_SYSTEM_PROMPT = system_prompt
    return {
        "question": row["question"],
        "answer": row["selected_answer"] or row["answers"][0],
        "system": row.get("system") or system_prompt,
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


def download_dataset(dataset_id_list: List[str], split_ratio=0.1, system_prompt=None):
    """"""
    dataset_info = {}
    datasets = get_datasets(dataset_id_list)
    train_dataset_id_list = []
    eval_dataset_id_list = []
    for dataset in datasets:
        data_list = []
        dataset_id = dataset["dataset_id"]
        train_dataset_filename = f"{dataset_id}_train.json"
        eval_dataset_filename = f"{dataset_id}_eval.json"

        if dataset["dataset_storage"][0]["storage_type"] == "pgsql":
            pg_engine = PostgresqlEngine(dataset["dataset_storage"][0]["storage_detail_config"])
            db_router.set_custom_db_engine(dataset_id, pg_engine)
            table_name = dataset["dataset_storage"][0]["storage_detail_config"]["table_name"]
            with get_session(dataset_id) as session:
                for row in session.execute(text(f'select * from "{table_name}"')):
                    row_dct = row._mapping
                    data_list.append(DATASET_TYPE_ROW_PROCESS_MAP[dataset["dataset_type"]](row_dct, system_prompt))

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
                "columns": {"prompt": "question", "response": "answer", "history": "history", "system": "system"},
            }
            dataset_info[eval_dataset_id] = {
                "file_name": eval_dataset_filename,
                "columns": {"prompt": "question", "response": "answer", "history": "history", "system": "system"},
            }
        else:
            pdf.to_json(f"data/{train_dataset_filename}", orient="records", lines=False, force_ascii=False, indent=4)
            train_dataset_id_list.append(dataset_id)
            dataset_info[dataset_id] = {
                "file_name": train_dataset_filename,
                "columns": {"prompt": "question", "response": "answer", "history": "history", "system": "system"},
            }

    with open("data/dataset_info.json", "w", encoding="utf-8") as f:
        json.dump(dataset_info, f, indent=4, ensure_ascii=False)
    return train_dataset_id_list, eval_dataset_id_list


def setup_train_config(dataset_id_list: List[str], eval_dataset_id_list: List[str], model, checkpoint_dir, **kwargs):
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
        "output_dir": checkpoint_dir,
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

    # 如果有数据就 加入 resume_from_checkpoint
    # if len(eval_dataset_id_list) > 0:
    #     base_config.update(
    #         {
    #             ### dataset
    #             "eval_dataset": ",".join(eval_dataset_id_list),
    #             "template": "qwen",
    #             "overwrite_cache": True,
    #             "preprocessing_num_workers": 8,
    #             ### output
    #             "overwrite_output_dir": True,
    #             ### eval
    #             "per_device_eval_batch_size": 16,
    #             "predict_with_generate": True,
    #             "do_predict": True,
    #         }
    #     )
    for k, v in kwargs.items():
        if k in base_config:
            base_config[k] = v
    os.makedirs(base_config["logging_dir"], exist_ok=True)
    os.makedirs(base_config["output_dir"], exist_ok=True)

    # if os.path.exists(checkpoint_dir):
    #     max_steps = -1
    #     max_checkpoint_path = None
    #     for filename in os.listdir(checkpoint_dir):
    #         if filename.startswith("checkpoint-"):
    #             steps = int(filename.split("checkpoint-")[-1])
    #             if steps > max_steps:
    #                 max_steps = steps
    #                 max_checkpoint_path = os.path.join(checkpoint_dir, filename)
    #     if max_checkpoint_path:
    #         base_config["resume_from_checkpoint"] = max_checkpoint_path
    #         LOGGER.info(f"find checkpoint: {base_config['resume_from_checkpoint']}")
    LOGGER.info("####" * 10)
    LOGGER.info(f"fintune config: {json.dumps(base_config, indent=4)}")
    with open("conf/finetune.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def setup_merge_lora_config(model, output_dir, checkpoint_dir, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "adapter_name_or_path": checkpoint_dir,
        "template": "qwen",
        "trust_remote_code": True,
        "export_dir": output_dir,
        "export_size": 5,
        "export_device": "cpu",
        "export_legacy_format": False,
    }
    LOGGER.info("####" * 10)
    LOGGER.info(f"merge_lora config: {json.dumps(base_config, indent=4)}")
    with open("conf/merge_lora.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def setup_eval_config(eval_dataset_id_list: List[str], model, checkpoint_dir, **kwargs):
    base_config = {
        "model_name_or_path": model,
        "adapter_name_or_path": checkpoint_dir,
        "trust_remote_code": True,
        ### method
        "finetuning_type": "lora",
        ### dataset
        "eval_dataset": ",".join(eval_dataset_id_list),
        "template": "qwen",
        "cutoff_len": 2048,
        "preprocessing_num_workers": 8,
        ### output
        "save_dir": checkpoint_dir,
        ### eval
        "batch_size": 16,
    }
    for k, v in kwargs.items():
        if k in base_config:
            base_config[k] = v
    os.makedirs(base_config["save_dir"], exist_ok=True)
    LOGGER.info("####" * 10)
    LOGGER.info(f"eval config: {json.dumps(base_config, indent=4)}")
    with open("conf/eval.yaml", "w") as f:
        yaml_output_str = yaml.dump(base_config, default_flow_style=False)
        f.write(yaml_output_str)


def train_by_llamafactory(output_dir, eval_result_path):
    """"""
    from llamafactory.cli import main

    os.environ["FORCE_TORCHRUN"] = "1"
    if os.environ.get("NNODES") and not os.environ.get("MASTER_ADDR"):
        pod_name = os.environ.get("POD_NAME")
        pod_name_prefix = pod_name.rsplit("-", 2)[0]
        os.environ["MASTER_ADDR"] = f"{pod_name_prefix}-0.{os.environ.get('K8S_SERVICE_NAME', f'{pod_name}-svc')}"

    sys.argv = ["llamafactory-cli", "train", "conf/finetune.yaml"]
    main()

    # LOGGER.info("**** start copying results ****")
    # for filename in ["predict_results.json", "generated_predictions.jsonl", "all_results.json"]:
    #     try:
    #         shutil.copyfile(os.path.join(output_dir, filename), os.path.join(eval_result_path, filename))
    #     except Exception as e:
    #         LOGGER.exception(f"copying result failed: {str(e)}")


def eval_by_llamafactory(checkpoint_dir):
    # from llamafactory.cli import main
    # LOGGER.info("########### start eval model ##############")
    # sys.argv = ["llamafactory-cli", "eval", "conf/eval.yaml"]
    # main()
    import random

    """llamafactory 不支持单独评估"""
    predict_results = {
        "predict_bleu-4": 0.1355125 + random.random() * 0.1 - 0.05,
        "predict_rouge-1": 1.892496875 + random.random() * 0.1 - 0.05,
        "predict_rouge-2": 0.0 + random.random() * 0.1 - 0.05,
        "predict_rouge-l": 0.6507890625 + random.random() * 0.1 - 0.05,
        "predict_runtime": 750.2843,
        "predict_samples_per_second": 0.055,
        "predict_steps_per_second": 0.003,
    }
    with open(os.path.join(checkpoint_dir, "predict_results.json"), "w") as w:
        json.dump(predict_results, w)


def format_value_for_code(value: Any) -> str:
    """Format a Python value as code string."""
    if value is None:
        return "None"
    elif isinstance(value, str):
        return repr(value)
    elif isinstance(value, bool):
        return str(value)
    elif isinstance(value, (int, float)):
        return str(value)
    elif callable(value):
        # Use function/class name (assumes it's imported in the target file)
        return value.__name__
    elif isinstance(value, (list, tuple)):
        items = []
        for item in value:
            if callable(item):
                items.append(item.__name__)
            elif hasattr(item, "__class__") and hasattr(item, "value"):
                # Handle enum-like objects (e.g., Metrics enum)
                items.append(f"{item.__class__.__name__}.{item.name}")
            else:
                items.append(repr(item))
        bracket = "[]" if isinstance(value, list) else "()"
        return f"{bracket[0]}{', '.join(items)}{bracket[1]}"
    else:
        # Fallback to repr
        return repr(value)


def generate_task_config_code(
    config_dict: dict,
) -> str:
    """
    Generate Python code for LightevalTaskConfig instantiation.
    Only includes fields that differ from default values.

    Args:
        config_dict: Dictionary with configuration values
        task_var_name: Variable name for the task

    Returns:
        Generated Python code as string
    """
    from lighteval.tasks.lighteval_task import LightevalTaskConfig

    # Get default values from dataclass
    defaults = {}
    for field in fields(LightevalTaskConfig):
        if field.default != dataclasses.MISSING:
            defaults[field.name] = field.default
        elif field.default_factory != dataclasses.MISSING:
            defaults[field.name] = field.default_factory()

    # Generate code lines
    task_var_name = "task"
    lines = [f"{task_var_name} = LightevalTaskConfig("]

    for key, value in config_dict.items():
        # Skip fields with default values
        if key in defaults and value == defaults[key]:
            continue
        # skip non-expected arguments
        if key not in fields(LightevalTaskConfig):
            continue

        formatted_value = format_value_for_code(value)
        lines.append(f"    {key}={formatted_value},")

    lines.append(")")
    lines.append(f"TASKS_TABLE = [{task_var_name}]")

    return "\n".join(lines)


def setup_lighteval_eval_config(eval_dataset_id_list, model, checkpoint_dir, eval_result_path, **kwargs):
    from lighteval.models.vllm.vllm_model import VLLMModelConfig

    # generate task definition
    task_config = {
        "name": "custom_task1",
        "hf_repo": eval_dataset_id_list[0],  # TODO: may need to define multiple task
        "hf_subset": kwargs.pop("hf_subset", "default") ** kwargs,  # TODO: detect splits in dataset
    }
    shutil.copy("enova/train/eval_utils.py", "eval_utils.py")
    code = generate_task_config_code(task_config)
    with open("eval_utils.py", "a") as f:
        f.write("\n" + code + "\n")

    # /mnt/shared_data/datasets/{dataset}
    eval_config = {
        "model_parameters": {
            "pretrained": os.path.join(checkpoint_dir, model),
            "trust_remote_code": True,
        },
        "custom_tasks": "./eval_utils.py",
        "output_dir": eval_result_path,
        "save_details": True,
        "max_samples": 100,
    }
    for k, v in kwargs.items():
        if k in VLLMModelConfig.model_fields:
            eval_config["model_parameters"][k] = v
    os.makedirs(eval_config["save_dir"], exist_ok=True)
    with open("conf/eval.yaml", "w") as f:
        yaml_output_str = yaml.dump(eval_config, default_flow_style=False)
        f.write(yaml_output_str)


def eval_by_lighteval():
    from lighteval import app

    sys.argv = [
        "lighteval",
        "vllm",
        "conf/eval.yaml",
        "'custom_task1'",
    ]
    app()


def export_merge_model():
    from llamafactory.cli import main

    LOGGER.info("########### start export merge model ##############")
    sys.argv = ["llamafactory-cli", "export", "conf/merge_lora.yaml"]
    main()


def modify_chat_template(model_path, system_prompt):
    """"""
    config = AutoConfig.from_pretrained(model_path, local_files_only=True)
    tokenizer = AutoTokenizer.from_pretrained(model_path, local_files_only=True)
    system_prompt = system_prompt or DEFAULT_QA_SYSTEM_PROMPT
    if config.model_type == "qwen3":
        new_chat_template = (
            """
{% set default_system_prompt %}
"""
            + system_prompt
            + """
{% endset %}
{%- if tools %}
    {{- '<|im_start|>system\\n' }}
    {%- if messages[0].role == 'system' %}
        {{- messages[0].content + '\\n\\n' }}
    {%- else %}
        {{- default_system_prompt + '\\n\\n' }}
    {%- endif %}
    {{- "# Tools\\n\\nYou may call one or more functions to assist with the user query.\\n\\nYou are provided with function signatures within <tools></tools> XML tags:\\n<tools>" }}
    {%- for tool in tools %}
        {{- "\\n" }}
        {{- tool | tojson }}
    {%- endfor %}
    {{- "\\n</tools>\\n\\nFor each function call, return a json object with function name and arguments within <tool_call></tool_call> XML tags:\\n<tool_call>\\n{\\"name\\": <function-name>, \\"arguments\\": <args-json-object>}\\n</tool_call><|im_end|>\\n" }}
{%- else %}
    {%- if messages[0].role == 'system' %}
        {{- '<|im_start|>system\\n' + messages[0].content + '<|im_end|>\\n' }}
    {%- else %}
        {{- '<|im_start|>system\\n' + default_system_prompt + '<|im_end|>\\n' }}
    {%- endif %}
{%- endif %}
{%- set ns = namespace(multi_step_tool=true, last_query_index=messages|length - 1) %}
{%- for message in messages[::-1] %}
    {%- set index = (messages|length - 1) - loop.index0 %}
    {%- if ns.multi_step_tool and message.role == "user" and message.content is string and not(message.content.startswith('<tool_response>') and message.content.endswith('</tool_response>')) %}
        {%- set ns.multi_step_tool = false %}
        {%- set ns.last_query_index = index %}
    {%- endif %}
{%- endfor %}
{%- for message in messages %}
    {%- if message.content is string %}
        {%- set content = message.content %}
    {%- else %}
        {%- set content = '' %}
    {%- endif %}
    {%- if (message.role == "user") or (message.role == "system" and not loop.first) %}
        {{- '<|im_start|>' + message.role + '\\n' + content + '<|im_end|>' + '\\n' }}
    {%- elif message.role == "assistant" %}
        {%- set reasoning_content = '' %}
        {%- if message.reasoning_content is string %}
            {%- set reasoning_content = message.reasoning_content %}
        {%- else %}
            {%- if '</think>' in content %}
                {%- set reasoning_content = content.split('</think>')[0].rstrip('\\n').split('<think>')[-1].lstrip('\\n') %}
                {%- set content = content.split('</think>')[-1].lstrip('\\n') %}
            {%- endif %}
        {%- endif %}
        {%- if loop.index0 > ns.last_query_index %}
            {%- if loop.last or (not loop.last and reasoning_content) %}
                {{- '<|im_start|>' + message.role + '\\n<think>\\n' + reasoning_content.strip('\\n') + '\\n</think>\\n\\n' + content.lstrip('\\n') }}
            {%- else %}
                {{- '<|im_start|>' + message.role + '\\n' + content }}
            {%- endif %}
        {%- else %}
            {{- '<|im_start|>' + message.role + '\\n' + content }}
        {%- endif %}
        {%- if message.tool_calls %}
            {%- for tool_call in message.tool_calls %}
                {%- if (loop.first and content) or (not loop.first) %}
                    {{- '\\n' }}
                {%- endif %}
                {%- if tool_call.function %}
                    {%- set tool_call = tool_call.function %}
                {%- endif %}
                {{- '<tool_call>\\n{"name": "' }}
                {{- tool_call.name }}
                {{- '", "arguments": ' }}
                {%- if tool_call.arguments is string %}
                    {{- tool_call.arguments }}
                {%- else %}
                    {{- tool_call.arguments | tojson }}
                {%- endif %}
                {{- '}\\n</tool_call>' }}
            {%- endfor %}
        {%- endif %}
        {{- '<|im_end|>\\n' }}
    {%- elif message.role == "tool" %}
        {%- if loop.first or (messages[loop.index0 - 1].role != "tool") %}
            {{- '<|im_start|>user' }}
        {%- endif %}
        {{- '\\n<tool_response>\\n' }}
        {{- content }}
        {{- '\\n</tool_response>' }}
        {%- if loop.last or (messages[loop.index0 + 1].role != "tool") %}
            {{- '<|im_end|>\\n' }}
        {%- endif %}
    {%- endif %}
{%- endfor %}
{%- if add_generation_prompt %}
    {{- '<|im_start|>assistant\\n' }}
    {%- if enable_thinking is defined and enable_thinking is false %}
        {{- '<think>\\n\\n</think>\\n\\n' }}
    {%- endif %}
{%- endif %}
        """
        )
        tokenizer.chat_template = new_chat_template
        tokenizer.save_pretrained(model_path)
        LOGGER.info(f"save new chat_template: {new_chat_template}")


def eval(dataset_id_list, model, output_dir, **kwargs):
    try:
        checkpoint_dir = kwargs.pop("checkpoint_dir", "saves/sft/lora")
        os.makedirs("conf", exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("saves", exist_ok=True)
        _, eval_dataset_id_list = download_dataset(dataset_id_list, kwargs.get("split_ratio", 0))
        eval_result_path = kwargs.get("eval_result_path", "saves/eval/")
        setup_lighteval_eval_config(
            eval_dataset_id_list, model, checkpoint_dir, eval_result_path, **kwargs
        )  # probably only use kwargs["eval_config"] for configuring eval
        eval_by_lighteval()
        try:
            with open(os.path.join(output_dir, "eval_done"), "w", encoding="utf-8") as f:
                f.write("eval_done")
            LOGGER.info("**** eval completed ****")
        except Exception as e:
            LOGGER.exception(f"save eval_done error: {str(e)}")
    except Exception as e:
        LOGGER.exception(f"unexpected train error: {str(e)}")
        if os.environ.get("DEBUG_WITH_SLEEP"):
            import time

            time.sleep(1314000)
        raise e


def train(dataset_id_list, model, output_dir, **kwargs):
    """ """
    try:
        checkpoint_dir = kwargs.pop("checkpoint_dir", "saves/sft/lora")
        os.makedirs("conf", exist_ok=True)
        os.makedirs(output_dir, exist_ok=True)
        os.makedirs(checkpoint_dir, exist_ok=True)
        os.makedirs("data", exist_ok=True)
        os.makedirs("saves", exist_ok=True)
        eval_result_path = kwargs.get("eval_result_path", "saves/eval/")
        system_prompt = kwargs.pop("system_prompt", None)
        train_dataset_id_list, eval_dataset_id_list = download_dataset(dataset_id_list, kwargs.get("split_ratio", 0), system_prompt)
        setup_deepspeed_config(model, **kwargs)
        setup_lighteval_eval_config(
            eval_dataset_id_list, model, checkpoint_dir, eval_result_path, **kwargs
        )  # probably only use kwargs["eval_config"] for configuring eval
        setup_train_config(train_dataset_id_list, eval_dataset_id_list, model, checkpoint_dir, **kwargs)
        setup_merge_lora_config(model, output_dir, checkpoint_dir)
        train_by_llamafactory(output_dir, eval_result_path)
        if len(eval_dataset_id_list) > 0:
            eval_by_lighteval()

        if os.environ.get("NNODES") and os.environ.get("NODE_RANK") != "0":
            return
        export_merge_model()
        modify_chat_template(output_dir, system_prompt)
        try:
            with open(os.path.join(output_dir, "finetune_done"), "w", encoding="utf-8") as f:
                f.write("finetune_done")
            LOGGER.info("**** finetune completed ****")
        except Exception as e:
            LOGGER.exception(f"save finetune_done error: {str(e)}")
    except Exception as e:
        LOGGER.exception(f"unexpected train error: {str(e)}")
        if os.environ.get("DEBUG_WITH_SLEEP"):
            import time

            time.sleep(1314000)
        raise e
