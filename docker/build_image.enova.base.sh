#!/bin/bash

set -x
echo "Runing build image enova:base using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")


export HARBOR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.enova.base -t $HARBOR_PATH/enova:base --build-arg HARBOR_PATH="$HARBOR_PATH" $BASEDIR
