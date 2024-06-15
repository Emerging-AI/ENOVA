#!/bin/bash

set -x
IMAGE_VERSION=v`cat VERSION`
ENOVA_VERSION=`cat VERSION`
LLMO_VERSION="0.0.3"

echo "Runing build image enova:${IMAGE_VERSION} using ${PWD}"

SCRIPT=$(realpath "$0")
BASEDIR=$(dirname "$SCRIPT")
BASEDIR=$(dirname "$BASEDIR")
echo "BASEDIR: " ${BASEDIR}

# build front
cd $BASEDIR/front
rm $BASEDIR/enova/web_statics -rf
npm install
npm run build
# yarn
# yarn build

echo $BASEDIR/front/dist $BASEDIR/enova/web_statics
mv $BASEDIR/front/dist $BASEDIR/enova/web_statics

export HARBOR_PATH=emergingai

# build enova
cd $BASEDIR
docker build -f $BASEDIR/docker/Dockerfile.enova -t $HARBOR_PATH/enova:$IMAGE_VERSION \
    --build-arg ENOVA_VERSION="${ENOVA_VERSION}" \
    --build-arg LLMO_VERSION="${LLMO_VERSION}" \
    --build-arg HARBOR_PATH="$HARBOR_PATH" \
    --build-arg CACHEBUST=$(date +%s) \
    $BASEDIR
