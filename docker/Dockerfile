# FROM nvcr.io/nvidia/pytorch:24.03-py3
FROM mergingai/enova:base

RUN apt update && apt install net-tools -y

COPY ./dist/enova-0.0.7-py3-none-any.whl /tmp/
COPY ./llmo/enova-instrumentation-llmo/dist/enova_instrumentation_llmo-0.0.7-py3-none-any.whl /tmp/

RUN pip config set global.index-url https://mirrors.aliyun.com/pypi/simple && \
    pip uninstall enova enova-instrumentation-llmo -y && \
    pip install --no-cache-dir /tmp/enova_instrumentation_llmo-0.0.7-py3-none-any.whl && \
    pip install --no-cache-dir /tmp/enova-0.0.7-py3-none-any.whl
