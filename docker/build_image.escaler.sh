#!/bin/bash

set -x
IMAGE_VERSION=v`cat VERSION`

echo "Runing build image enova:${IMAGE_VERSION} using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")
echo "BASEDIR: " ${BASEDIR}


export HARBOR_PATH=dev-harbor.emergingai.inner.com/emergingai
export MIRROR_PATH=emergingai

# check golang tar.gz
GOLANG_TAR=dependencies/go1.22.2.linux-amd64.tar.gz
DOWNLOAD_URL=https://go.dev/dl/go1.22.2.linux-amd64.tar.gz

if [ ! -f "$GOLANG_TAR" ]; then
    mkdir -p dependencies

    echo "golang tar $GOLANG_TAR is not existed, start to download..."
    cd dependencies
    wget "$DOWNLOAD_URL"
    cd ../
    if [ $? -eq 0 ]; then
        echo "download sucessfully"
    else
        echo "failed to download"
    fi
fi

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.escaler -t $HARBOR_PATH/enova-escaler:$IMAGE_VERSION $BASEDIR

docker tag $HARBOR_PATH/enova-escaler:$IMAGE_VERSION  $MIRROR_PATH/enova-escaler:$IMAGE_VERSION
