from datetime import datetime

import numpy as np
import pandas as pd

from enova.common.logger import LOGGER


def metric_freq(metric, th=0.8):
    """metric frequency"""

    # observation points should be larger than 5
    if len(metric) < 5:
        return None

    delta_t = np.unique(np.diff([v[0] for v in metric]), return_counts=True)
    if np.max(delta_t[1]) / np.sum(delta_t[1]) > th:
        return delta_t[0][np.argmax(delta_t[1])]
    return None


def metric_norm(metric, n=30, th=0.8, fill_v=0):
    """metric preprocessing via frequency normalization"""

    metric_s = sorted(metric, key=lambda x: x[0], reverse=False)
    df = pd.DataFrame(metric_s, columns=["timestamp", "value"])

    freq = metric_freq(metric_s, th=th)
    if freq is None:
        return df, freq

    index = pd.date_range(
        datetime.fromtimestamp((-n + 1) * 60 + metric_s[-1][0]),
        datetime.fromtimestamp(metric_s[-1][0]),
        freq=f"{freq / 60}min",
    )

    df["date_time"] = [datetime.fromtimestamp(t[0]) for t in metric_s]
    df = df.set_index("date_time").reindex(index, fill_value=fill_v)
    df["timestamp"] = [idx.timestamp() for idx in index]
    return df, freq


def metric_process(params, name, **kwargs):
    metric, freq = None, None
    i = 0
    resp = [metric_norm(metric[name], **kwargs) for metric in params["metrics"]]
    for df, freq in resp:
        # not consider the replica of LLM service without enough observation points
        if freq is None:
            continue
        i += 1
        if metric is None:
            metric = df
        else:
            metric["value"] += df["value"]
    return metric, i, freq


def llm_performance_ad(params, **kwargs):
    # constant default rules
    m = kwargs.get("detect_window", 3)
    LOGGER.debug(f"llm_performance_ad params: {params}")
    # scale up
    pending_requests, i, freq = metric_process(params, "pending_requests", **kwargs)
    if not i:
        is_up_anomaly = False
    else:
        th = kwargs.get("pending_threshold", 50)

        pending_requests = pending_requests.resample("1min").sum()
        LOGGER.info(f"llm_performance_ad pending_requests: {pending_requests}")
        is_up_anomaly = all(pending_requests["value"].to_numpy()[-m:] >= th)

    # scale down
    if params["configurations"]["replicas"] == 1:
        return {"is_anomaly": int(is_up_anomaly)}

    kv_cache_usage, i, freq = metric_process(params, "gpu_kv_cache_usage", **kwargs)
    if not i:
        is_down_anomaly = False
    else:
        th = kwargs.get("gpu_kv_cache_threshold", 10)
        kv_cache_usage = kv_cache_usage.resample("1min").mean() / i
        is_down_anomaly = all(kv_cache_usage["value"].to_numpy()[-m:] <= th)

    running_requests, i, freq = metric_process(params, "running_requests", **kwargs)
    if not i:
        is_down_anomaly = False
    else:
        th = kwargs.get("running_threshold", 0.1)
        running_requests = running_requests.resample("1min").mean() / i
        is_down_anomaly = is_down_anomaly & all(
            running_requests["value"].to_numpy()[-m:] <= th * params["configurations"]["max_num_seqs"]
        )

    # TODO: collect data, and update detection model

    return {"is_anomaly": int(is_up_anomaly | is_down_anomaly)}


