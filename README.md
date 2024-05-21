# ENOVA

# Introducation


# How to install

## Python version
\>= 3.10

## Install llmo
```
pip install llmo/enova-instrumentation-llmo/dist/enova_instrumentation_llmo-0.0.1-py3-none-any.whl
```

## Install enova
```
pip install dist/enova-0.0.1-py3-none-any.whl
```

# How to use

## Prerequisites
Docker

## All in one
- first use docker-compose to start grafana, prometheus, opentelmentry-collector, tempo, dcgm etc..
- second use docker-compose to start enova-app, enova-algo, enova-pilot
- finally use enova-app api to start serving with vllm(/generate)
```bash
enova pilot run --model THUDM/chatglm3-6b --host 0.0.0.0 --port 9199 --tensor_parallel_size 1

# test model
curl -X POST http://localhost:9199/generate \
-d '{
"prompt": "San Francisco is a",
"use_beam_search": true,
"stream": false,
"n": 4,
"temperature": 0
}'
```

- Enova directly pass vllm config to vllm backend through command line params
```bash
enova pilot run --model THUDM/chatglm3-6b --host 0.0.0.0 --port 9199 --tensor_parallel_size 1 --trust_remote_code=True --vllm_mode=openai --hf_proxy=http://192.168.3.2:7892
```

### Use proxy


## Just run model
- just serving in vllm(/generate) in default 
```bash
enova enode run --model THUDM/chatglm3-6b --port 9199 --tensor_parallel_size 1
```

## Run webui
before starting webui separately, please ensure that you already have an available enova serving service.
```bash
enova webui run --serving_host 127.0.0.1 --serving_port 9199 --host 0.0.0.0 --port 8501
```

## Run monitor servics
Enova used Monitor services included Grafana, Prometheus, Tempo, Opentelemetry, DCGM to visualize the performance of llm
### start up
```
enova mon start
```

### status
```
enova mon status
```

### down all
```
enova mon stop
```

## Run injection

## View metrics

## Metric in Grafana
Enova start grafana to present metric by default.

Enova present 3 types of dashboard

### Grafana url
```
http://{current_ip}:32827

# user / passwd
admin / grafana
```

# Problems
- mostly, hardware maybe the first problem, such as P100 does not support fp16, and memory not enough for llm models
- Environment will be another problem. CUDA version, nccl, etc.

# How to build

## Build into docker image
### enova
```bash
bash docker/build_image.enova.sh
```

### enova-pilot
```bash
bash docker/build_image.pilot.sh
```

# Develop Requirements

## zmq
- ubuntu
```bash
apt install libzmq3-dev
```

## redis
- ubuntu
```bash
apt install redis
```

## node 8

## Pilot
- apidocs
    after start pilot server
    - http://127.0.0.1:8183/api/pilot/docs/swagger/index.html

# future works
## autoscale
- [ x ] enova in docker
- [ x ] autoscale detector / autoscale scaler
- [ x ] http request inject
- [ ] triton server with models
- [ ] enova in k8s
