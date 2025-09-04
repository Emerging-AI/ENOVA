import os
import shutil
import json
import stat
import argparse
import types
from typing import List
from datasets import Dataset
from transformers import AutoTokenizer, AutoModelForCausalLM, AutoConfig
from llmcompressor.modifiers.awq import AWQModifier
from llmcompressor import oneshot
from sqlalchemy import text
import torch
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
        model_path = get_valid_read_path(model_path, is_dir=True, check_user_stat=False)
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
        model_path = get_valid_read_path(model_path, is_dir=True, check_user_stat=False)
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
        data = json_safe_load(src_config_filepath, check_user_stat=False)

        if args.mindie_format:
            dest_quant_description_filepath = os.path.join(dest_dir, f"quant_model_description_{quantize_type.lower()}.json")
        else:
            dest_quant_description_filepath = os.path.join(dest_dir, f"quant_model_description.json")
        quant_description_data = json_safe_load(dest_quant_description_filepath, check_user_stat=False)

        data["torch_dtype"] = str(torch_dtype).split(".")[1]
        if args.mindie_format:
            data["quantize"] = quantize_type
        if args is not None:
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

            if args.mindie_format:
                data["quantization_config"] = quantization_config

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
    import os
    import json
    import torch
    import torch.nn.functional as F

    from msmodelslim.pytorch.llm_ptq.anti_outlier import AntiOutlier, AntiOutlierConfig
    from msmodelslim.pytorch.llm_ptq.llm_ptq_tools import Calibrator, QuantConfig
    from msmodelslim.pytorch.llm_ptq.llm_ptq_tools.layer_select import LayerSelector

    CPU = "cpu"
    NPU = "npu"
    rank: int = int(os.getenv("RANK", "0"))

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

    def get_down_proj_disable_names(num_layers: int) -> list:
        disable_names = ["lm_head"]
        # 遍历层数并添加对应的 disable_names
        for i in range(num_layers):
            disable_names.append(f"model.layers.{i}.mlp.down_proj")
        return disable_names

    def get_c_proj_disable_names(num_layers: int) -> list:
        disable_names = ["lm_head"]
        # 遍历层数并添加对应的 disable_names
        for i in range(num_layers):
            disable_names.append(f"transformer.h.{i}.mlp.c_proj")
        return disable_names

    def get_padding_data(tokenizer, calib_list, device_type):
        calib_dataset = []
        max_len = 0
        for calib_data in calib_list:
            inputs = tokenizer(calib_data, return_tensors="pt", add_special_tokens=False)
            calib_dataset.append(inputs.data["input_ids"].to(device_type))
            max_len = max(max_len, inputs.data["input_ids"].size(1))
        new_calib_dataset = []
        for inputs in calib_dataset:
            new_inputs = F.pad(inputs, (0, max_len - inputs.size(1)), value=0)
            new_calib_dataset.append(new_inputs)
        return [torch.cat(new_calib_dataset)]

    def get_batch_tokenized_data(tokenizer, input_texts, device_type, batch_size=4):
        batch_ant_calib_texts = [input_texts[i : i + batch_size] for i in range(0, len(input_texts), batch_size)]
        tokenized_ant_calib_data = []
        for prompt in batch_ant_calib_texts:
            tmp = get_padding_data(tokenizer, prompt, device_type)
            tokenized_ant_calib_data.append(tmp)
        return tokenized_ant_calib_data

    def auto_layer_select(model, disable_names, disable_threshold, select_layer_data):

        layer_selector = LayerSelector(model=model, layer_names=disable_names)
        layer_selector.run(select_layer_data)
        return layer_selector.select_layers_by_threshold(disable_threshold)

    def get_select_anti_dataset(tokenizer, mixed_dataset, device="npu"):
        """用于离群值抑制的校准集"""
        anti_data = []
        for prpt_ans in mixed_dataset:
            calib_dataset = []
            calib_list = [prpt_ans["prompt"]]
            max_len = 0
            for calib_data in calib_list:
                inputs = tokenizer(calib_data, return_tensors="pt")
                calib_dataset.append(inputs.data["input_ids"].to(device))
                max_len = max(max_len, inputs.data["input_ids"].size(1))
            for i, data in enumerate(calib_dataset):
                calib_dataset[i] = F.pad(data, (0, max_len - data.size(1)), value=0)
            anti_data.append(torch.cat(calib_dataset))

        anti_dataset = []
        for data in anti_data:
            anti_dataset.append([data])

        return anti_dataset

    def parse_arguments():
        # parser = ArgumentParser()
        # parser.add_argument('--model_path', type=str, help="model and tokenizer path")
        # parser.add_argument('--save_directory', type=str)
        # parser.add_argument('--part_file_size', type=int, default=None)
        # parser.add_argument(
        #     '--calib_texts',
        #     type=str,
        #     nargs='+',
        #     default=None)
        # parser.add_argument(
        #     '--calib_file',
        #     type=str,
        #     help='A jsonl file contains calibration data.',
        #     default=os.path.join(os.path.dirname(os.path.dirname(__file__)), 'common', 'teacher_qualification.jsonl'))
        # parser.add_argument('--w_bit', type=int, default=8)
        # parser.add_argument('--a_bit', type=int, default=8)
        # parser.add_argument('--disable_names', type=str, nargs='+', default=None)
        # parser.add_argument('--device_type', type=str, choices=[CPU, NPU], default=CPU)
        # parser.add_argument('--fraction', type=float, default=0.01)
        # parser.add_argument("--act_method", type=int, choices=[1, 2, 3], default=1,
        #                     help=" 1: MinMax, 2: Histogram, 3: Auto")
        # parser.add_argument('--co_sparse', type=cmd_bool, default=False)
        # parser.add_argument('--anti_method', type=str, default='')
        # parser.add_argument('--disable_level', type=str, default='L0')
        # parser.add_argument('--do_smooth', type=cmd_bool, default=False)
        # parser.add_argument('--use_sigma', type=cmd_bool, default=False)
        # parser.add_argument('--use_reduce_quant', type=cmd_bool, default=False)
        # parser.add_argument('--tp_size', type=int, default=1)
        # parser.add_argument('--sigma_factor', type=float, default=3.0)
        # parser.add_argument('--is_lowbit', type=cmd_bool, default=False)
        # parser.add_argument('--w_sym', type=cmd_bool, default=True)
        # parser.add_argument('--use_kvcache_quant', type=cmd_bool, default=False)
        # parser.add_argument('--use_fa_quant', type=cmd_bool, default=False)
        # parser.add_argument('--fa_amp', type=int, default=0)
        # parser.add_argument('--open_outlier', type=cmd_bool, default=True)
        # parser.add_argument('--group_size', type=int, default=64)
        # parser.add_argument('--is_dynamic', type=cmd_bool, default=False)
        # # parser.add_argument('--input_ids_name', type=str, default='input_ids',
        # #                     validator=StringArgumentValidator(min_length=1, max_length=MAX_KEY_LENGTH))
        # # parser.add_argument('--attention_mask_name', type=str, default='attention_mask',
        # #                     validator=StringArgumentValidator(min_length=1, max_length=MAX_KEY_LENGTH))
        # # parser.add_argument('--tokenizer_args', type=str, default='{}',
        # #                     validator=StringArgumentValidator(min_length=2, max_length=MAX_JSON_LENGTH))
        # # parser.add_argument('--disable_last_linear', type=cmd_bool, default=True)
        # # parser.add_argument('--model_name', type=str, default=None,
        # #                     validator=StringArgumentValidator(min_length=1, max_length=MAX_KEY_LENGTH, allow_none=True))
        # parser.add_argument('--model_type', type=str, default='qwen2',
        #                     choices=['qwen1', 'qwen1.5', 'qwen2', 'qwen2.5', 'qwen3'],
        #                     help='Specify the type of qwen model (choices: qwen1, qwen1.5, qwen2, qwen2.5, qwen3)')
        # parser.add_argument('--anti_calib_file', type=str, default=None,
        #                 help='Path to anti-calibration data file (.json or .jsonl)')
        # parser.add_argument('--disable_threshold', type=float, default=0,
        #                 help='Disable threshold when auto select disable names')
        # parser.add_argument('--pdmix', type=cmd_bool, default=False,
        #                 help='use pdmix quantization type')
        # parser.add_argument('--trust_remote_code', type=cmd_bool, default=False)
        # parser.add_argument('--layer_count', type=int, default=0)
        # parser.add_argument('--mindie_format', action="store_true", help="Compatible with quantization formats \
        #                     supported by before B050 version of MindIE")
        # parser.add_argument('--w_method', type=str, default='MinMax',
        #                     choices=['MinMax', 'GPTQ', 'HQQ', 'NF'],
        #                     help='Specify the type of weight quantization method (choices: MinMax, GPTQ, HQQ, NF)')
        # return parser.parse_args()
        default_config = {
            "model_path": model,
            "save_directory": output_dir,
            "part_file_size": None,
            "calib_texts": None,
            "calib_file": os.path.join(os.path.dirname(os.path.dirname(__file__)), "common", "teacher_qualification.jsonl"),
            "w_bit": 8,
            "a_bit": 8,
            "disable_names": None,
            "device_type": "CPU",  # 假设 CPU 是字符串常量
            "fraction": 0.01,
            "act_method": 1,
            "co_sparse": False,
            "anti_method": "",
            "disable_level": "L0",
            "do_smooth": False,
            "use_sigma": False,
            "use_reduce_quant": False,
            "tp_size": 1,
            "sigma_factor": 3.0,
            "is_lowbit": False,
            "w_sym": True,
            "use_kvcache_quant": False,
            "use_fa_quant": False,
            "fa_amp": 0,
            "open_outlier": True,
            "group_size": 64,
            "is_dynamic": False,
            "model_type": "qwen2",
            "anti_calib_file": None,
            "disable_threshold": 0,
            "pdmix": False,
            "trust_remote_code": False,
            "layer_count": 0,
            "mindie_format": False,
            "w_method": "MinMax",
        }
        default_config.update(kwargs)
        config = types.SimpleNamespace(**default_config)
        return config

    class Quantifier:
        def __init__(self, model_path_or_name, args, anti_outlier_config=None, device_type="cpu", **kwargs):
            self.args = args
            safe_generator = SafeGenerator()
            self.device_type = device_type
            device_map = CPU if self.device_type == CPU else "auto"
            self.anti_outlier_config = anti_outlier_config
            self.model_path_or_name = model_path_or_name
            self.trust_remote_code = self.args.trust_remote_code

            self.config = safe_generator.get_config_from_pretrained(self.model_path_or_name, trust_remote_code=self.trust_remote_code)
            self.layer_count = kwargs.get("layer_count", 0)
            self.config.num_hidden_layers = self.layer_count if self.layer_count > 0 else self.config.num_hidden_layers
            self.dtype = self.config.torch_dtype if self.device_type == NPU else torch.float32
            self.model = safe_generator.get_model_from_pretrained(
                self.model_path_or_name,
                low_cpu_mem_usage=True,
                torch_dtype=self.dtype,
                device_map=device_map,
                trust_remote_code=self.trust_remote_code,
            )

            tokenizer_args = kwargs.get("tokenizer_args", {})
            self.tokenizer = safe_generator.get_tokenizer_from_pretrained(
                self.model_path_or_name, use_fast=False, trust_remote_code=self.trust_remote_code, legacy=False, **tokenizer_args
            )
            self.model_name = kwargs.get("model_name", None)
            self.quant_config = None

        def create_quant_config(
            self,
            num_layers,
            select_layer_data=None,
        ):
            args = self.args
            disable_names = args.disable_names
            # Check if disable_names is provided, if not and a_bit is 8, generate disable_names
            if not disable_names and args.a_bit in [8, 16]:
                if args.disable_threshold > 0:
                    disable_names = get_down_proj_disable_names(num_layers)
                elif args.model_type == "qwen1":
                    disable_names = get_c_proj_disable_names(num_layers)
                else:
                    disable_names = get_down_proj_disable_names(num_layers)
            if args.disable_threshold > 0:
                disable_names = auto_layer_select(self.model, disable_names, args.disable_threshold, select_layer_data)

            quant_config = QuantConfig(
                w_bit=args.w_bit,
                a_bit=args.a_bit,
                disable_names=disable_names,
                dev_type=args.device_type,
                dev_id=rank,
                act_method=args.act_method,
                w_sym=args.w_sym,
                mm_tensor=False,
                co_sparse=args.co_sparse,
                fraction=args.fraction,
                sigma_factor=args.sigma_factor,
                use_sigma=args.use_sigma,
                is_lowbit=args.is_lowbit,
                do_smooth=args.do_smooth,
                open_outlier=args.open_outlier,
                group_size=args.group_size,
                use_kvcache_quant=args.use_kvcache_quant,
                is_dynamic=args.is_dynamic,
                disable_last_linear=args.disable_last_linear,
                w_method=args.w_method,
                pdmix=args.pdmix,
            )

            if args.use_fa_quant:
                quant_config = quant_config.fa_quant(fa_amp=args.fa_amp)
            self.quant_config = quant_config

        def get_batch_tokenized_data(self, input_texts, batch_size=4):
            return get_batch_tokenized_data(self.tokenizer, input_texts, self.device_type, batch_size)

        def get_tokenized_data(self, input_texts, input_ids_name="input_ids", attention_mask_name="attention_mask"):
            tokenized_data = []
            for input_text in input_texts:
                inputs = self.tokenizer(input_text, return_tensors="pt", padding=True).to(self.device_type)
                tokenized_data.append([inputs.data[input_ids_name], inputs.data[attention_mask_name]])
            return tokenized_data

        def convert(self, tokenized_data, save_path, disable_level, part_file_size=None, tokenized_ant_calib_data=None):
            if self.device_type == NPU:
                # 避免在线编译算子，使用二进制编译的算子
                torch.npu.set_compile_mode(jit_compile=False)
            if tokenized_ant_calib_data is None:
                tokenized_ant_calib_data = tokenized_data

            if self.anti_outlier_config is not None:
                if self.model_name == "baichuan":
                    anti_outlier = AntiOutlier(
                        self.model, calib_data=tokenized_ant_calib_data, cfg=self.anti_outlier_config, norm_class_name="RMSNorm"
                    )
                else:
                    anti_outlier = AntiOutlier(self.model, calib_data=tokenized_ant_calib_data, cfg=self.anti_outlier_config)
                anti_outlier.process()

            if not os.path.exists(save_path):
                os.mkdir(save_path, mode=0o750)

            calibrator = Calibrator(self.model, self.quant_config, calib_data=tokenized_data, disable_level=disable_level)
            calibrator.run()
            save_type = "safe_tensor" if args.mindie_format else "ascendV1"
            calibrator.save(save_path, save_type=[save_type], part_file_size=part_file_size)

    args = parse_arguments()
    checker = SafeGenerator()
    rank: int = int(os.getenv("RANK", "0"))

    model_path = args.model_path
    save_directory = args.save_directory

    num_layers = checker.get_config_from_pretrained(model_path, trust_remote_code=args.trust_remote_code).num_hidden_layers

    num_layers = args.layer_count if args.layer_count > 0 else num_layers

    anti_outlier_config_val = None
    if args.anti_method == "m3":
        anti_outlier_config_val = AntiOutlierConfig(
            a_bit=args.a_bit, w_bit=args.w_bit, anti_method=args.anti_method, w_sym=args.w_sym, dev_type=args.device_type, dev_id=rank
        )
    elif args.anti_method == "m6":
        keys = [".o_proj"]
        anti_disable_names = ["model.layers.{}.self_attn.o_proj".format(i) for i in range(num_layers)]
        if args.model_type == "qwen3":
            anti_outlier_config_val = AntiOutlierConfig(
                a_bit=args.a_bit,
                w_bit=args.w_bit,
                w_sym=args.w_sym,
                anti_method=args.anti_method,
                dev_type=args.device_type,
                disable_anti_names=anti_disable_names,
                flex_config={"alpha": 0.4, "beta": 0.325},
            )
        else:
            anti_outlier_config_val = AntiOutlierConfig(
                anti_method=args.anti_method,
                dev_type=args.device_type,
                disable_anti_names=anti_disable_names,
                flex_config={"alpha": 0.6, "beta": 0.3},
            )
    elif args.anti_method:
        anti_outlier_config_val = AntiOutlierConfig(anti_method=args.anti_method, dev_type=args.device_type)

    tokenizer_args = parse_tokenizer_args(args.tokenizer_args, default={})
    if tokenizer_args == {} and args.model_type == "qwen1":
        tokenizer_args = {"padding_side": "left", "pad_token": "<|extra_0|>", "eos_token": "<|endoftext|>"}
    quantifier = Quantifier(
        model_path,
        args,
        anti_outlier_config_val,
        device_type=args.device_type,
        tokenizer_args=tokenizer_args,
        model_name=args.model_name,
        layer_count=args.layer_count,
    )

    # tokenized_calib_data = []
    # if args.calib_file.lower() == 'none':
    #     args.calib_file = None
    # calib_file = args.calib_file
    # if calib_file:
    #     if calib_file.endswith('.jsonl'):
    #         calib_texts = checker.load_jsonl(calib_file)
    #         if calib_texts is not None:
    #             tokenized_calib_data = quantifier.get_tokenized_data(
    #                 calib_texts,
    #                 # input_ids_name=args.input_ids_name,
    #                 # attention_mask_name=args.attention_mask_name
    #             )
    #     elif calib_file.endswith('.json'):
    #         def get_calib_dataset(tokenizer, mixed_dataset, device='npu'):
    #             """用于量化的校准集"""
    #             dataset_calib = []
    #             for prpt_ans in mixed_dataset:
    #                 calib_list = [prpt_ans["prompt"]]
    #                 calib_dataset = []
    #                 for calib_data in calib_list:
    #                     inputs = tokenizer(calib_data, return_tensors='pt').to(device)
    #                     calib_dataset.append([inputs.data['input_ids']])
    #                 dataset_calib += calib_dataset

    #             return dataset_calib
    #         with open(calib_file, 'r') as f:
    #             calib_promt = json.load(f)
    #         tokenized_calib_data = get_calib_dataset(quantifier.tokenizer, calib_promt, args.device_type)
    #     else:
    #         raise ValueError("Unsupported calibration file format: {}".format(calib_file))
    # else:
    #     calib_texts = args.calib_texts

    calib_texts = list(dataset["text"])

    tokenized_calib_data = quantifier.get_tokenized_data(
        calib_texts,
        # input_ids_name=args.input_ids_name,
        # attention_mask_name=args.attention_mask_name
    )

    tokenized_ant_calib_data = tokenized_calib_data
    if args.anti_calib_file:
        if args.model_type == "qwen3":
            anti_calib_file_path = args.anti_calib_file
            with open(anti_calib_file_path, "r") as f:
                anti_promt = json.load(f)
            tokenized_ant_calib_data = get_select_anti_dataset(quantifier.tokenizer, anti_promt, args.device_type)
        else:
            ant_calib_texts = checker.load_jsonl(args.anti_calib_file)
            if ant_calib_texts is not None:
                tokenized_ant_calib_data = quantifier.get_batch_tokenized_data(ant_calib_texts)

    if isinstance(args.disable_threshold, float) and args.disable_threshold > 0:
        quantifier.create_quant_config(num_layers, tokenized_ant_calib_data)
    elif args.disable_threshold == 0:
        quantifier.create_quant_config(num_layers)
    else:
        raise ValueError("disable_threshold should be a float number >= 0")

    quantifier.convert(
        tokenized_calib_data,
        save_directory,
        args.disable_level,
        part_file_size=args.part_file_size,
        tokenized_ant_calib_data=tokenized_ant_calib_data,
    )

    # 通过 model_quant_type 获得 quant_type
    quant_type = quantifier.quant_config.model_quant_type.lower()

    auto_config = checker.get_config_from_pretrained(model_path, trust_remote_code=args.trust_remote_code)
    checker.modify_config(model_path, save_directory, auto_config.torch_dtype, quant_type, args)
    checker.copy_tokenizer_files(model_path, save_directory)


def quantize_by_llmcompressor(model, dataset_id_list, output_dir, quantization_method="awq", **kwargs):
    """"""
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
        return quantize_by_msmodelslim(model, dataset_id_list, output_dir, quantization_method=quantization_method, **kwargs)
    return quantize_by_llmcompressor(model, dataset_id_list, output_dir, quantization_method=quantization_method, **kwargs)