class LLMConfig:
    """
    # TODO: Automatically get these configs by launching a job.
    # Since param size is depended on llm framework, we will obtain these configs after launching a job.
    #
    # For param_size
    # param_size = vocab_size * hidden_size + num_hidden_layers * (attn_size + o_size + mlp_size)
    #       + hidden_size * vocab_size // depends on llm framework
    # attn_size = hidden_size * (k_dim + v_dim + q_dim) // depends on llm framework
    # o_size = hidden_size * hidden_size
    # mlp_size = hidden_size * intermediate_size * 2 + intermediate_size * hidden_size // depends on llm framework
    #
    # For token_size
    # token_size = k_token_size + v_token_size
    # k_token_size = num_layers * k_dim; v_token_size = num_layers * v_dim // k_dim = n_head * d_size
    """

    LLM_CONFIG = {
        "baichuan": {
            7: {
                "param_size": 7505707008,
                "token_size": 262144,
                "n_head": 32,
                "seq_length": 4096,
            },
            13: {
                "param_size": 13896253440,
                "token_size": 409600,
                "n_head": 40,
                "seq_length": 8192,
            },
        },
        "chatglm": {
            6: {
                "param_size": 6243221504,
                "token_size": 86016,
                "n_head": 32,
                "seq_length": 8192,
            }
        },
        "gemma": {
            2: {
                "param_size": 2506096640,
                "token_size": 9216,
                "n_head": 8,
                "seq_length": 8192,
            },
            7: {
                "param_size": 8537505792,
                "token_size": 262144,
                "n_head": 16,
                "seq_length": 8192,
            },
        },
        "llama": {
            7: {
                "param_size": 6607077376,
                "token_size": 262144,
                "n_head": 32,
                "seq_length": 4096,
            },
            13: {
                "param_size": 12851609600,
                "token_size": 409600,
                "n_head": 40,
                "seq_length": 4096,
            },
        },
        "mistral": {
            7: {
                "param_size": 7110393856,
                "token_size": 65536,
                "n_head": 32,
                "seq_length": 32768,
            }
        },
        "qwen": {
            7: {
                "param_size": 7720665088,
                "token_size": 262144,
                "n_head": 32,
                "seq_length": 8192,
            },
            14: {
                "param_size": 14166261760,
                "token_size": 409600,
                "n_head": 40,
                "seq_length": 8192,
            },
        },
    }

    DEFAULT_CONFIG = {
        7: {
            "token_size": 262144,  # k_token_size: 4096, num_layers: 32
            "seq_length": 8192,
        },
        13: {
            "token_size": 409600,  # k_token_size: 5120, num_layers: 40
            "seq_length": 8192,
        },
        70: {
            "token_size": 1310720,  # k_token_size: 8192, num_layers: 80
            "seq_length": 8192,
        },
    }


class GPUConfig:
    """
    # TODO: Automatically calculate the batch sizes of continuous batching based on ttft prediction model.
    # More training data need to be collected before deployed online.
    """

    BATCH_BASELINE = 256 * (7 * 1024**3)


class RecConfig:
    MAX_NUM_SEQ = [8, 16, 32, 64, 128, 256, 512, 1024]
    GPU_MEM_UTIL = [
        0.4,
        0.5,
        0.6,
        0.7,
        0.8,
        0.9,
    ]


def prime_factors(n):
    factors = []
    i = 2
    while i * i <= n:
        if n % i:
            i += 1
        else:
            n //= i
            factors.append(i)
    if n > 1:
        factors.append(n)
    return factors


def find_divisors(n):
    factors = prime_factors(n)
    divisors = {1}
    for i in range(len(factors)):
        temp_divisors = set()
        for divisor in divisors:
            temp_divisors.add(divisor * factors[i])
        divisors |= temp_divisors
    return sorted(divisors)


def config_match(llm, param):
    try:
        config = LLMConfig.LLM_CONFIG[llm][param]
    except Exception as e:
        LOGGER.info(f"Failed to match LLM config: {llm}, {param}, {e}. Adopt default instead.")
        param_key = min(LLMConfig.DEFAULT_CONFIG.keys(), key=lambda x: abs(x - param))
        config = {
            "param_size": param * 1024**3,
            "token_size": LLMConfig.DEFAULT_CONFIG[param_key]["token_size"],
            "n_head": 8,
            "seq_length": LLMConfig.DEFAULT_CONFIG[param_key]["seq_length"],
        }
    return config


def max_num_seqs_rec(llm_config):
    return min(RecConfig.MAX_NUM_SEQ, key=lambda x: abs(x - GPUConfig.BATCH_BASELINE / llm_config["param_size"]))


def memory_estimation(param_size, token_size, seq_length, dtype_size=2, mem_activations=5):
    return (param_size + token_size * seq_length) * dtype_size + mem_activations


def memory_config_rec(total_mem, n_head, gpu_spec, gpu_num, r_limit=0.9):
    # for each GPU, safe limit
    gpu_spec = gpu_spec * 0.9
    tp_size, mem_util = None, None
    for s in find_divisors(n_head):
        if s * gpu_spec * 1024**3 * max(RecConfig.GPU_MEM_UTIL) > total_mem and s <= gpu_num:
            tp_size = s
            break

    if tp_size is None:
        LOGGER.warning(f"GPU Memory is not enough for allocation: total_mem={total_mem}.")
    else:
        for m in RecConfig.GPU_MEM_UTIL:
            if m * tp_size * gpu_spec * 1024**3 > total_mem:
                mem_util = m
                break
    return tp_size, mem_util


