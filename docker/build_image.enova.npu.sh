#!/bin/bash

set -x
echo "Runing build image enova:base using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")


export HARBOR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.enova.base.npu -t $HARBOR_PATH/enova:base-npu --build-arg HARBOR_PATH="$HARBOR_PATH" $BASEDIR
IMAGE_VERSION=v`cat VERSION`
ENOVA_VERSION=`cat VERSION`
LLMO_VERSION="0.1.1"

echo "Runing build image enova:${IMAGE_VERSION} using ${PWD}"


docker build -f $BASEDIR/docker/Dockerfile.enova.npu -t $HARBOR_PATH/enova:$IMAGE_VERSION-npu \
    --build-arg ENOVA_VERSION="${ENOVA_VERSION}" \
    --build-arg LLMO_VERSION="${LLMO_VERSION}" \
    --build-arg HARBOR_PATH="$HARBOR_PATH" \
    --build-arg CACHEBUST=$(date +%s) \
    $BASEDIR

