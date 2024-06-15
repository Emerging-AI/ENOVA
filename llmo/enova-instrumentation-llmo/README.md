## 使用方式
安装whl包
```bash
pip install enova_instrumentation_llmo-0.0.3-py3-none-any.whl 
```
在vllm程序代码中进行ot配置和开启注入
```python

# 开启instrument
from enova.llmo import start
# 指定ot collector地址和service name
start(otlp_exporter_endpoint="localhost:4317", service_name="service_name")

#######接原代码内容#######
```

## Metrics 指标说明
- `avg_prompt_throughput` prompt 输入速率，单位 tokens/s
- `avg_generation_throughput` 生成速率，单位 tokens/s
- `running_requests` 当前 running 的 requests 数
- `swapped_requests` 当前 swapped 的 requests 数
- `pending_requests` 当前 pending 的 requests 数
- `gpu_kv_cache_usage` gpu kv cache 使用率
- `cpu_kv_cache_usage` cpu kv cache 使用率
- `generated_tokens` 生成的 tokens 数
- `llm_engine_init_config` engine启动参数，attributes如下
  - `model`
  - `tokenizer`
  - `tokenizer_mode`
  - `revision`
  - `tokenizer_revision`
  - `trust_remote_code`
  - `dtype`
  - `max_seq_len`
  - `download_dir`
  - `load_format`
  - `tensor_parallel_size`
  - `disable_custom_all_reduce`
  - `quantization`
  - `enforce_eager`
  - `kv_cache_dtype`
  - `seed`
  - `max_num_batched_tokens`
  - `max_num_seqs`
  - `max_paddings`
  - `pipeline_parallel_size`
  - `worker_use_ray`
  - `max_parallel_loading_workers`
- `http.server.active_requests` FastAPI 正在处理中的 HTTP 请求的数量
- `http.server.duration` FastAPI 服务端请求处理时间。
- `http.server.response.size` FastAPI HTTP 响应消息的大小
- `http.server.request.size` FastAPI HTTP 请求的大小


## trace span 说明
- `POST /generate` /generate请求
- `POST /generate prompt` 带有 `prompt` attribute
- `ModelRunner.execute_model` 模型execute，对应一次 token 生成
- `CUDAGraphRunner.forward` CUDA Graph的 forward 计算，在 `ModelRunner.execute_model` 中被调用
- `ChatGLMForCausalLM.forward` chatglm 模型 forward
- `LlamaForCausalLM.forward` llama 模型 forward