def gpu_memory_rec(llm_config, gpu_config, dtype_size=2, mem_activations=5):
    """
    The tensor parallel size and gpu_memory_usage recommendation.

    :param llm_config:
    :param gpu_config:
    :param dtype_size:
    :param mem_activations: memory used to place activations and other variables.
    """
    total_mem = memory_estimation(
        llm_config["param_size"], llm_config["token_size"], llm_config["seq_length"], dtype_size, mem_activations
    )

    gpu_spec, gpu_num = gpu_config["spec"], gpu_config["num"]

    tp_size, mem_util = memory_config_rec(total_mem, llm_config["n_head"], gpu_spec, gpu_num)
    return tp_size, mem_util


def llm_config_recommendations(params, **kwargs):
    config = config_match(params["llm"]["framework"], params["llm"]["param"])
    max_num_seqs = max_num_seqs_rec(config)

    dtype_size = kwargs.get("dtype_size", 2)
    # Default 3.0 GB to store inner state variables.
    # When loading Mistral-7B, it needs about more 5.0 GB memories to store inner state variables.
    mem_activations = 3 if params["llm"]["framework"].lower() != "mistral" else 5
    mem_activations = kwargs.get("mem_activations", mem_activations) * 1024**3
    tp_size, mem_util = gpu_memory_rec(config, params["gpu"], dtype_size, mem_activations)

    return {
        "max_num_seqs": max_num_seqs,
        "tensor_parallel_size": tp_size,
        "gpu_memory_utilization": mem_util,
        "replicas": 1,
    }


def llm_config_recovery(params, **kwargs):
    config = config_match(params["llm"]["framework"], params["llm"]["param"])

    dtype_size = kwargs.get("dtype_size", 2)
    mem_activations = kwargs.get("mem_activations", 5) * 1024**3
    lower_mem = memory_estimation(
        config["param_size"], config["token_size"], config["seq_length"], dtype_size, mem_activations
    )

    m = kwargs.get("detect_window", 3)
    max_num_seqs = params["configurations"]["max_num_seqs"]
    tp_size = params["configurations"]["tensor_parallel_size"]
    mem_util = params["configurations"]["gpu_memory_utilization"]
    replicas = params["configurations"]["replicas"]

    # If collected data is out of expectation, we do not recommend the recovery configurations.
    pending_requests, i, freq = metric_process(params, "pending_requests", **kwargs)
    if replicas != i:
        LOGGER.warning("The number of collected pending_requests is not equal to the replicas of LLM service ")
        return params["configurations"]
    pending_requests = pending_requests.resample("1min").sum()

    kv_cache_usage, i, freq = metric_process(params, "gpu_kv_cache_usage", **kwargs)
    if replicas != i:
        LOGGER.warning("The number of collected kv_cache_usage is not equal to the replicas of LLM service ")
        return params["configurations"]
    kv_cache_usage = kv_cache_usage.resample("1min").mean() / i

    running_requests, i, freq = metric_process(params, "running_requests", **kwargs)
    if replicas != i:
        LOGGER.warning("The number of collected running_requests is not equal to the replicas of LLM service ")
        return params["configurations"]
    running_requests = running_requests.resample("1min").mean() / i

    th = kwargs.get("pending_threshold", 50)
    batch_usage = np.percentile(running_requests["value"].to_numpy()[-m:], 90) / max_num_seqs
    kv_cache_usage = np.percentile(kv_cache_usage["value"].to_numpy()[-m:], 90)

    is_scale_up = all(pending_requests["value"].to_numpy()[-m:] >= th)
    is_scale_down = (batch_usage < kwargs.get("running_threshold", 0.1)) & (
        kv_cache_usage < kwargs.get("gpu_kv_cache_threshold", 10)
    )

    # 1) max_num_seqs verification
    # Here we adopt default GPU config
    # TODO: Automatically calculate the batch sizes of continuous batching based on ttft prediction model.
    # More training data need to be collected before deployed online.
    if is_scale_up or is_scale_down:
        max_num_seqs_new = max_num_seqs_rec(config)
    else:
        max_num_seqs_new = max_num_seqs

    # 2) gpu_memory_utilization verification
    # Scale up verification: kv_cache_usage, running requests
    # A. if kv_cache_usage is near full and running requests do not reach max_num_seqs,
    #       the allocated memory for one replica of LLM service is not enough.
    # B. if kv_cache_usage does not reach 100% and pending requests exist,
    #       the allocated memory for one replica of LLM service is wasted.
    param_mem = config["param_size"] * dtype_size

    if is_scale_up:
        gpu_spec, gpu_num = params["gpu"]["spec"], params["gpu"]["num"]
        current_mem = tp_size * mem_util * gpu_spec * 1024**3

        if kv_cache_usage < 90 and batch_usage < 0.9:
            LOGGER.warning("The collected metrics may be made-up. Configuration recommendation will not be executed.")
            return params["configurations"]

        if kv_cache_usage > 90 and batch_usage < 0.9:
            required_kv_mem = (current_mem - param_mem) / batch_usage
        elif kv_cache_usage < 90 and batch_usage > 0.9:
            required_kv_mem = kv_cache_usage * (current_mem - param_mem) / 100
        else:
            required_kv_mem = current_mem - param_mem
        required_mem = max(required_kv_mem + param_mem, lower_mem)

        tp_size_new, mem_util_new = memory_config_rec(required_mem, config["n_head"], gpu_spec, gpu_num)
        if tp_size_new is None:
            LOGGER.info("The memory of current gpu is not enough to store kv_cache. Use the upper limit instead.")
            tp_size_new = max(RecConfig.GPU_MEM_UTIL)
            mem_util_new = max([v for v in find_divisors(config["n_head"]) if v <= gpu_num])
    else:
        tp_size_new, mem_util_new = tp_size, mem_util

    # 3) replicas prediction
    # Scale up: more replicas to achieve success requests → New requests.
    #       Success Requests: the capacity of one replica of LLM service.
    #       New requests: the number of requests per minute from actual industrial users.
    # Scale down: fewer replicas to achieve batch_usage, kv_cache_usage → 100%.
    #       The replicas will be scaled down via multiple steps,
    #       while the rate of scaling-down can not be lower than 50% in one step.

    if is_scale_up:
        gpu_spec, gpu_num = params["gpu"]["spec"], params["gpu"]["num"]

        server_new_requests, i, freq = metric_process(params, "server_new_requests", **kwargs)
        server_success_requests, j, freq = metric_process(params, "server_success_requests", **kwargs)
        if replicas != i or replicas != j:
            LOGGER.warning("The number of collected server requests is not equal to the replicas of LLM service.")
            replicas_new = replicas
        else:
            new_requests = np.percentile(server_new_requests["value"].to_numpy()[-m:], 90)
            success_requests = np.percentile(server_success_requests["value"].to_numpy()[-m:], 90)

            new_mem = tp_size_new * mem_util_new * gpu_spec * 1024**3 - param_mem
            old_mem = tp_size * mem_util * gpu_spec * 1024**3 - param_mem
            replicas_new = np.clip(
                int(np.ceil(old_mem / new_mem * new_requests / success_requests * replicas)),
                replicas,
                gpu_num // tp_size_new,
            )
    elif is_scale_down:
        replicas_new = np.ceil(replicas / 2)
    else:
        replicas_new = replicas

    return {
        "max_num_seqs": int(max_num_seqs_new),
        "tensor_parallel_size": int(tp_size_new),
        "gpu_memory_utilization": mem_util_new,
        "replicas": int(replicas_new),
    }


