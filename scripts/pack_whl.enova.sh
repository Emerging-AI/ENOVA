#!/bin/bash

set -x
echo "Runing packing wheel using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")

DOCKER_COMPOSE_BIN=enova/template/deployment/docker-compose/bin/docker-compose-linux-x86_64
DOWNLOAD_URL=https://github.com/docker/compose/releases/download/v2.24.5/docker-compose-linux-x86_64


if [ ! -f "$DOCKER_COMPOSE_BIN" ]; then
    echo "PWD: " $PWD
    mkdir -p enova/template/deployment/docker-compose/bin/

    echo "docker-compose binary $DOCKER_COMPOSE_BIN is not existed, start to download..."
    cd enova/template/deployment/docker-compose/bin/
    wget "$DOWNLOAD_URL"

    chmod +x docker-compose-linux-x86_64
    cd $BASEDIR
    if [ $? -eq 0 ]; then
        echo "download sucessfully"
    else
        echo "failed to download"
    fi
fi

# pack
cd $BASEDIR
python -m build --no-isolation

