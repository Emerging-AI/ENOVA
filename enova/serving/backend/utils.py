import numpy as np
from transformers import AutoConfig, AutoModel, AutoModelForCausalLM
from enova.common.logger import LOGGER


def hf_model_params_size(model_name, hf_proxies=None):
    """
    TODO: implement special model
    """
    LOGGER.debug(f"starg parse model's config: {model_name}")
    try:
        return specific_eval_hf_model_params_size(model_name, hf_proxies)
    except Exception as e:
        LOGGER.warning(f"specific_eval_hf_model_params_size error: {str(e)}")
        return estimate_hf_model_params_size(model_name, hf_proxies)


def specific_eval_hf_model_params_size(model_name, hf_proxies=None):
    """ """
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True, proxies=hf_proxies)
    if config.__class__.__name__ in ["BaichuanConfig", "QWenConfig"]:
        model = AutoModelForCausalLM.from_config(config, trust_remote_code=True)
    else:
        model = AutoModel.from_config(config, trust_remote_code=True)
    params_size = 0
    for w_name, p in list(model.named_parameters()):
        LOGGER.debug(f"w_name: {w_name}, shape: {p.shape}")
        params_size += np.prod(p.shape)
    return {"params_size": int(params_size), "model_type": config.model_type}


def estimate_hf_model_params_size(model_name, hf_proxies=None):
    """fast estimate hf model params_szie"""
    config = AutoConfig.from_pretrained(model_name, trust_remote_code=True, proxies=hf_proxies)
    if config.model_type == "chatglm":
        return chatglm_estimate_hf_model_params_size(config)
    num_layers = config.num_hidden_layers
    hidden_size = config.hidden_size
    vocab_size = config.vocab_size
    params_size = (
        vocab_size * hidden_size
        + num_layers * (4 * hidden_size**2 + 4 * hidden_size)
        + num_layers * (8 * hidden_size**2 + 5 * hidden_size)
        + 4 * num_layers * hidden_size
    )
    return {"params_size": int(params_size), "model_type": config.model_type}


def chatglm_estimate_hf_model_params_size(config):
    num_layers = config.num_layers
    hidden_size = config.hidden_size
    vocab_size = config.vocab_size
    params_size = (
        vocab_size * hidden_size
        + num_layers * (4 * hidden_size**2 + 4 * hidden_size)
        + num_layers * (8 * hidden_size**2 + 5 * hidden_size)
        + 4 * num_layers * hidden_size
    )
    return {"params_size": int(params_size), "model_type": config.model_type}