class AlgoService:
    async def anomaly_recover(self, params):
        """anomaly recover via configuration update"""

        return llm_config_recovery(params)

    async def anomaly_detect(self, params):
        """anomalous llm performance detection"""

        return llm_performance_ad(params)

    async def config_recommend(self, params):
        """configuration recommendation when cold-start"""

        return llm_config_recommendations(params)


if __name__ == "__main__":
    rs = 120
    param = {
        "metrics": [
            {
                "pending_requests": [[1713164400 + (i - 29) * 15, np.random.randint(50, 100)] for i in range(rs)],
                "running_requests": [[1713164400 + (i - 29) * 15, np.random.randint(0, 10)] for i in range(rs)],
                "gpu_kv_cache_usage": [[1713164400 + (i - 29) * 15, np.random.randint(0, 5)] for i in range(rs)],
                "server_new_requests": [[1713164400 + (i - 29) * 15, np.random.randint(320, 400)] for i in range(rs)],
                "server_success_requests": [
                    [1713164400 + (i - 29) * 15, np.random.randint(80, 100)] for i in range(rs)
                ],
            }
            for _ in range(2)
        ],
        "llm": {"framework": "mistral", "param": 7.0},
        "gpu": {
            "name": "4090",
            "spec": 24,
            "num": 8,
        },
        "configurations": {
            "max_num_seqs": 256,
            "tensor_parallel_size": 1,
            "gpu_memory_utilization": 0.95,
            "replicas": 2,
        },
    }
    # print(llm_config_recommendations(param, **{"fill_v": 0, "n": 50}))
    # print(llm_performance_ad(param, **{'fill_v': 0, 'n': 50}))
    # print(llm_config_recovery(param, **{"fill_v": 0, "n": 50}))
