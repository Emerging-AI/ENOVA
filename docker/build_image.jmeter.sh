#!/bin/bash

set -x
IMAGE_VERSION=v`cat VERSION`

echo "Runing build image enova-jmoter:${IMAGE_VERSION} using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")
echo "BASEDIR: " ${BASEDIR}


export HARBOR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.jmeter -t $HARBOR_PATH/enova-jmeter:$IMAGE_VERSION  $BASEDIR
