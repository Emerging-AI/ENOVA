#!/bin/bash

set -x
IMAGE_VERSION=v0.0.1 # TODO: version.txt

echo "Runing build image enova-jmoter:${IMAGE_VERSION} using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")
echo "BASEDIR: " ${BASEDIR}


export HARBOR_PATH=dev-harbor.emergingai.inner.com/emergingai
# export MIRROR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.jmeter -t $HARBOR_PATH/enova-jmeter:$IMAGE_VERSION  $BASEDIR